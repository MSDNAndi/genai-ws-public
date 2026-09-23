#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package Microsoft.Agents.AI.Workflows@1.22.0
#:package ModelContextProtocol.Core@2.2.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// STARTER - complete the TODO block(s). The finished version is in solution/04_critic.cs
// Lab 3 · step 4 — add a critic: researcher -> writer -> critic -> writer (revise), as a group chat with a fixed
// speaking order and a hard round limit. The critic can end it early by saying APPROVED.
// (No revision loop needed? AgentWorkflowBuilder.BuildSequential(researcher, writer, critic) is the one-liner.)
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Diagnostics;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Workflows;
using Microsoft.Extensions.AI;
using ModelContextProtocol.Client;
using OpenAI;
using OpenAI.Chat;
using ChatMessage = Microsoft.Extensions.AI.ChatMessage;   // OpenAI.Chat has a ChatMessage too
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

// The Lab 2 MCP server — always the finished C# one — started as a child process over stdio.
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

string task = "Write the FAQ entry: 'Can I send a 150 Wh power bank with Kestrel, and what happens if my parcel is lost?'";

AIAgent researcher = chatClient.AsAIAgent(name: "researcher", tools: [.. docsTools],
    instructions: "Collect the facts with search_docs. Bullet list with chunk ids.");
AIAgent writer = chatClient.AsAIAgent(name: "writer",
    instructions: "Write or revise the FAQ entry (max 90 words) from the researcher's facts and the critic's feedback.");
AIAgent critic = chatClient.AsAIAgent(name: "critic",
    instructions: "Check the latest FAQ draft against the researcher's facts. If it is correct, complete and under 90 words, " +
                  "reply only APPROVED. Otherwise list the fixes.");

// A group chat: every agent sees the whole conversation; our manager decides who speaks next and when to stop.
Workflow groupChat = AgentWorkflowBuilder
    .CreateGroupChatBuilderWith(_ => new CriticLoop(researcher, writer, critic) { MaximumIterationCount = 5 })
    .AddParticipants([researcher, writer, critic])
    .Build();
AgentResponse result = await groupChat.AsAIAgent(name: "faq-team", includeExceptionDetails: true).RunAsync(task);
if (result.Messages.SelectMany(m => m.Contents).OfType<ErrorContent>().FirstOrDefault() is { } error)
    throw new InvalidOperationException($"workflow failed: {error.Message}");   // a failing step comes back as ErrorContent

List<ChatMessage> drafts = [.. result.Messages.Where(m => m.AuthorName == "writer" && m.Text != "")];
Console.WriteLine($"speaking order: {string.Join(" -> ", result.Messages.Where(m => m.Text != "").Select(m => m.AuthorName))}");
Console.WriteLine($"{drafts.Count} writer draft(s). Final:\n{(drafts.Count > 0 ? drafts[^1].Text : "(none)")}");

sealed class CriticLoop(AIAgent researcher, AIAgent writer, AIAgent critic) : GroupChatManager
{
    // Called before every turn; IterationCount = number of turns so far (0 = the first one).
    // (Picking the agent that just spoke ends the chat - MAF's group chat never lets an agent answer itself.)
    protected override ValueTask<AIAgent> SelectNextAgentAsync(IReadOnlyList<ChatMessage> history, CancellationToken cancellationToken = default)
    {
        AIAgent next;
        // TODO 2: return who speaks next - round 0 (IterationCount == 0) the researcher, then writer and critic take turns
        throw new NotImplementedException("TODO 2: return who speaks next - round 0 (IterationCount == 0) the researcher, then writer and critic take turns");
        return ValueTask.FromResult(next);
    }

    // Stop after MaximumIterationCount turns — or as soon as the critic says APPROVED.
    protected override ValueTask<bool> ShouldTerminateAsync(IReadOnlyList<ChatMessage> history, CancellationToken cancellationToken = default) =>
        ValueTask.FromResult(IterationCount >= MaximumIterationCount ||
                             history.Any(m => m.AuthorName == "critic" && m.Text.Contains("APPROVED")));
}

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
