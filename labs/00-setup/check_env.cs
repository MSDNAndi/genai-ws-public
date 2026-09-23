#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// check_env.cs — is my laptop ready for the C# track?      dotnet run --file 00-setup/check_env.cs   (from labs/)
// The first run also downloads the NuGet packages the labs use (so it works offline on the day).
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Net.Http.Json;
using System.Text.Json;
using OpenAI;
using OpenAI.Chat;
using OpenAI.Embeddings;
#pragma warning disable OPENAI001

var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
// labs/.env, or one .env at the repo root: load every .env from labs/ upward - NoClobber, so the nearest wins
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));
string Get(string name) => Environment.GetEnvironmentVariable(name) ?? "";
int fails = 0;
void Report(bool ok, string what, string detail = "") { if (!ok) fails++; Console.WriteLine($"{(ok ? "✅" : "❌")} {what}{(!ok && detail != "" ? "\n     " + detail : "")}"); }
string Hint(Exception e) => e.Message switch
{
    var m when m.Contains("401") => "401: key missing or wrong. Check GENAI_API_KEY and GENAI_KEY_HEADER=api-key.",
    var m when m.Contains("404") => "404: model/deployment name or URL wrong (GENAI_BASE_URL must end with /openai/v1 or /v1).",
    var m when m.Contains("429") => "429: your per-minute token limit was hit - wait a minute, then retry.",
    var m when m.Contains("403") => "403: today's token quota for your key is used up (or the key may not use this model) - ask the instructor.",
    var m => m.Length > 200 ? m[..200] : m,
};

Report(Environment.Version.Major >= 10, $".NET runtime {Environment.Version}", ".NET 10 SDK required: https://dot.net");
string[] need = ["GENAI_BASE_URL", "GENAI_API_KEY", "GENAI_MODEL", "GENAI_EMBED_MODEL"];
var absent = need.Where(n => Get(n) == "" || Get(n).Contains('<')).ToList();
if (absent.Count > 0) { Report(false, "settings missing: " + string.Join(", ", absent), "copy labs/.env.example to labs/.env"); return 1; }
string key = Get("GENAI_API_KEY"), model = Get("GENAI_MODEL");
Console.WriteLine($"   endpoint {Get("GENAI_BASE_URL")} · model {model} · key …{key[^4..]}");

var options = new OpenAIClientOptions { Endpoint = new Uri(Get("GENAI_BASE_URL")), NetworkTimeout = TimeSpan.FromMinutes(2) };
if ((Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key")
    options.AddPolicy(new HeaderPolicy("api-key", key), PipelinePosition.PerCall);
var openai = new OpenAIClient(new ApiKeyCredential(key), options);
var chatOptions = new ChatCompletionOptions();
if (Get("GENAI_REASONING_EFFORT") is { Length: > 0 } effort) chatOptions.ReasoningEffortLevel = new ChatReasoningEffortLevel(effort);

try
{
    var r = await openai.GetChatClient(model).CompleteChatAsync([new UserChatMessage("Reply with the word ready.")], chatOptions);
    Report(true, $"chat: '{r.Value.Content[0].Text.Trim()}'");
}
catch (Exception e) { Report(false, "chat call failed", Hint(e)); return 1; }

try
{
    var tool = ChatTool.CreateFunctionTool("get_weather", "Weather for a city",
        BinaryData.FromString("""{"type":"object","properties":{"city":{"type":"string"}},"required":["city"]}"""));
    var toolOptions = new ChatCompletionOptions { Tools = { tool }, ReasoningEffortLevel = chatOptions.ReasoningEffortLevel };
    var r = await openai.GetChatClient(model).CompleteChatAsync([new UserChatMessage("What's the weather in Paris?")], toolOptions);
    var call = r.Value.ToolCalls.FirstOrDefault();
    Report(true, call is null ? "tool calling: model answered without the tool (try another model)" : $"tool calling: {call.FunctionName}({call.FunctionArguments})");
}
catch (Exception e) { Report(false, "tool calling failed", Hint(e)); }

try
{
    var emb = await openai.GetEmbeddingClient(Get("GENAI_EMBED_MODEL")).GenerateEmbeddingAsync("hello");
    Report(true, $"embeddings: {Get("GENAI_EMBED_MODEL")} -> {emb.Value.ToFloats().Length} dims");
}
catch (Exception e) { Report(false, "embeddings failed (needed for Lab 2)", Hint(e)); }

if (Get("OLLAMA_BASE_URL") is { Length: > 0 } ollama)
{
    try
    {
        using var http = new HttpClient { Timeout = TimeSpan.FromSeconds(10) };
        var models = await http.GetFromJsonAsync<JsonElement>(ollama.TrimEnd('/') + "/models");
        Console.WriteLine($"✅ Ollama: {models.GetProperty("data").GetArrayLength()} model(s) at {ollama}");
    }
    catch (Exception e) { Console.WriteLine($"⚠️  Ollama not reachable (needed for Lab 1 step 5 and Lab 4): {e.Message}"); }
}
Console.WriteLine(fails == 0 ? "\nAll set - see you at the workshop!" : "\nPlease fix the ❌ items (details above).");
return fails == 0 ? 0 : 1;

sealed class HeaderPolicy(string name, string value) : PipelinePolicy
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
