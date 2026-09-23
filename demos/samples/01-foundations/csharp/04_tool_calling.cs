#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:property PublishAot=false

// %% [markdown]
// # 04 - The tool-calling loop (C#)
//
// The exact same loop as the Python twin, with C# types. Every agent framework
// you will meet today - Microsoft.Agents.AI, LangGraph, the OpenAI and Claude
// Agent SDKs - is this loop with better ergonomics around it.
//
// The model never runs anything. It emits *a request to run something*, you run
// it, you hand the result back, and it continues.
//
// ```bash
// dotnet run 04_tool_calling.cs -- --profile mock
// ```

// %%
using System.Net.Http.Json;
using System.Text.Json;
using GenAIClass;
using OpenAI.Chat;

var profile = Providers.GetProfile(args: args);
ChatClient chat = Providers.CreateClient(profile).GetChatClient(profile.Model);
Console.WriteLine(profile);

// %% [markdown]
// ## 1. The functions - ordinary C#, no AI involved
//
// `GetRoute` calls openrouteservice.org when OPENROUTESERVICE_API_KEY is set and
// otherwise returns a plausible stub, so the loop is demonstrable offline.

// %%
string? orsKey = Environment.GetEnvironmentVariable("OPENROUTESERVICE_API_KEY");
using var http = new HttpClient();

async Task<object> GetRouteAsync(string origin, string destination)
{
    if (string.IsNullOrWhiteSpace(orsKey))
        return new { origin, destination, distance_km = 42.0, duration_min = 35.0,
                     source = "stub (no ORS key set)" };

    async Task<double[]> GeocodeAsync(string place)
    {
        var url = $"https://api.openrouteservice.org/geocode/search?api_key={orsKey}" +
                  $"&text={Uri.EscapeDataString(place)}&size=1";
        using var doc = JsonDocument.Parse(await http.GetStringAsync(url));
        var coordinates = doc.RootElement.GetProperty("features")[0]
            .GetProperty("geometry").GetProperty("coordinates");
        return [coordinates[0].GetDouble(), coordinates[1].GetDouble()];
    }

    var body = new { coordinates = new[] { await GeocodeAsync(origin), await GeocodeAsync(destination) } };
    using var request = new HttpRequestMessage(HttpMethod.Post,
        "https://api.openrouteservice.org/v2/directions/driving-car")
    {
        Content = JsonContent.Create(body),
    };
    request.Headers.Add("Authorization", orsKey);
    var response = await http.SendAsync(request);
    response.EnsureSuccessStatusCode();

    using var result = JsonDocument.Parse(await response.Content.ReadAsStringAsync());
    var summary = result.RootElement.GetProperty("routes")[0].GetProperty("summary");
    return new
    {
        origin,
        destination,
        distance_km = Math.Round(summary.GetProperty("distance").GetDouble() / 1000, 1),
        duration_min = Math.Round(summary.GetProperty("duration").GetDouble() / 60),
        source = "openrouteservice.org",
    };
}

// Deliberately fake - it is here to prove the model picks between tools.
object GetCurrentWeather(string location) =>
    new { location, temperature_c = 18, conditions = "light rain" };

// %% [markdown]
// ## 2. The descriptions - this is the prompt engineering that matters
//
// The model sees nothing but these names, descriptions and schemas. A vague
// description is a bug: it is how the model decides *whether* to call you and
// *what* to put in the arguments.

// %%
ChatTool routeTool = ChatTool.CreateFunctionTool(
    functionName: "get_route",
    functionDescription: "Driving distance and duration between two places. " +
                         "Use for any question about how far or how long a drive is.",
    functionParameters: BinaryData.FromString("""
    {
      "type": "object",
      "properties": {
        "origin":      { "type": "string", "description": "Start, e.g. Bellevue, WA" },
        "destination": { "type": "string", "description": "End, e.g. Redmond, WA" }
      },
      "required": ["origin", "destination"],
      "additionalProperties": false
    }
    """));

ChatTool weatherTool = ChatTool.CreateFunctionTool(
    functionName: "get_current_weather",
    functionDescription: "Current weather conditions for one place.",
    functionParameters: BinaryData.FromString("""
    {
      "type": "object",
      "properties": { "location": { "type": "string" } },
      "required": ["location"],
      "additionalProperties": false
    }
    """));

var options = new ChatCompletionOptions { Tools = { routeTool, weatherTool } };

// %% [markdown]
// ## 3. The loop
//
// 1. send the conversation plus the tool catalogue
// 2. if `FinishReason == ToolCalls`, run every requested call
// 3. append the assistant turn **and** one `ToolChatMessage` per call - the ids
//    must match, or the next request is rejected
// 4. go back to 1; stop when the model answers in prose
//
// `maxTurns` is not optional politeness. Without it, a confused model and a
// failing tool will bill you in a tight loop.

// %%
async Task<string> RunConversationAsync(string question, int maxTurns = 6)
{
    List<ChatMessage> messages =
    [
        new SystemChatMessage("You are a travel assistant. Use the tools; never guess numbers."),
        new UserChatMessage(question),
    ];

    for (var turn = 1; turn <= maxTurns; turn++)
    {
        ChatCompletion completion = await chat.CompleteChatAsync(messages, options);
        messages.Add(new AssistantChatMessage(completion));

        if (completion.FinishReason != ChatFinishReason.ToolCalls)
        {
            Console.WriteLine($"  turn {turn}: answered");
            return completion.Content.Count > 0 ? completion.Content[0].Text : "";
        }

        foreach (ChatToolCall call in completion.ToolCalls)
        {
            using var arguments = JsonDocument.Parse(call.FunctionArguments);
            string Arg(string name) => arguments.RootElement.TryGetProperty(name, out var v)
                ? v.GetString() ?? "" : "";

            Console.WriteLine($"  turn {turn}: model wants {call.FunctionName}({call.FunctionArguments})");

            object result;
            try
            {
                result = call.FunctionName switch
                {
                    "get_route" => await GetRouteAsync(Arg("origin"), Arg("destination")),
                    "get_current_weather" => GetCurrentWeather(Arg("location")),
                    _ => new { error = $"unknown tool {call.FunctionName}" },
                };
            }
            catch (Exception error) // hand failures back as data, never crash the loop
            {
                result = new { error = $"{error.GetType().Name}: {error.Message}" };
            }

            messages.Add(new ToolChatMessage(call.Id, JsonSerializer.Serialize(result)));
        }
    }

    return "(gave up - hit maxTurns)";
}

Console.WriteLine(await RunConversationAsync(
    "How far is it from Bellevue, WA to Redmond, WA, and what is the weather there?"));

// %% [markdown]
// ## What you just built
//
// * **Parallel tool calls** - `ToolCalls` is a list; good models ask for route
//   and weather in one turn. Handle all of them before replying.
// * **Errors are data.** Returning an error object lets the model apologise or
//   retry; throwing kills the run.
// * **The catalogue is context.** Every tool costs tokens on every single turn.
// * **Nothing here is provider-specific.** Swap `--profile` and the same loop
//   runs against a local model.
//
// Sample `05_extensions_ai.cs` shows the same thing again through
// `Microsoft.Extensions.AI`, where the plumbing above collapses into
// `AIFunctionFactory.Create(GetRoute)` plus a middleware that runs the loop for
// you. Write it by hand once, then never again.
