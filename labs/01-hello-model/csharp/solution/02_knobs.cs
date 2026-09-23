#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 1 · step 2 — the sampling knobs: temperature, top_p, seed ... and the models that ignore them.
//
// Reasoning models (gpt-5 family, o-series, many "thinking" models) fix temperature/top_p at their defaults and use
// reasoning_effort instead. So this script asks the model first and falls back gracefully.
// Tip: run it once with GENAI_MODEL=gpt-5-mini and once with GENAI_MODEL=$GENAI_MODEL_2 (e.g. DeepSeek-V3.2) or Ollama.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Diagnostics;
using OpenAI;
using OpenAI.Chat;
#pragma warning disable OPENAI001 // Seed and ReasoningEffortLevel are still marked "experimental" in the OpenAI .NET SDK 2.13

var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))    // walk up to the labs/ root
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
// labs/.env, or one .env at the repo root: load every .env from labs/ upward - NoClobber, so the nearest wins
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));   // labs/.env; real environment variables win
static string Env(string name, string? fallback = null) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
    ? value : fallback ?? throw new InvalidOperationException($"{name} is not set - copy labs/.env.example to labs/.env");

string key = Env("GENAI_API_KEY"), model = Env("GENAI_MODEL");
var clientOptions = new OpenAIClientOptions { Endpoint = new Uri(Env("GENAI_BASE_URL")) };
if ((Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key")
    clientOptions.AddPolicy(new HeaderPolicy("api-key", key), PipelinePosition.PerCall);
ChatClient client = new OpenAIClient(new ApiKeyCredential(key), clientOptions).GetChatClient(model);
// local "thinking" models: reasoning_effort=none keeps this fast (the knob experiment itself is below)
bool noThinking = Env("GENAI_REASONING_EFFORT", "") == "none";

const string Prompt = "Invent a name for a coffee shop run by robots. Answer with the name only.";

// Three answers with the same knobs, printed like a Python list.
async Task<string> AskThreeTimes(Func<ChatCompletionOptions> knobs)
{
    var answers = new List<string>();
    for (int i = 0; i < 3; i++)
    {
        ChatCompletionOptions options = knobs();
        if (noThinking) options.ReasoningEffortLevel = ChatReasoningEffortLevel.None;
        ChatCompletion r = await client.CompleteChatAsync([new UserChatMessage(Prompt)], options);
        answers.Add($"'{r.Content.FirstOrDefault()?.Text.Trim()}'");
    }
    return $"[{string.Join(", ", answers)}]";
}

try
{
    foreach (float t in new[] { 0.0f, 1.0f, 1.6f })
        Console.WriteLine($"temperature={t:0.0}: {await AskThreeTimes(() => new() { Temperature = t })}");
    Console.WriteLine($"temperature=1.0, top_p=0.1: {await AskThreeTimes(() => new() { Temperature = 1.0f, TopP = 0.1f })}");
    Console.WriteLine($"temperature=1.0, seed=42 (best effort!): {await AskThreeTimes(() => new() { Temperature = 1.0f, Seed = 42 })}");
}
catch (ClientResultException e) when (e.Status == 400)            // HTTP 400 = the service rejected a parameter
{
    Console.WriteLine($"'{model}' rejected a sampling knob -> it is probably a reasoning model.\n  {Cut(e.Message.ReplaceLineEndings(" "), 200)}");
    Console.WriteLine("Reasoning models expose a different knob: reasoning_effort (how long they think).");
    foreach (var effort in new[] { "minimal", "low", "high" })
    {
        var clock = Stopwatch.StartNew();
        try
        {
            ChatCompletion r = await client.CompleteChatAsync([new UserChatMessage("Is 1001 prime? One line.")],
                new ChatCompletionOptions { ReasoningEffortLevel = new ChatReasoningEffortLevel(effort) });
            ChatTokenUsage u = r.Usage;
            Console.WriteLine($"  reasoning_effort={effort,-7} {clock.Elapsed.TotalSeconds,5:F1}s  completion={u.OutputTokenCount} " +
                              $"(reasoning={u.OutputTokenDetails?.ReasoningTokenCount})  -> {Cut(r.Content.FirstOrDefault()?.Text.Trim() ?? "", 60)}");
        }
        catch (ClientResultException e2) when (e2.Status == 400)
        {
            Console.WriteLine($"  reasoning_effort={effort}: not supported here ({Cut(e2.Message.ReplaceLineEndings(" "), 80)})");
        }
    }
}

static string Cut(string text, int max) => text.Length <= max ? text : text[..max];

// What to notice:
//  * temperature 0 is "mostly the same", not "guaranteed identical"; seed is best-effort on most providers.
//  * top_p=0.1 narrows the choice to the few most likely tokens — similar effect to a low temperature.
//  * reasoning tokens are billed even though you never see them.

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
