#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:package Microsoft.Agents.AI@1.22.0
#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package Microsoft.Agents.AI.Workflows@1.22.0
#:property PublishAot=false

// %% [markdown]
// # 05 - Group chat (shared transcript, C#)
//
// | | |
// |---|---|
// | **Pattern** | group chat: several agents take turns in one conversation, a manager picks who speaks |
// | **Communication** | **shared blackboard** - everyone reads the whole transcript and writes to it |
// | **Use when** | iterative refinement between roles: writer + critic, planner + reviewer |
// | **Watch out** | it can loop forever politely agreeing; always cap the iterations |
//
// Twin of `python/05_maf_group_chat.py`.
//
// ```bash
// dotnet run 05_maf_group_chat.cs -- --profile mock
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

AIAgent writer = chatClient.AsAIAgent("You are a writer. Draft or revise a tagline for the product in the chat.", "writer");
AIAgent critic = chatClient.AsAIAgent("You are a critic. Name the single biggest weakness of the latest tagline.", "critic");

// %% [markdown]
// ## The manager decides who speaks
//
// `RoundRobinGroupChatManager` takes turns in order - deterministic and free.
// Subclass `GroupChatManager` for an LLM-driven one that reads the transcript
// and picks. `MaximumIterationCount` is the circuit breaker.

// %%
Workflow workflow = AgentWorkflowBuilder
    .CreateGroupChatBuilderWith(agents => new RoundRobinGroupChatManager(agents) { MaximumIterationCount = 4 })
    .AddParticipants(writer, critic)
    .Build();

// %% [markdown]
// ## Watch the transcript grow
//
// The context counter in each (mock) reply goes up every turn: each agent is
// sent everything said so far. That is the blackboard - and the cost curve.

// %%
await using StreamingRun run = await InProcessExecution.RunStreamingAsync(
    workflow, new List<ChatMessage> { new(ChatRole.User, "Product: a solar-powered bike lock.") });
await run.TrySendMessageAsync(new TurnToken(emitEvents: true));

string? speaker = null;
await foreach (WorkflowEvent evt in run.WatchStreamAsync())
{
    if (evt is AgentResponseUpdateEvent update)   // must come before WorkflowOutputEvent
    {
        var name = update.ExecutorId.Split('_')[0];
        if (name != speaker) { speaker = name; Console.Write($"\n[{speaker}] "); }
        Console.Write(update.Update.Text);
    }
    else if (evt is WorkflowOutputEvent output)
    {
        Console.WriteLine($"\n\ntranscript: {output.As<List<ChatMessage>>()?.Count} messages");
        break;
    }
}
