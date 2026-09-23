#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:package Microsoft.Agents.AI@1.22.0
#:package Microsoft.Agents.AI.OpenAI@1.22.0
#:property PublishAot=false

// %% [markdown]
// # 01 - One agent (Microsoft Agent Framework, C#)
//
// | | |
// |---|---|
// | **Pattern** | single agent: instructions + tools + memory |
// | **Communication** | request/response; conversation state held in an `AgentSession` |
// | **Use when** | one job, one persona. Start here and only add agents when this breaks |
// | **Watch out** | a session is memory you pay for - every turn resends the whole history |
//
// Twin of `python/01_maf_agent.py`. An `AIAgent` is sample
// `01-foundations/csharp/05_extensions_ai.cs` - an `IChatClient` with function
// invocation - plus instructions, a name and a session.
//
// ```bash
// dotnet run 01_maf_agent.cs -- --profile mock
// ```

// %%
using System.ComponentModel;
using GenAIClass;
using Microsoft.Agents.AI;
using Microsoft.Extensions.AI;
using OpenAI.Chat;

var profile = Providers.GetProfile(args: args);
Console.WriteLine(profile);

// The only provider-specific line: an OpenAI-compatible ChatClient for the profile.
ChatClient chatClient = Providers.CreateClient(profile).GetChatClient(profile.Model);

// %% [markdown]
// ## Tools are plain methods
//
// `AIFunctionFactory.Create` reads the signature and the `[Description]`
// attributes and builds the JSON schema you wrote by hand in Segment 1.

// %%
[Description("How far it is and how long it takes to drive between two places.")]
static object GetRoute([Description("Start, e.g. Bellevue, WA")] string origin,
                       [Description("End, e.g. Redmond, WA")] string destination)
    => new { origin, destination, distance_km = 42.0, duration_min = 35 };

[Description("Current weather conditions for one place.")]
static object GetCurrentWeather([Description("City and region")] string location)
    => new { location, temperature_c = 18, conditions = "light rain" };

AIAgent agent = chatClient.AsAIAgent(
    instructions: "You are a travel assistant. Use the tools; never guess numbers. Be brief.",
    name: "travel",
    // Name tools explicitly: local functions in a top-level program get
    // compiler-mangled names ("_Main_g_GetRoute_0_0") that the model would see.
    tools: [AIFunctionFactory.Create(GetRoute, name: "get_route"),
            AIFunctionFactory.Create(GetCurrentWeather, name: "get_current_weather")]);

// %% [markdown]
// ## 1. One call - the loop runs inside
//
// `response.Messages` is the loop, recorded: tool calls out, results back, answer.

// %%
Console.WriteLine("--- 1. one call");
AgentResponse response = await agent.RunAsync("How far is Bellevue to Redmond, and what is the weather there?");
foreach (var message in response.Messages)
    Console.WriteLine($"  {message.Role,-9} {(string.IsNullOrEmpty(message.Text) ? "[tool call]" : message.Text[..Math.Min(90, message.Text.Length)])}");
Console.WriteLine($"\nanswer: {response.Text}");

// %% [markdown]
// ## 2. Memory is a session, and you choose to keep one
//
// Without a session every `RunAsync` starts from nothing. With one, the framework
// replays the history - which is also the cost. (`GetNewThread` from older
// samples is now `CreateSessionAsync`.)

// %%
Console.WriteLine("\n--- 2. memory");
AgentSession session = await agent.CreateSessionAsync();
await agent.RunAsync("My name is Ada and I live in Redmond.", session);
AgentResponse remembered = await agent.RunAsync("Where do I live?", session);
AgentResponse forgotten = await agent.RunAsync("Where do I live?");
Console.WriteLine($"with session   : {remembered.Text}");
Console.WriteLine($"without session: {forgotten.Text}");

// %% [markdown]
// ## 3. Streaming

// %%
Console.WriteLine("\n--- 3. streaming");
await foreach (var update in agent.RunStreamingAsync("Say hello in five words."))
    Console.Write(update.Text);
Console.WriteLine();
