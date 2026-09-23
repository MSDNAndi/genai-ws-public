#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package ModelContextProtocol.Core@2.2.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 3 · step 2 — give the agent the Lab 2 documents through MCP. No adapter code: an MCP server IS a tool source.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Diagnostics;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using ModelContextProtocol.Client;
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
IList<McpClientTool> docsTools = await docs.ListToolsAsync();   // McpClientTool IS an AIFunction: tools only, no prompts

AIAgent agent = chatClient.AsAIAgent(
    name: "KestrelSupport",
    tools: [.. docsTools],
    instructions: "You answer questions about Kestrel Drone Logistics. Always call search_docs first and cite the chunk ids " +
                  "you used, like (kestrel_operations_handbook#2). If the documents do not answer the question, say so.");

foreach (string question in new[] { "Can I fly a K-2 Sparrow at night at 100 m?",
                                    "My payload was lost in August. How quickly will someone call me, and what do I get?" })
{
    AgentResponse response = await agent.RunAsync(question);
    Console.WriteLine($"> {question}\n  {response.Text.Trim()}\n");
}

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
