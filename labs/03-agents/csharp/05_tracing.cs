#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package OpenTelemetry@1.19.1
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// STARTER - complete the TODO block(s). The finished version is in solution/05_tracing.cs
// Lab 3 · step 5 — see what the agent actually did: OpenTelemetry spans (the GenAI semantic conventions).
//
// In .NET, telemetry is opt-in: UseOpenTelemetry() on the agent emits an "invoke_agent" span and instruments its chat
// client ("chat <model>", with token usage) and its tool calls ("execute_tool <name>"). The OpenTelemetry SDK collects
// the spans of our source. The stock console exporter (OpenTelemetry.Exporter.Console) prints every attribute of every
// span, so for the lab we plug in a tiny exporter that prints one line per span instead. In production you point the
// same spans at Application Insights, Aspire, Jaeger or Langfuse (.AddOtlpExporter() + OTEL_EXPORTER_OTLP_ENDPOINT) —
// no change to the agent code.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.ComponentModel;
using System.Diagnostics;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using OpenAI;
using OpenAI.Chat;
using OpenTelemetry;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
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

[Description("Current weather for a city.")]
object GetWeather(string city) => new { city, temp_c = 22, sky = "sunny" };

AIAgent agent = chatClient.AsAIAgent(name: "WeatherAgent", instructions: "Use the tool. One sentence.",
                                     tools: [AIFunctionFactory.Create(GetWeather, "get_weather")]);

const string Source = "bsgai-lab3";   // the ActivitySource name our spans are emitted under
TracerProvider? tracing = null;
// TODO 3: switch tracing on: wrap the agent with UseOpenTelemetry (with sensitive data, so tool arguments show up) and let an OpenTelemetry tracer provider export our source with OneLinePerSpan
throw new NotImplementedException("TODO 3: switch tracing on: wrap the agent with UseOpenTelemetry (with sensitive data, so tool arguments show up) and let an OpenTelemetry tracer provider export our source with OneLinePerSpan");

Console.WriteLine((await agent.RunAsync("Weather in Mannheim?")).Text.Trim());
tracing?.ForceFlush();                                  // spans are exported in batches - flush before exit
tracing?.Dispose();

// One line per finished span: name, duration, token usage (chat spans), tool arguments (execute_tool spans).
sealed class OneLinePerSpan : BaseExporter<Activity>
{
    public override ExportResult Export(in Batch<Activity> batch)
    {
        foreach (Activity span in batch)
        {
            string tokens = span.GetTagItem("gen_ai.usage.input_tokens") is { } input
                ? $"  tokens in={input} out={span.GetTagItem("gen_ai.usage.output_tokens")}" : "";
            string toolArgs = span.GetTagItem("gen_ai.tool.call.arguments") is { } args
                ? $"  args={string.Join(' ', $"{args}".Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries))}" : "";
            string name = span.DisplayName.Split('(')[0];   // "invoke_agent WeatherAgent(<agent id>)" -> without the id
            Console.WriteLine($"  span {name,-34} {span.Duration.TotalMilliseconds,8:F0} ms{tokens}{toolArgs}");
        }
        return ExportResult.Success;
    }
}

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
