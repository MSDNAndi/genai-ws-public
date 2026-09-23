#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:package Microsoft.Agents.AI@1.22.0
#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package Microsoft.Agents.AI.Workflows@1.22.0
#:property PublishAot=false

// %% [markdown]
// # 04 - Handoff (triage and routing, C#)
//
// | | |
// |---|---|
// | **Pattern** | handoff: an agent decides who should own the conversation next |
// | **Communication** | **control transfer** - the model calls a handoff function and the target takes over |
// | **Use when** | triage -> specialist, escalation, "let me put you through" |
// | **Watch out** | routing is a model decision and can be wrong; the `Description` of each agent *is* the routing rule |
//
// Twin of `python/04_maf_handoff.py`, with two real differences (verified on 1.22):
//
// * **Each user turn is a new run that starts at the triage agent again.** You
//   carry the history forward yourself, and triage re-routes using it. The
//   Python version keeps the workflow alive, so turn 2 goes straight to the
//   specialist who already owns the conversation.
// * **Handoff functions are numbered** (`handoff_to_1`, `handoff_to_2`), not
//   named after the agent. The target's `Description` is the *only* routing
//   signal the model gets - write it carefully.
//
// ```bash
// dotnet run 04_maf_handoff.cs -- --profile mock
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
// ## The agents
//
// `Description` becomes the description of the handoff function the triage
// agent sees. `RequirePerServiceCallChatHistoryPersistence` keeps each agent's
// local history consistent when a handoff short-circuits a tool call - the
// Python builder refuses to run without its equivalent, so set it here too.

// %%
AIAgent Specialist(string name, string instructions, string description) =>
    chatClient.AsAIAgent(new ChatClientAgentOptions
    {
        Name = name,
        Description = description,
        ChatOptions = new() { Instructions = instructions },
        RequirePerServiceCallChatHistoryPersistence = true,
    });

AIAgent triage = Specialist("triage", "You are the front desk. Route every request to the right team.",
                            "Front desk that routes requests");
AIAgent billing = Specialist("billing", "You are billing support. Resolve invoice and payment issues.",
                             "Billing: invoices, payments, refunds, charges");
AIAgent tech = Specialist("tech", "You are technical support. Resolve login, error and outage issues.",
                          "Technical: login problems, errors, outages, bugs");

Workflow workflow = AgentWorkflowBuilder.CreateHandoffBuilderWith(triage)
    .WithHandoffs(triage, [billing, tech])   // triage may route to either specialist
    .WithHandoffs([billing, tech], triage)   // specialists may hand back, not sideways
    .Build();

// %% [markdown]
// ## A two-turn conversation
//
// Each turn: run the workflow on the whole history, print who spoke, keep the
// new messages. The handoff itself shows up as a function call in the stream.

// %%
async Task<List<ChatMessage>> TurnAsync(List<ChatMessage> history)
{
    await using StreamingRun run = await InProcessExecution.RunStreamingAsync(workflow, history);
    await run.TrySendMessageAsync(new TurnToken(emitEvents: true));

    string? speaker = null;
    await foreach (WorkflowEvent evt in run.WatchStreamAsync())
    {
        if (evt is AgentResponseUpdateEvent update)   // must come before WorkflowOutputEvent
        {
            var name = update.ExecutorId.Split('_')[0];
            if (name != speaker) { speaker = name; Console.Write($"\n[{speaker}] "); }
            Console.Write(update.Update.Text);
            foreach (var call in update.Update.Contents.OfType<FunctionCallContent>())
                Console.Write($"(calls {call.Name})");
        }
        else if (evt is WorkflowOutputEvent output)
        {
            Console.WriteLine();
            return output.As<List<ChatMessage>>() ?? [];
        }
    }
    return [];
}

List<ChatMessage> history = [new(ChatRole.User, "My invoice looks wrong.")];
history = await TurnAsync(history);

Console.WriteLine("[user] The charge appears twice, on the 3rd and the 4th.");
history.Add(new(ChatRole.User, "The charge appears twice, on the 3rd and the 4th."));
history = await TurnAsync(history);
