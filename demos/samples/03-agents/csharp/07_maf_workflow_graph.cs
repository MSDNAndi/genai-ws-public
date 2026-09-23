#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:package Microsoft.Agents.AI@1.22.0
#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:package Microsoft.Agents.AI.Workflows@1.22.0
#:property PublishAot=false

// %% [markdown]
// # 07 - An explicit workflow graph (C#)
//
// | | |
// |---|---|
// | **Pattern** | graph / state machine: you draw the nodes and edges, including conditional branches |
// | **Communication** | **typed messages along edges** - each node sends a value of a declared type to the next |
// | **Use when** | the process is known and must be auditable; only *some* steps need a model |
// | **Watch out** | more code than an orchestration builder; that is the price of determinism |
//
// Twin of `python/07_maf_workflow_graph.py`. A deterministic spine, with a
// model called only where judgement is needed. Your `AddCase` predicates decide
// the control flow, not the model.
//
// ```
//                 +--> [urgent]  (code)  ---> output
//   [classify] ---+
//     (code)      +--> [draft_reply] (agent) -> output
// ```
//
// ```bash
// dotnet run 07_maf_workflow_graph.cs -- --profile mock
// ```

// %%
using System.Text.RegularExpressions;
using GenAIClass;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Workflows;
using OpenAI.Chat;

var profile = Providers.GetProfile(args: args);
Console.WriteLine(profile);
ChatClient chatClient = Providers.CreateClient(profile).GetChatClient(profile.Model);

// %% [markdown]
// ## Nodes: two plain functions and one agent
//
// Any delegate becomes a node with `.BindAsExecutor("id")`. Its input and
// output types are the message types on its edges - checked when the workflow
// is built, not at 3 a.m. in production.

// %%
Func<string, Ticket> classify = text =>
    new(text, Regex.IsMatch(text, @"\b(outage|down|urgent|security|breach)\b", RegexOptions.IgnoreCase));

// No model on the urgent path: it must be fast, predictable and paged to a human.
Func<Ticket, string> escalate = ticket => $"PAGED ON-CALL: {ticket.Text}";

AIAgent replier = chatClient.AsAIAgent("You are a support agent. Draft a two-sentence friendly reply.", "draft_reply");
Func<Ticket, ValueTask<string>> draftReply = async ticket => $"DRAFT: {(await replier.RunAsync(ticket.Text)).Text}";

// %% [markdown]
// ## Edges: the control flow is data, not a prompt
//
// `AddSwitch` routes on the message: first matching `AddCase` wins,
// `WithDefault` catches the rest. `WithOutputFrom` marks which nodes produce
// the workflow's result.

// %%
Workflow BuildWorkflow()
{
    var classifyNode = classify.BindAsExecutor("classify");
    var urgentNode = escalate.BindAsExecutor("urgent");
    var draftNode = draftReply.BindAsExecutor("draft_reply");

    return new WorkflowBuilder(classifyNode)
        .AddSwitch(classifyNode, sw => sw
            .AddCase<Ticket>(t => t!.Urgent, [urgentNode])
            .WithDefault([draftNode]))
        .WithOutputFrom(urgentNode, draftNode)
        .Build();
}

foreach (var text in new[] { "Our whole site is down since 09:00!", "How do I change my invoice address?" })
{
    await using StreamingRun run = await InProcessExecution.RunStreamingAsync(BuildWorkflow(), text);
    await foreach (WorkflowEvent evt in run.WatchStreamAsync())
    {
        if (evt is WorkflowOutputEvent output)
        {
            var result = output.As<string>() ?? "";
            Console.WriteLine($"{text,-40} -> {result[..Math.Min(90, result.Length)]}");
            break;
        }
    }
}

// The message type that travels along the edges.
record Ticket(string Text, bool Urgent);
