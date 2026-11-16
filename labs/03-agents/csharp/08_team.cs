#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package ModelContextProtocol.Core@2.2.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// STARTER - complete the TODO block(s). The finished version is in solution/08_team.cs
// Lab 3 · stretch — a team of four agents on four vendors' models, one endpoint.
//
//     lead (plans) --> policy analyst --+--> fact-checker --> lead (merges the incident review)
//                      comms writer ----+   (in parallel)
//
// The policy analyst looks up the rules in the Kestrel docs (the Lab 2 MCP server), the comms writer drafts the
// customer message at the same time (no tool - on purpose), the fact-checker holds the draft against the docs, and the
// lead merges everything. Every agent runs on a different vendor's model - same client class, same endpoint, only the
// model name changes (override with TEAM_LEAD_MODEL, TEAM_POLICY_MODEL, TEAM_COMMS_MODEL, TEAM_CHECKER_MODEL).
//
// Team = specialists with different jobs (and models); policy and comms run in PARALLEL, the rest one after another.
// What to notice: agreement is not correctness - check the 09:05 arrival against the docs yourself.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Diagnostics;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using ModelContextProtocol.Client;
using OpenAI;
using OpenAI.Chat;
#pragma warning disable OPENAI001 // ReasoningEffortLevel is still marked "experimental" in the OpenAI .NET SDK 2.13

// --- setup, the same in every Lab 3 file: find labs/, load labs/.env, connect to the model ---
var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))    // walk up to the labs/ root
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));   // labs/.env; real environment variables win
static string Env(string name, string? fallback = null) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
    ? value : fallback ?? throw new InvalidOperationException($"{name} is not set - copy labs/.env.example to labs/.env");

var models = new Dictionary<string, string>   // defaults - every one can be overridden from the environment
{
    ["lead"] = Env("TEAM_LEAD_MODEL", "gpt-5-nano"),
    ["policy"] = Env("TEAM_POLICY_MODEL", "DeepSeek-V4.1-Flash-1017"),
    ["comms"] = Env("TEAM_COMMS_MODEL", "Llama-4-Maverick-17B-128E-Instruct-FP8"),
    ["checker"] = Env("TEAM_CHECKER_MODEL", "grok-4-1-fast-non-reasoning"),
};
string key = Env("GENAI_API_KEY"), effort = Env("GENAI_REASONING_EFFORT", "low");
var clientOptions = new OpenAIClientOptions { Endpoint = new Uri(Env("GENAI_BASE_URL")) };
if ((Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key")
    clientOptions.AddPolicy(new HeaderPolicy("api-key", key), PipelinePosition.PerCall);
var openai = new OpenAIClient(new ApiKeyCredential(key), clientOptions);
// --- end of setup ---

// One chat client per model. reasoning_effort only means something for reasoning models, so only they get it
// (the gateway drops it for the others anyway).
IChatClient ClientFor(string model)
{
    bool reasoning = model.StartsWith("gpt-5") || model.StartsWith("gpt-oss") || model.StartsWith("o3") || model.StartsWith("o4");
    return openai.GetChatClient(model).AsIChatClient().AsBuilder()
        .ConfigureOptions(o =>
        {
            if (reasoning) o.RawRepresentationFactory ??= _ => new ChatCompletionOptions { ReasoningEffortLevel = new(effort) };
        })
        .Build();
}
// One team member: its own model (lead_plan and lead_merge both use models["lead"]), its job, its tools.
AIAgent Member(string name, string instructions, IList<AITool>? tools = null) =>
    ClientFor(models[name.Split('_')[0]]).AsAIAgent(name: name, instructions: instructions, tools: tools);

// Run() = agent.RunAsync plus a stopwatch: one ledger row per agent run (who, which model, how long, how many tokens)
var ledger = new List<(string Agent, string Model, double Sec, long In, long Out)>();
async Task<string> Run(AIAgent agent, string input)
{
    var sw = Stopwatch.StartNew();
    AgentResponse response = await agent.RunAsync(input);
    // lock: policy and comms may finish at the same moment
    lock (ledger) ledger.Add((agent.Name!, models[agent.Name!.Split('_')[0]], sw.Elapsed.TotalSeconds,
                              response.Usage?.InputTokenCount ?? 0, response.Usage?.OutputTokenCount ?? 0));
    return response.Text.Trim();
}

string incident = """
    Ops log, 16 Nov 2026, 07:10, Heidelberg. A K-7 Heron took off in light rain with a 5.1 kg parcel
    (Standard delivery, window 06:00-08:00). Shortly after take-off it reported low lift, aborted and made an emergency
    landing in a field. Nobody was hurt; the parcel was damaged. A replacement parcel arrived at 09:05.
    The customer (Ms. Weber) has complained on social media.
    """;

Console.WriteLine("Team: " + string.Join(", ", models.Select(m => $"{m.Key}={m.Value}")) + "\n");
var total = Stopwatch.StartNew();

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
    ShutdownTimeout = TimeSpan.FromSeconds(1),
}));
IList<AITool> docsTools = [.. await docs.ListToolsAsync()];
double setup = total.Elapsed.TotalSeconds;

