#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 1 · step 5 — same code, different model. The point of the day in one script.
//
// What this shows: one prompt and one tool request, sent unchanged to every endpoint it finds in labs/.env:
//   the workshop endpoint (GENAI_MODEL), a second vendor behind the same key (GENAI_MODEL_2),
//   local Ollama (OLLAMA_BASE_URL / OLLAMA_MODEL) and LM Studio (LMSTUDIO_BASE_URL) if they are running.
// What to notice: only the URL, key and model name differ — compare speed, answer length and tool-calling habits.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Diagnostics;
using OpenAI;
using OpenAI.Chat;
#pragma warning disable OPENAI001 // ReasoningEffortLevel is still marked "experimental" in the OpenAI .NET SDK 2.13

// ---- 1. Settings (same as step 1) ----
var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))    // walk up to the labs/ root
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
// labs/.env, or one .env at the repo root: load every .env from labs/ upward - NoClobber, so the nearest wins
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));   // labs/.env; real environment variables win
static string Env(string name, string? fallback = null) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
    ? value : fallback ?? throw new InvalidOperationException($"{name} is not set - copy labs/.env.example to labs/.env");

string baseUrl = Env("GENAI_BASE_URL"), key = Env("GENAI_API_KEY");
bool keyHeader = (Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key";
// Thinking knob: OLLAMA_REASONING_EFFORT for local models, GENAI_REASONING_EFFORT for the workshop model only
string effort = Env("GENAI_REASONING_EFFORT", ""), localEffort = Env("OLLAMA_REASONING_EFFORT", "");

// ---- 2. The list of targets — add a line here to add a target ----
// label, endpoint, key, send the api-key header?, model ("" = ask the server), reasoning effort ("" = don't send)
var targets = new List<(string Label, string BaseUrl, string Key, bool KeyHeader, string Model, string Effort)>
{
    ("workshop endpoint", baseUrl, key, keyHeader, Env("GENAI_MODEL"), effort),
};
if (Env("GENAI_MODEL_2", "") is { Length: > 0 } model2)
    targets.Add(("2nd vendor, same key", baseUrl, key, keyHeader, model2, ""));
if (Env("OLLAMA_BASE_URL", "") is { Length: > 0 } ollama && Env("OLLAMA_MODEL", "") is { Length: > 0 } ollamaModel)
    targets.Add(("local Ollama", ollama, "ollama", false, ollamaModel, localEffort));
if (Env("LMSTUDIO_BASE_URL", "") is { Length: > 0 } lmStudio)
    targets.Add(("local LM Studio", lmStudio, "lm-studio", false, Env("LMSTUDIO_MODEL", ""), localEffort));

// One tool, described exactly as in step 4.
ChatTool weatherTool = ChatTool.CreateFunctionTool("get_weather", "Current weather for a city.", BinaryData.FromString(
    """{"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}"""));

// ---- 3. The same two calls against every target ----
foreach (var (label, url, apiKey, header, configuredModel, eff) in targets)
{
    string model = configuredModel;
    try
    {
        // NetworkTimeout: a laptop model can be slow; maxRetries: 0: if a target is down, say so at once
        var clientOptions = new OpenAIClientOptions
        {
            Endpoint = new Uri(url), NetworkTimeout = TimeSpan.FromSeconds(180), RetryPolicy = new ClientRetryPolicy(maxRetries: 0),
        };
        if (header) clientOptions.AddPolicy(new HeaderPolicy("api-key", apiKey), PipelinePosition.PerCall);
        var openai = new OpenAIClient(new ApiKeyCredential(apiKey), clientOptions);
        if (model == "")                                     // LM Studio: take whatever model is loaded
            model = (await openai.GetOpenAIModelClient().GetModelsAsync()).Value[0].Id;
        ChatClient client = openai.GetChatClient(model);
        ChatCompletionOptions Options() => eff == "" ? new() : new() { ReasoningEffortLevel = new ChatReasoningEffortLevel(eff) };

        var clock = Stopwatch.StartNew();                    // call 1: plain chat, timed
        ChatCompletion r = await client.CompleteChatAsync(
            [new UserChatMessage("Explain retrieval-augmented generation to a developer in one sentence.")], Options());
        double chatSeconds = clock.Elapsed.TotalSeconds;
        clock.Restart();                                     // call 2: does it ask for the tool?
        ChatCompletionOptions withTool = Options();
        withTool.Tools.Add(weatherTool);
        ChatCompletion r2 = await client.CompleteChatAsync([new UserChatMessage("What's the weather in Mannheim?")], withTool);
        double toolSeconds = clock.Elapsed.TotalSeconds;

        // ---- 4. What came back: time, length and answer per target ----
        Console.WriteLine($"\n== {label}: {model}  ({url})");
        Console.WriteLine($"   chat  {chatSeconds,5:F1}s  {r.Usage?.OutputTokenCount.ToString() ?? "?"} tokens: {Cut(Text(r), 160)}");
        Console.WriteLine($"   tools {toolSeconds,5:F1}s  " + (r2.ToolCalls.Count > 0
            ? string.Join(", ", r2.ToolCalls.Select(c => $"{c.FunctionName}({c.FunctionArguments})"))
            : $"no tool call -> {Cut(Text(r2), 80)}"));
    }
    catch (Exception e)                                      // a missing local runtime must not stop the comparison
    {
        Console.WriteLine($"\n== {label}: {(model == "" ? "?" : model)}  skipped ({e.GetType().Name}: {Cut(e.Message.ReplaceLineEndings(" "), 120)})");
    }
}

// Small helpers: all text parts of an answer joined; the first n characters of a string.
static string Text(ChatCompletion c) => string.Concat(c.Content.Select(part => part.Text)).Trim();
static string Cut(string text, int max) => text.Length <= max ? text : text[..max];

// What to notice: identical code, different answers, latency and tool-calling habits.
// Independence = being able to make this switch in one line — and knowing what you lose or gain when you do.

// Plumbing (same in every file): adds the "api-key" header to every request. You can skip reading this.
sealed class HeaderPolicy(string name, string value) : PipelinePolicy
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
