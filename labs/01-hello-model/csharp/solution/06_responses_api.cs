#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 1 · stretch — the Responses API: the newer dialect at OpenAI and Foundry (/openai/v1/responses).
//
// Differences to Chat Completions you can see here: input items + instructions instead of messages; server-side
// conversation state via PreviousResponseId; typed output items; streaming as semantic events.
// Works on Foundry and OpenAI. Local runners and gateways may only speak Chat Completions — that is why every
// other lab uses Chat Completions.
using System.ClientModel;
using System.ClientModel.Primitives;
using OpenAI;
using OpenAI.Responses;
#pragma warning disable OPENAI001 // the Responses client is still marked "experimental" in the OpenAI .NET SDK 2.13

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
ResponsesClient client = new OpenAIClient(new ApiKeyCredential(key), clientOptions).GetResponsesClient();
string effort = Env("GENAI_REASONING_EFFORT", "");

// One request = model + input items (+ instructions, previous response ...).
// The Responses API spells the reasoning knob differently: reasoning = { effort: ... }
CreateResponseOptions Request(string input)
{
    var request = new CreateResponseOptions { Model = model, InputItems = { ResponseItem.CreateUserMessageItem(input) } };
    if (effort != "") request.ReasoningOptions = new ResponseReasoningOptions { ReasoningEffortLevel = new ResponseReasoningEffortLevel(effort) };
    return request;
}

CreateResponseOptions firstRequest = Request("Name one advantage of running a model locally.");
firstRequest.Instructions = "Be brief.";
ResponseResult first = await client.CreateResponseAsync(firstRequest);
Console.WriteLine($"1: {first.GetOutputText()}");

// The service keeps the conversation: refer to the previous turn by id instead of resending the history.
// (Needs the endpoint to store responses; if yours does not, resend the history as input items instead.)
try
{
    CreateResponseOptions secondRequest = Request("And one disadvantage? Same length.");
    secondRequest.PreviousResponseId = first.Id;
    ResponseResult second = await client.CreateResponseAsync(secondRequest);
    Console.WriteLine($"2: {second.GetOutputText()}");
}
catch (Exception e)
{
    Console.WriteLine($"2: previous_response_id not supported here -> {Cut(e.Message.ReplaceLineEndings(" "), 120)}");
}

Console.Write("3 (streamed): ");
CreateResponseOptions streamRequest = Request("Count from 1 to 5, comma separated.");
streamRequest.StreamingEnabled = true;                  // the 2.13 SDK insists on this flag for the streaming call
await foreach (StreamingResponseUpdate update in client.CreateResponseStreamingAsync(streamRequest))
{
    if (update is StreamingResponseOutputTextDeltaUpdate delta) Console.Write(delta.Delta);   // one event type per kind of change
}
Console.WriteLine();

static string Cut(string text, int max) => text.Length <= max ? text : text[..max];

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
