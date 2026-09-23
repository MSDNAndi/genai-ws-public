#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:package Microsoft.Agents.AI@1.22.0
#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:property PublishAot=false

// %% [markdown]
// # 06 - Agents as tools (supervisor / hierarchical, C#)
//
// | | |
// |---|---|
// | **Pattern** | supervisor: one orchestrator agent delegates sub-tasks to specialist agents |
// | **Communication** | **encapsulated function call** - a sub-agent gets only a task string and returns only an answer |
// | **Use when** | the orchestrator must stay in charge; sub-agents need clean, small contexts |
// | **Watch out** | the orchestrator only knows what the sub-agent chose to return |
//
// Twin of `python/06_maf_agent_as_tool.py`. `AsAIFunction()` turns an agent into
// an `AIFunction` - the same type as any tool from `AIFunctionFactory.Create`.
//
// ```bash
// dotnet run 06_maf_agent_as_tool.cs -- --profile mock
// ```

// %%
using GenAIClass;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using OpenAI.Chat;

var profile = Providers.GetProfile(args: args);
Console.WriteLine(profile);
ChatClient chatClient = Providers.CreateClient(profile).GetChatClient(profile.Model);

// %% [markdown]
// ## Two specialists, turned into tools
//
// The agent's `name` and `description` become the function's name and
// description - that is all the orchestrator sees, so write them like a job ad.

// %%
AIAgent researcher = chatClient.AsAIAgent(
    instructions: "You are a researcher. Answer factual questions in three bullet points.",
    name: "research",
    description: "Look up facts about a topic, place, product or company.");
AIAgent calculator = chatClient.AsAIAgent(
    instructions: "You are a calculator. Do the arithmetic step by step, give the number.",
    name: "calculate",
    description: "Do arithmetic: totals, percentages, costs, unit conversions.");

AIAgent orchestrator = chatClient.AsAIAgent(
    instructions: "You are a planning assistant. Delegate facts to `research` and numbers to " +
                  "`calculate`, then combine their answers into one short reply.",
    name: "orchestrator",
    tools: [researcher.AsAIFunction(), calculator.AsAIFunction()]);

// %% [markdown]
// ## One question, two delegations
//
// Each function result is a whole sub-agent run, compressed into one string.
// Note the sub-agents' context counters: they never see the orchestrator's
// conversation - the isolation is the point.

// %%
AgentResponse response = await orchestrator.RunAsync(
    "Research the facts about Lisbon for a trip, and calculate the cost of 4 nights at 120 EUR plus 15 percent tax.");

foreach (var content in response.Messages.SelectMany(m => m.Contents))
{
    if (content is FunctionCallContent call)
        Console.WriteLine($"  -> delegates to {call.Name}");
    else if (content is FunctionResultContent result)
        Console.WriteLine($"  <- result: {result.Result?.ToString()?[..Math.Min(90, result.Result.ToString()!.Length)]}");
}
Console.WriteLine($"\nfinal: {response.Text}");
