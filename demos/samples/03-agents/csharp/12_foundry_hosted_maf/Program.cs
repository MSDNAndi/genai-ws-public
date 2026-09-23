// # 12 - A Foundry hosted agent (Microsoft Agent Framework, C#)
//
// | | |
// |---|---|
// | **Pattern** | the same agent as sample 01, **deployed**: Foundry runs your container per session |
// | **Communication** | the **Responses protocol over HTTP** - any OpenAI SDK is a client |
// | **Use when** | the agent must be a service: identity, scaling, sessions, telemetry, versioning |
// | **Watch out** | never bake keys into the image - the platform gives the agent its own Entra identity |
//
// Twin of `python/12_foundry_hosted_maf/main.py`.
//
// Why a .csproj here (the only one in the samples): a container build only sees
// this folder, so it cannot reach `shared/csharp`. Local mode therefore reads the
// GENAI_* variables directly and defaults to the offline mock server. It speaks
// `Authorization: Bearer`, i.e. the mock, Ollama or OpenAI - use the Python twin
// against the APIM course gateway, which wants an `api-key` header.
//
//   dotnet run                           # serves http://localhost:8088/responses
//   uv run ../../python/14_call_hosted_agent.py
//   azd ai agent init -m azure.yaml && azd up

using System.ClientModel;
using System.ComponentModel;
using Azure.AI.AgentServer.Core;
using Azure.AI.Projects;
using Azure.Identity;
using Microsoft.Agents.AI;
using Microsoft.Agents.AI.Foundry.Hosting;
using Microsoft.Extensions.AI;
using OpenAI;
using OpenAI.Chat; // ChatClient.AsAIAgent lives here

const string Instructions = "You are a travel assistant. Use the tools; never guess numbers. Be brief.";

[Description("Current weather conditions for one place.")]
static object GetCurrentWeather([Description("City and region")] string location)
    => new { location, temperature_c = 18, conditions = "light rain" };

// One agent, two runtimes. Hosted: the platform injects FOUNDRY_PROJECT_ENDPOINT
// and DefaultAzureCredential resolves to the agent's own Entra identity - no key
// exists anywhere. Local: any OpenAI-compatible endpoint.
static AIAgent BuildAgent()
{
    // Explicit name: a local function's own name is compiler-mangled ("_Main_g_...").
    AITool[] tools = [AIFunctionFactory.Create(GetCurrentWeather, name: "get_current_weather")];

    if (Environment.GetEnvironmentVariable("FOUNDRY_PROJECT_ENDPOINT") is { Length: > 0 } project)
    {
        return new AIProjectClient(new Uri(project), new DefaultAzureCredential()).AsAIAgent(
            model: Environment.GetEnvironmentVariable("AZURE_AI_MODEL_DEPLOYMENT_NAME")
                   ?? throw new InvalidOperationException("AZURE_AI_MODEL_DEPLOYMENT_NAME is not set."),
            instructions: Instructions,
            name: "travel-agent",
            tools: tools);
    }

    var baseUrl = Environment.GetEnvironmentVariable("GENAI_BASE_URL") ?? "http://localhost:8080/v1";
    var apiKey = Environment.GetEnvironmentVariable("GENAI_API_KEY") ?? "mock";
    var model = Environment.GetEnvironmentVariable("GENAI_MODEL") ?? "mock-model-1";
    Console.WriteLine($"local mode: {model} @ {baseUrl}");

    return new OpenAIClient(new ApiKeyCredential(apiKey), new OpenAIClientOptions { Endpoint = new Uri(baseUrl) })
        .GetChatClient(model)
        .AsAIAgent(instructions: Instructions, name: "travel-agent", tools: tools);
}

// AgentHost wires up Kestrel on port 8088 (or PORT), GET /readiness for the
// platform's health probe, OpenTelemetry, and the Responses protocol endpoint.
var builder = AgentHost.CreateBuilder(args);
builder.Services.AddFoundryResponses(BuildAgent());
builder.RegisterProtocol("responses", endpoints => endpoints.MapFoundryResponses());
builder.Build().Run();
