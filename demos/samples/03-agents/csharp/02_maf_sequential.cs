#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:package Microsoft.Agents.AI@1.22.0
#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package Microsoft.Agents.AI.Workflows@1.22.0
#:property PublishAot=false

// %% [markdown]
// # 02 - Sequential pipeline (C#)
//
// | | |
// |---|---|
// | **Pattern** | sequential: A -> B -> C, fixed order, each step refines the last |
// | **Communication** | the **conversation is handed down the chain** - every agent sees everything before it |
// | **Use when** | the steps are known up front: draft -> review -> translate |
// | **Watch out** | context grows at every hop, and a bad early step poisons everything after it |
//
// Twin of `python/02_maf_sequential.py`.
//
// ```bash
// dotnet run 02_maf_sequential.cs -- --profile mock
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

// %% [markdown]
// ## Build one workflow per conversation
//
// A built workflow carries the state of the runs it has seen. Build a fresh one
// per conversation (see the Python twin for the measured effect).

// %%
Workflow BuildWorkflow() => AgentWorkflowBuilder.BuildSequential(
[
    chatClient.AsAIAgent("You are a copywriter. Write one punchy product slogan.", "writer"),
    chatClient.AsAIAgent("You are an editor. Tighten the slogan above; return only the new slogan.", "editor"),
    chatClient.AsAIAgent("You are a translator. Translate the final slogan into German.", "translator"),
]);

// %% [markdown]
// ## Run it and watch the hand-offs
//
// Agent workflows in C# wait for a `TurnToken` before the agents start - it is
// the "your turn" signal, and `emitEvents: true` asks for streaming updates.
// `AgentResponseUpdateEvent.ExecutorId` tells you who is speaking right now.

// %%
List<ChatMessage> input = [new(ChatRole.User, "A reusable water bottle that tracks hydration.")];

await using StreamingRun run = await InProcessExecution.RunStreamingAsync(BuildWorkflow(), input);
await run.TrySendMessageAsync(new TurnToken(emitEvents: true));

string? speaker = null;
await foreach (WorkflowEvent evt in run.WatchStreamAsync())
{
    if (evt is AgentResponseUpdateEvent update)
    {
        if (update.ExecutorId != speaker)
        {
            speaker = update.ExecutorId;
            // Executor ids are "<agent name>_<guid>"; the name is what matters here.
            Console.Write($"\n-> [{speaker.Split('_')[0]}] ");
        }
        Console.Write(update.Update.Text);
    }
    else if (evt is WorkflowOutputEvent output)
    {
        var conversation = output.As<List<ChatMessage>>() ?? [];
        Console.WriteLine($"\n\nfinal conversation: {conversation.Count} messages, " +
                          $"last from {conversation.LastOrDefault()?.AuthorName}");
        break;
    }
}
