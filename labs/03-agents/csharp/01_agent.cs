#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 3 · step 1 — an agent is the Lab 1 tool loop + a runtime: instructions, tools, memory (a session), a budget.
//
// Microsoft Agent Framework (MAF) 1.22 for .NET. We use a Chat Completions client because every endpoint of the day speaks
// it (Foundry, the gateway, Ollama, LM Studio, the offline mock); GetResponsesClient() would use the Responses API instead.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.ComponentModel;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using OpenAI;
using OpenAI.Chat;
#pragma warning disable OPENAI001 // ReasoningEffortLevel is still marked "experimental" in the OpenAI .NET SDK 2.13

var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))    // walk up to the labs/ root
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
// labs/.env, or one .env at the repo root: load every .env from labs/ upward - NoClobber, so the nearest wins
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));   // labs/.env; real environment variables win
static string Env(string name, string? fallback = null) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
    ? value : fallback ?? throw new InvalidOperationException($"{name} is not set - copy labs/.env.example to labs/.env");

string key = Env("GENAI_API_KEY"), effort = Env("GENAI_REASONING_EFFORT", "");
var clientOptions = new OpenAIClientOptions { Endpoint = new Uri(Env("GENAI_BASE_URL")) };
if ((Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key")
    clientOptions.AddPolicy(new HeaderPolicy("api-key", key), PipelinePosition.PerCall);
// One chat client for all agents. GENAI_REASONING_EFFORT rides along on every request (low for gpt-5 models, none for
// local thinking models): RawRepresentationFactory hands the OpenAI SDK its own request options with the effort set.
IChatClient chatClient = new OpenAIClient(new ApiKeyCredential(key), clientOptions)
    .GetChatClient(Env("GENAI_MODEL")).AsIChatClient()
    .AsBuilder()
    .ConfigureOptions(o =>
    {
        if (effort != "") o.RawRepresentationFactory ??= _ => new ChatCompletionOptions { ReasoningEffortLevel = new(effort) };
    })
    .Build();

var fakeWeather = new Dictionary<string, (int TempC, string Sky)>
{
    ["paris"] = (19, "light rain"), ["mannheim"] = (22, "sunny"), ["jacksonville"] = (31, "thunderstorms"),
};

// Tools are plain C# methods. Return data, not strings: the framework serializes the result to JSON for the model.
[Description("Current weather for a city (temperature in Celsius and sky).")]
object GetWeather(string city)
{
    var (temp, sky) = fakeWeather.GetValueOrDefault(city.ToLowerInvariant(), (20, "unknown"));
    return new { city, temp_c = temp, sky };
}

[Description("Convert Celsius to Fahrenheit.")]
object ToFahrenheit(double celsius) => new { fahrenheit = Math.Round(celsius * 9 / 5 + 32, 1) };

// AIFunctionFactory turns a method into a tool: name, [Description]s and parameter types become the JSON Schema the
// model sees. (Without the explicit name, a local function would show up as "_Main_g_GetWeather_0_0".)
AIAgent agent = chatClient.AsAIAgent(
    name: "WeatherAgent",
    instructions: "You are a travel assistant. Use the tools for facts; answer in one or two sentences.",
    tools: [AIFunctionFactory.Create(GetWeather, "get_weather"), AIFunctionFactory.Create(ToFahrenheit, "to_fahrenheit")]);

AgentSession session = await agent.CreateSessionAsync();       // the conversation memory lives here
string[] questions = ["What's the weather in Mannheim?", "And what is that in Fahrenheit?", "Which city did I ask about?"];
foreach (string question in questions)
{
    AgentResponse response = await agent.RunAsync(question, session);
    Console.WriteLine($"> {question}\n  {response.Text.Trim()}");
}
// No session -> no memory: the agent cannot know what "that" refers to.
Console.WriteLine($"\nWithout the session: {Cut((await agent.RunAsync("And what is that in Fahrenheit?")).Text.Trim(), 160)}");

static string Cut(string text, int max) => text.Length <= max ? text : text[..max];

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
