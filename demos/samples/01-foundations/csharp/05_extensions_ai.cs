#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:property PublishAot=false

// %% [markdown]
// # 05 - The same loop through Microsoft.Extensions.AI
//
// `Microsoft.Extensions.AI` is the .NET abstraction over "a chat model":
// `IChatClient`, `IEmbeddingGenerator`, dependency injection, and middleware.
// Every serious .NET AI library sits on it - including Microsoft Agent
// Framework, whose agents wrap an `IChatClient`.
//
// Teach this before any agent framework. Once `IChatClient` is familiar, agent
// frameworks stop looking like magic and start looking like a loop plus policy.
//
// ```bash
// dotnet run 05_extensions_ai.cs -- --profile mock
// ```

// %%
using System.ComponentModel;
using GenAIClass;
using Microsoft.Extensions.AI;

var profile = Providers.GetProfile(args: args);
Console.WriteLine(profile);

// %% [markdown]
// ## One interface, any provider
//
// `Providers.CreateChatClient` is three lines: build the OpenAI client, get a
// chat client for the model, call `.AsIChatClient()`. The rest of your code now
// depends on an interface, not on a vendor SDK - swap in Ollama, Foundry or a
// test double without touching it.

// %%
IChatClient raw = Providers.CreateChatClient(profile);

ChatResponse response = await raw.GetResponseAsync(
[
    new ChatMessage(ChatRole.System, "You are a concise assistant. One sentence."),
    new ChatMessage(ChatRole.User, "Why is the sky blue?"),
]);

Console.WriteLine(response.Text);
Console.WriteLine($"tokens: {response.Usage?.TotalTokenCount}");

// %% [markdown]
// ## Tools without the plumbing
//
// In sample 04 you wrote the loop by hand: check the finish reason, parse the
// arguments, dispatch, append a tool message, repeat. `UseFunctionInvocation()`
// is a middleware that does exactly that, and `AIFunctionFactory.Create` builds
// the JSON schema from the method signature and its `[Description]` attributes.
//
// This is the same trade you make with every framework from here on: less code,
// less visibility. You now know what it is hiding.

// %%
[Description("Driving distance and duration between two places.")]
static object GetRoute(
    [Description("Start, e.g. Bellevue, WA")] string origin,
    [Description("End, e.g. Redmond, WA")] string destination)
    => new { origin, destination, distance_km = 42.0, duration_min = 35.0, source = "stub" };

[Description("Current weather conditions for one place.")]
static object GetCurrentWeather([Description("City and state")] string location)
    => new { location, temperature_c = 18, conditions = "light rain" };

IChatClient client = raw
    .AsBuilder()
    .UseFunctionInvocation()
    .Build();

var chatOptions = new ChatOptions
{
    // Name them explicitly: a local function in a top-level program has a
    // compiler-generated name (e.g. "_Main_g_GetRoute_0_0"), and without `name:`
    // that mangled string is the tool name the model sees.
    Tools = [AIFunctionFactory.Create(GetRoute, name: "get_route"),
             AIFunctionFactory.Create(GetCurrentWeather, name: "get_current_weather")],
};

ChatResponse answer = await client.GetResponseAsync(
    "How far is it from Bellevue, WA to Redmond, WA, and what is the weather there?",
    chatOptions);

Console.WriteLine(answer.Text);

// %% [markdown]
// ## What the middleware bought you
//
// | By hand (sample 04)                  | `UseFunctionInvocation()`              |
// |--------------------------------------|----------------------------------------|
// | write a JSON schema per tool         | generated from the method signature    |
// | parse `FunctionArguments` yourself   | bound to typed parameters              |
// | append `ToolChatMessage` with the id | handled                                |
// | your own `maxTurns` guard            | `MaximumIterationsPerRequest`          |
//
// Middleware composes, and that is the real point. The same builder chain takes
// `.UseDistributedCache(...)`, `.UseOpenTelemetry(...)` and
// `.UseLogging(...)` - caching, tracing and logging for any provider, added in
// one line each, because they are policy around an interface rather than
// features of a vendor SDK.
//
// Next: `samples/03-agents` puts `Microsoft.Agents.AI` on top of this exact
// `IChatClient` - an agent is this object plus instructions, a name, memory and
// a session.