AIAgent leadPlan = Member("lead_plan", "You lead an incident review at Kestrel Drone Logistics. Split the job for your " +
    "team: write ONE short task line each for the POLICY ANALYST (which rules, incident code, escalation and customer " +
    "entitlements to look up) and the COMMS WRITER (the message to the customer). Max 60 words. No answers yourself.");
AIAgent policy = Member("policy", "You are the policy analyst. Use search_docs (2-3 searches). Return at most 6 bullets: " +
    "which rule was broken, the incident code, who must be told within what time, what the customer is entitled to. " +
    "Each bullet ends with its chunk id. No prose.", docsTools);
AIAgent comms = Member("comms", "You are the comms writer. Write the message to the customer about the incident: " +
    "apologetic, honest, plain language, at most 90 words. You have no documents - do not invent numbers or " +
    "compensation you were not given. Reply with the message only.");
AIAgent checker;
// TODO 1: the fact-checker - holds the comms draft against the docs (search_docs) and lists what is wrong or missing
throw new NotImplementedException("TODO 1: the fact-checker - holds the comms draft against the docs (search_docs) and lists what is wrong or missing");
AIAgent leadMerge = Member("lead_merge", "You lead the incident review. Merge your team's work into the final review in " +
    "markdown: 1) what happened (2 lines), 2) rules broken and incident code, 3) escalation and deadlines, 4) the " +
    "customer message, rewritten in full (max 90 words) with the fact-checker's corrections. Max 250 words. Use only " +
    "facts from the team.");

// 1 · the lead splits the job
string plan = await Run(leadPlan, $"Incident:\n{incident}");
Console.WriteLine($"[lead] plan:\n{plan}\n");

// 2 · the two specialists work at the same time
string notes, draft;
// Start both runs first (they then run at the same time); Task.WhenAll waits until both are done.
// TODO 2: run policy and comms CONCURRENTLY on the same input (start both runs, then await both with Task.WhenAll)
throw new NotImplementedException("TODO 2: run policy and comms CONCURRENTLY on the same input (start both runs, then await both with Task.WhenAll)");
Console.WriteLine($"[policy] notes:\n{notes}\n\n[comms] draft:\n{draft}\n");

// 3 · the fact-checker reviews the draft, 4 · the lead merges everything
string check = await Run(checker, $"Policy notes:\n{notes}\n\nCustomer message draft:\n{draft}");
Console.WriteLine($"[checker] findings:\n{check}\n");
string review = await Run(leadMerge, $"Incident:\n{incident}\n\nPolicy notes:\n{notes}\n\nCustomer message draft:\n" +
                                     $"{draft}\n\nFact-checker:\n{check}");
Console.WriteLine(new string('=', 80) + $"\nINCIDENT REVIEW\n{review}\n" + new string('=', 80));

Console.WriteLine($"\n{"agent",-11} {"model",-40} {"sec",6} {"tok in",7} {"tok out",8}");
foreach (var r in ledger) Console.WriteLine($"{r.Agent,-11} {r.Model,-40} {r.Sec,6:F1} {r.In,7} {r.Out,8}");
Console.WriteLine($"{"(setup)",-11} {"MCP server build + start",-40} {setup,6:F1}");
Console.WriteLine($"{"total",-11} {"(wall clock - policy+comms ran in parallel)",-40} {total.Elapsed.TotalSeconds,6:F1} " +
                  $"{ledger.Sum(r => r.In),7} {ledger.Sum(r => r.Out),8}");

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
