#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:package Microsoft.Agents.AI@1.22.0
#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package Microsoft.Agents.AI.Workflows@1.22.0
#:property PublishAot=false

// %% [markdown]
// # 03 - Concurrent fan-out / fan-in (C#)
//
// | | |
// |---|---|
// | **Pattern** | concurrent: the same input goes to N agents at once, results are aggregated |
// | **Communication** | **broadcast** in, **aggregate** out - the agents never see each other |
// | **Use when** | independent perspectives: review panels, multi-source research, voting |
// | **Watch out** | N agents = N times the cost; the aggregator is where quality is decided |
//
// Twin of `python/03_maf_concurrent.py`.
//
// ```bash
// dotnet run 03_maf_concurrent.cs -- --profile mock
// ```

// %%
using GenAIClass;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Workflows;
using Microsoft.Extensions.AI;
using OpenAI.Chat;
using ChatMessage = Microsoft.Extensions.AI.ChatMessage;

var profile = Providers.GetProfile(args: args);
Console.WriteLine(profile);
ChatClient chatClient = Providers.CreateClient(profile).GetChatClient(profile.Model);

const string Idea = "Replace our support hotline with an AI agent next quarter.";

AIAgent[] Panel() =>
[
    chatClient.AsAIAgent("You are an optimist. Give the strongest case FOR the idea in two sentences.", "optimist"),
    chatClient.AsAIAgent("You are a skeptic. Give the strongest case AGAINST the idea in two sentences.", "skeptic"),
    chatClient.AsAIAgent("You are a finance lead. Estimate cost and payback in two sentences.", "finance"),
];

// %% [markdown]
// ## The aggregator is a function over everyone's answers
//
// `BuildConcurrent(agents, aggregator)`: the aggregator receives one message
// list per agent and returns the workflow's output. Here a judge agent decides;
// a vote count or a merge would be just as valid. Without an aggregator you get
// the raw panel back.

// %%
AIAgent judge = chatClient.AsAIAgent("You are the decision maker. Weigh the panel and give a go/no-go in one line.", "judge");

List<ChatMessage> Judge(IList<List<ChatMessage>> answers)
{
    var panel = string.Join("\n", answers.Select(a => a.LastOrDefault()).Where(m => m is not null)
                                         .Select(m => $"{m!.AuthorName}: {m.Text}"));
    // The aggregator is synchronous here; keep the judge call short.
    var verdict = judge.RunAsync($"Idea: {Idea}\n\nPanel:\n{panel}").GetAwaiter().GetResult();
    return [new ChatMessage(ChatRole.Assistant, verdict.Text) { AuthorName = "judge" }];
}

async Task RunAsync(Workflow workflow, string title)
{
    Console.WriteLine($"\n--- {title}");
    await using StreamingRun run = await InProcessExecution.RunStreamingAsync(
        workflow, new List<ChatMessage> { new(ChatRole.User, Idea) });
    await run.TrySendMessageAsync(new TurnToken(emitEvents: true));

    await foreach (WorkflowEvent evt in run.WatchStreamAsync())
    {
        // Trap (verified on 1.22): AgentResponseUpdateEvent *derives from*
        // WorkflowOutputEvent. Test the specific type first, or the first
        // streamed token matches "output", carries no message list, and the
        // loop exits early with the workflow still running.
        if (evt is AgentResponseUpdateEvent)
            continue;
        if (evt is WorkflowOutputEvent output)
        {
            foreach (var message in output.As<List<ChatMessage>>() ?? [])
                if (message.Role == ChatRole.Assistant)
                    Console.WriteLine($"  {message.AuthorName,-9} {message.Text[..Math.Min(100, message.Text.Length)]}");
            break;
        }
    }
}

await RunAsync(AgentWorkflowBuilder.BuildConcurrent(Panel()), "1. default aggregation (the raw panel)");
await RunAsync(AgentWorkflowBuilder.BuildConcurrent(Panel(), Judge), "2. custom aggregator (a judge decides)");
