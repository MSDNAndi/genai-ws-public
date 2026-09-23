using System.ClientModel;
using System.ClientModel.Primitives;
using System.Text.Json;
using System.Runtime.CompilerServices;
using System.Text.RegularExpressions;
using Microsoft.Extensions.AI;
using OpenAI;

namespace GenAIClass;

/// <summary>One provider entry from providers.json, with ${VAR} already expanded.</summary>
public sealed record Profile(
    string Name,
    string Label,
    string BaseUrl,
    string ApiKey,
    string KeyHeader,
    string Model,
    string EmbedModel)
{
    public IReadOnlyList<string> Missing()
    {
        var gaps = new List<string>();
        if (string.IsNullOrWhiteSpace(BaseUrl) || BaseUrl.Contains('<')) gaps.Add("base_url");
        if (string.IsNullOrWhiteSpace(ApiKey)) gaps.Add("api_key");
        return gaps;
    }

    public override string ToString() => $"[{Name}] {Model} @ {BaseUrl}";
}

/// <summary>
/// Resolves a provider profile from providers.json plus .env / environment, and
/// hands back a client. The workshop endpoint, OpenAI, OpenRouter, Ollama and
/// LM Studio differ only in a base URL, a key and a model name.
/// </summary>
public static class Providers
{
    private static readonly Regex Placeholder =
        new(@"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}", RegexOptions.Compiled);

    /// <summary>Walk up from the caller's directory until providers.json shows up.</summary>
    public static DirectoryInfo RepoRoot(string? start = null)
    {
        var dir = new DirectoryInfo(start ?? AppContext.BaseDirectory);
        for (var d = dir; d is not null; d = d.Parent)
            if (File.Exists(Path.Combine(d.FullName, "providers.json")))
                return d;

        // File-based apps build into a temp folder, so also try the current directory.
        for (var d = new DirectoryInfo(Directory.GetCurrentDirectory()); d is not null; d = d.Parent)
            if (File.Exists(Path.Combine(d.FullName, "providers.json")))
                return d;

        throw new FileNotFoundException("providers.json not found - run from inside the samples repo");
    }

    private static DirectoryInfo FindRoot(string callerFile)
    {
        var dir = string.IsNullOrEmpty(callerFile) ? null : Path.GetDirectoryName(callerFile);
        for (var d = dir is null ? null : new DirectoryInfo(dir); d is not null; d = d.Parent)
            if (File.Exists(Path.Combine(d.FullName, "providers.json")))
                return d;
        return RepoRoot();   // falls back to the build folder, then the current directory
    }

    private static void LoadDotEnv(DirectoryInfo root)
    {
        // demos/.env, or one .env at the root of a cloned repo: read every .env from the repo folder
        // upward. A variable that is already set is never overwritten, so the nearest file wins.
        for (var dir = root; dir is not null; dir = dir.Parent)
        {
            var path = Path.Combine(dir.FullName, ".env");
            if (File.Exists(path)) LoadDotEnvFile(path);
        }
    }

    private static void LoadDotEnvFile(string path)
    {
        foreach (var raw in File.ReadAllLines(path))
        {
            var line = raw.Trim();
            if (line.Length == 0 || line.StartsWith('#')) continue;
            var eq = line.IndexOf('=');
            if (eq <= 0) continue;
            var key = line[..eq].Trim();
            var value = line[(eq + 1)..].Trim().Trim('"');
            // Real environment variables win over the file.
            if (Environment.GetEnvironmentVariable(key) is null)
                Environment.SetEnvironmentVariable(key, value);
        }
    }

    private static string Expand(string value) => Placeholder.Replace(value, m =>
    {
        var fromEnv = Environment.GetEnvironmentVariable(m.Groups[1].Value);
        if (!string.IsNullOrEmpty(fromEnv)) return fromEnv;
        return m.Groups[2].Success ? m.Groups[2].Value : string.Empty;
    });

    /// <summary>Explicit name &gt; --profile on the command line &gt; GENAI_PROFILE &gt; the file's default.</summary>
    public static Profile GetProfile(string? name = null, string[]? args = null,
                                     [CallerFilePath] string callerFile = "")
    {
        // Start at the sample's own source file (the compiler fills callerFile in), so a sample run
        // from any folder still finds its repo, providers.json and .env - not only from inside the repo.
        var root = FindRoot(callerFile);
        LoadDotEnv(root);

        using var doc = JsonDocument.Parse(File.ReadAllText(Path.Combine(root.FullName, "providers.json")));
        var profiles = doc.RootElement.GetProperty("profiles");

        name ??= ProfileFromArgs(args ?? Environment.GetCommandLineArgs())
              ?? Environment.GetEnvironmentVariable("GENAI_PROFILE")
              ?? doc.RootElement.GetProperty("default").GetString();

        if (name is null || !profiles.TryGetProperty(name, out var entry))
        {
            var known = string.Join(", ", profiles.EnumerateObject().Select(p => p.Name));
            throw new ArgumentException($"Unknown profile '{name}'. Known profiles: {known}");
        }

        string Get(string key, string fallback = "") =>
            entry.TryGetProperty(key, out var v) ? Expand(v.GetString() ?? fallback) : fallback;

        return new Profile(
            Name: name,
            Label: Get("label", name),
            BaseUrl: Get("base_url").TrimEnd('/'),
            ApiKey: Get("api_key"),
            KeyHeader: Get("key_header", "authorization").ToLowerInvariant(),
            Model: Get("model"),
            EmbedModel: Get("embed_model"));
    }

    private static string? ProfileFromArgs(string[] args)
    {
        for (var i = 0; i < args.Length - 1; i++)
            if (args[i] is "--profile" or "-p") return args[i + 1];
        return null;
    }

    /// <summary>An <see cref="OpenAIClient"/> pointed at the profile's endpoint.</summary>
    public static OpenAIClient CreateClient(Profile? profile = null)
    {
        profile ??= GetProfile();
        var gaps = profile.Missing();
        if (gaps.Count > 0)
            throw new InvalidOperationException(
                $"Profile '{profile.Name}' is missing {string.Join(", ", gaps)}. " +
                "Fill it in .env (see .env.example) or pick another --profile.");

        var options = new OpenAIClientOptions { Endpoint = new Uri(profile.BaseUrl) };

        // Azure/APIM want the key in an `api-key` header; everyone else takes the
        // SDK's default `Authorization: Bearer`. Same client, one extra header.
        if (profile.KeyHeader == "api-key")
            options.AddPolicy(new HeaderPolicy("api-key", profile.ApiKey), PipelinePosition.PerCall);

        return new OpenAIClient(new ApiKeyCredential(profile.ApiKey), options);
    }

    /// <summary>The same endpoint behind Microsoft.Extensions.AI's <see cref="IChatClient"/>.</summary>
    public static IChatClient CreateChatClient(Profile? profile = null)
    {
        profile ??= GetProfile();
        return CreateClient(profile).GetChatClient(profile.Model).AsIChatClient();
    }

    private sealed class HeaderPolicy(string name, string value) : PipelinePolicy
    {
        public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
        {
            message.Request.Headers.Set(name, value);
            ProcessNext(message, pipeline, index);
        }

        public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
        {
            message.Request.Headers.Set(name, value);
            return ProcessNextAsync(message, pipeline, index);
        }
    }
}
