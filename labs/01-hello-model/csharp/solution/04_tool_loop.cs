#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 1 · step 4 — the tool-call loop, by hand. This loop is the foundation of every agent you will see today.
//
// What this shows: the model cannot run code — it can only ASK for a tool. The loop is:
// model -> "please call get_weather(city='Paris')" -> YOUR code runs it -> result goes back as a "tool" message ->
// model answers (or asks for another tool). Frameworks run exactly this loop for you: M.E.AI's FunctionInvokingChatClient
// and every Agent Framework agent (Lab 3) — here we write it ourselves with the plain OpenAI .NET SDK.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Text.Json;
using OpenAI;
using OpenAI.Chat;
#pragma warning disable OPENAI001 // ReasoningEffortLevel is still marked "experimental" in the OpenAI .NET SDK 2.13

// ---- 1. Settings and client (same as step 1) ----
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

// ---- 2. The tools: plain C# functions (fake data, so the result is predictable) ----
var fakeWeather = new Dictionary<string, (int TempC, string Sky)>
{
    ["paris"] = (19, "light rain"), ["mannheim"] = (22, "sunny"), ["jacksonville"] = (31, "thunderstorms"),
};

string GetWeather(string city)
{
    var (temp, sky) = fakeWeather.GetValueOrDefault(city.ToLowerInvariant(), (20, "unknown"));
    return JsonSerializer.Serialize(new { city, temp_c = temp, sky });   // tools return text; JSON is easy for models
}

string ToFahrenheit(double celsius) => JsonSerializer.Serialize(new { celsius, fahrenheit = Math.Round(celsius * 9 / 5 + 32, 1) });

// What the model SEES of each tool: a name, a description and a JSON Schema for the arguments (not the code).
var options = new ChatCompletionOptions
{
    Tools =
    {
        ChatTool.CreateFunctionTool("get_weather", "Current weather for a city.", BinaryData.FromString(
            """{"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}""")),
        ChatTool.CreateFunctionTool("to_fahrenheit", "Convert a temperature from Celsius to Fahrenheit.", BinaryData.FromString(
            """{"type": "object", "properties": {"celsius": {"type": "number"}}, "required": ["celsius"]}""")),
    },
};
// Optional "think less" knob (GENAI_REASONING_EFFORT=low); only sent when set (see step 1).
if (Env("GENAI_REASONING_EFFORT", "") is { Length: > 0 } effort) options.ReasoningEffortLevel = new ChatReasoningEffortLevel(effort);

// Our side of the contract: run the function the model asked for, with the arguments it sent (a JSON string).
string Run(ChatToolCall call)
{
    using JsonDocument args = JsonDocument.Parse(call.FunctionArguments);
    return call.FunctionName switch
    {
        "get_weather" => GetWeather(args.RootElement.GetProperty("city").GetString()!),
        "to_fahrenheit" => ToFahrenheit(args.RootElement.GetProperty("celsius").GetDouble()),
        _ => $$"""{"error": "unknown tool {{call.FunctionName}}"}""",
    };
}

// ---- 3. The conversation so far: the model has no memory, so we resend this list every time ----
List<ChatMessage> messages =
[
    new SystemChatMessage("Use the tools for facts. Be brief."),
    new UserChatMessage("What's the weather in Paris, and what is that temperature in Fahrenheit?"),
];

// ---- 4. The loop: call the model, run what it asks for, send the results back, repeat ----
const int Budget = 6;                                   // a budget: agents need a stop condition
int step = 0;
for (; step < Budget; step++)
{
    ChatCompletion response = await client.CompleteChatAsync(messages, options);
    // >>> TODO 2: append the assistant message; if it has no ToolCalls print the answer and stop; otherwise run each tool and append a ToolChatMessage per call
    messages.Add(new AssistantChatMessage(response));    // the assistant turn (incl. its tool calls) stays in the history
    if (response.ToolCalls.Count == 0)                   // no tool requested = this is the final answer
    {
        Console.WriteLine($"\nANSWER after {step} tool round(s): {response.Content[0].Text}");
        break;
    }
    foreach (ChatToolCall call in response.ToolCalls)    // the model may ask for several tools at once
    {
        string result = Run(call);
        Console.WriteLine($"  tool call #{step + 1}: {call.FunctionName}({call.FunctionArguments}) -> {result}");
        messages.Add(new ToolChatMessage(call.Id, result));   // Id = which request this answers
    }
    // <<< TODO
}
if (step == Budget) Console.WriteLine("Stopped: step budget exhausted.");   // the loop ran out without a final answer

// Try this:
//  * Ask something that needs no tool ("Tell me a joke") — the model answers directly.
//  * Ask for three cities at once — many models return several ToolCalls in ONE turn (parallel tool calls).
//  * Remove the system prompt or a tool description and watch the tool choice get worse.

// Plumbing (same in every file): adds the "api-key" header to every request. You can skip reading this.
sealed class HeaderPolicy(string name, string value) : PipelinePolicy
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
