#:package Microsoft.Extensions.AI@10.10.0
#:package Microsoft.Extensions.AI.OpenAI@10.10.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 1 · step 3 — structured output: a JSON Schema is a contract, not a hope.
//
// What this shows: we describe the shape we want (a C# record), Microsoft.Extensions.AI (M.E.AI) turns it into a
// JSON Schema, the service forces the model's answer to fit it, and we get a typed object back — no regex, no
// "please answer in JSON". What to notice: you can do maths on the result (total minutes) because the fields are ints.
// The OpenAI .NET SDK has no typed "parse" helper; M.E.AI's IChatClient (the layer Agent Framework builds on) has one.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.ComponentModel;
using System.Text.Json;
using Microsoft.Extensions.AI;
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
// AsIChatClient(): wrap the OpenAI client in M.E.AI's vendor-neutral interface
IChatClient client = new OpenAIClient(new ApiKeyCredential(key), clientOptions).GetChatClient(model).AsIChatClient();
// "strict": the service must follow the schema exactly (constrained decoding) — the Python SDK's parse() sends it too.
var options = new ChatOptions { AdditionalProperties = new() { ["strict"] = true } };
// Optional "think less" knob (GENAI_REASONING_EFFORT=low); only sent when set (see step 1).
// ChatOptions is provider-neutral (ChatOptions.Reasoning knows low/medium/high/none); RawRepresentationFactory hands the
// OpenAI SDK its own options object, so any value the service accepts ("minimal" too) goes through unchanged.
if (Env("GENAI_REASONING_EFFORT", "") is { Length: > 0 } effort)
    options.RawRepresentationFactory = _ => new ChatCompletionOptions { ReasoningEffortLevel = new ChatReasoningEffortLevel(effort) };

// The free text we want to turn into data.
const string Text = "Tomorrow at 10:50 the second segment starts: a 40-minute talk called 'The context window is the product', " +
                    "covering embeddings, RAG, MCP and prompt injection, followed by a 30-minute hands-on lab.";
// snake_case names in the schema and the output (talk_minutes ...), exactly like the Python version
var json = new JsonSerializerOptions(JsonSerializerOptions.Web) { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower, WriteIndented = true };

// ---- 2. The call: GetResponseAsync<Session> sends the schema and turns the JSON answer into a Session ----
ChatResponse<Session> completion;
// >>> TODO 1: ask for a Session - client.GetResponseAsync<Session>(messages, json, options) turns the record at the bottom into a JSON Schema and parses the reply into it
completion = await client.GetResponseAsync<Session>(
[
    new(ChatRole.System, "Extract the session described by the user."),
    new(ChatRole.User, Text),
], json, options);
// <<< TODO

// ---- 3. What came back: a real object, not a string ----
bool ok = completion.TryGetResult(out Session? session);      // a real Session instance (false if the model refused)
Console.WriteLine(ok ? JsonSerializer.Serialize(session, json) : completion.Text);
JsonElement schema = AIJsonUtilities.CreateJsonSchema(typeof(Session), serializerOptions: json);
Console.WriteLine("\nThe JSON Schema that was sent: [" +
                  string.Join(", ", schema.GetProperty("properties").EnumerateObject().Select(p => $"'{p.Name}'")) + "]");
Console.WriteLine(ok ? $"Total minutes: {session!.TalkMinutes + session.LabMinutes}" : "");   // ints, so + is maths

// Try this: add `string? Room` or an enum property (Level: Beginner/Advanced) to the record and see what the model does
// with information that is NOT in the text.

// ---- 4. The shape we want back (C# wants types at the bottom of the file) ----
// Property names, types and [Description]s all end up in the JSON Schema the model sees.
record Session(
    string Title,
    [property: Description("start time as HH:MM")] string Start,
    int TalkMinutes,
    int LabMinutes,
    List<string> Topics);

// Plumbing (same in every file): adds the "api-key" header to every request. You can skip reading this.
sealed class HeaderPolicy(string name, string value) : PipelinePolicy
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
