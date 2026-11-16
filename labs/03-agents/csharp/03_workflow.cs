#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package Microsoft.Agents.AI.Workflows@1.22.0
#:package ModelContextProtocol.Core@2.2.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// STARTER - complete the TODO block(s). The finished version is in solution/03_workflow.cs
// Lab 3 · step 3 — two agents, one workflow: a researcher (with the MCP tool) hands its notes to a writer.
//
// Workflow = fixed steps that YOU decide (researcher first, then writer) - no model picks the order. Each agent has
// one small job. What to notice: the writer has no tool; it only sees the researcher's notes in the shared conversation.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Diagnostics;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Workflows;
using Microsoft.Extensions.AI;
using ModelContextProtocol.Client;
using OpenAI;
using OpenAI.Chat;
#pragma warning disable OPENAI001 // ReasoningEffortLevel is still marked "experimental" in the OpenAI .NET SDK 2.13

// --- setup, the same in every Lab 3 file: find labs/, load labs/.env, connect to the model ---
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
// One chat client for all agents. GENAI_REASONING_EFFORT ("low" for gpt-5 models) rides along on every request; the
// gateway drops it for models that do not support it. RawRepresentationFactory = the OpenAI SDK's own request options.
IChatClient chatClient = new OpenAIClient(new ApiKeyCredential(key), clientOptions)
    .GetChatClient(Env("GENAI_MODEL")).AsIChatClient()
    .AsBuilder()
    .ConfigureOptions(o =>
    {
        if (effort != "") o.RawRepresentationFactory ??= _ => new ChatCompletionOptions { ReasoningEffortLevel = new(effort) };
    })
    .Build();
// --- end of setup ---

// The Lab 2 MCP server — always the finished C# one — started as a child process over stdio.
// McpClient = our side of the MCP connection; ListToolsAsync() asks the server which tools it has.
string server = Path.Combine(labs, "02-rag-mcp", "csharp", "solution", "04_mcp_server.cs");
if (!File.Exists(Path.Combine(labs, "02-rag-mcp", "build", "index.json")))
    throw new FileNotFoundException("The Lab 2 index is missing - run labs/02-rag-mcp/csharp/solution/02_embed.cs first.");
using (var build = Process.Start(new ProcessStartInfo("dotnet", ["build", server]) { RedirectStandardOutput = true })!)
{   // build first, then `run --no-build`: build output on stdout would corrupt the MCP protocol stream
    string log = await build.StandardOutput.ReadToEndAsync();
    await build.WaitForExitAsync();
    if (build.ExitCode != 0) throw new InvalidOperationException($"dotnet build {server} failed:\n{log}");
}
await using McpClient docs = await McpClient.CreateAsync(new StdioClientTransport(new StdioClientTransportOptions
{
    Name = "kestrel_docs", Command = "dotnet", Arguments = ["run", "--file", server, "--no-build"],
    ShutdownTimeout = TimeSpan.FromSeconds(1),   // SDK 2.2 waits this long for the server to quit on its own, then stops it
}));
IList<McpClientTool> docsTools = await docs.ListToolsAsync();

string task = "Customer question: 'My Standard delivery arrived 41 minutes late - what do I get, and why was it late?'";

AIAgent researcher, writer;
// TODO 1: create the researcher (uses the docs tools, returns cited facts only) and the writer (turns the facts into a friendly 80-word reply)
throw new NotImplementedException("TODO 1: create the researcher (uses the docs tools, returns cited facts only) and the writer (turns the facts into a friendly 80-word reply)");

// BuildSequential = run agents one after another; each sees the conversation so far and adds its turn.
// workflow.AsAIAgent(...) wraps the whole workflow as one agent, so we run it like any agent.
Workflow workflow = AgentWorkflowBuilder.BuildSequential(researcher, writer);
AgentResponse result = await workflow.AsAIAgent(name: "support-reply", includeExceptionDetails: true).RunAsync(task);
if (result.Messages.SelectMany(m => m.Contents).OfType<ErrorContent>().FirstOrDefault() is { } error)
    throw new InvalidOperationException($"workflow failed: {error.Message}");   // a failing step comes back as ErrorContent
// result.Messages = the whole conversation: the researcher's turns (with tool calls), then the writer's reply
foreach (var notes in result.Messages.Where(m => m.AuthorName == "researcher" && m.Text != ""))
    Console.WriteLine($"RESEARCHER NOTES:\n {Cut(notes.Text, 800)} \n");
Console.WriteLine($"WRITER:\n {result.Messages.Last().Text}");

static string Cut(string text, int max) => text.Length <= max ? text : text[..max];

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
