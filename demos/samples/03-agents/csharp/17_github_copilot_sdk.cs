#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj
#:package GitHub.Copilot.SDK@1.0.14
#:property PublishAot=false

// %% [markdown]
// # 17 - GitHub Copilot SDK (C#)
//
// | | |
// |---|---|
// | **Pattern** | **harness as a library**: the Copilot CLI's planner, tool loop and built-in tools, embedded in your app |
// | **Communication** | a session with an **event stream**; your tools and hooks are called back over the SDK's RPC channel |
// | **Use when** | you want Copilot's agent (and its GitHub integration) inside your own tool, CI job or service |
// | **Watch out** | it arrives with file/shell/GitHub tools switched on - restrict `AvailableTools` explicitly |
//
// Twin of `python/17_github_copilot_sdk.py`. The one .NET-specific detail worth
// pointing at: `SessionConfig.Tools` takes `Microsoft.Extensions.AI` functions,
// so a Copilot tool is the same `AIFunctionFactory.Create(...)` as in samples
// 01 and 05. Bring-your-own-model via `Provider` means no GitHub sign-in.
//
// ```bash
// dotnet run 17_github_copilot_sdk.cs -- --profile mock
// ```

// %%
using System.ComponentModel;
using GenAIClass;
using GitHub.Copilot;
using Microsoft.Extensions.AI;
using Rpc = GitHub.Copilot.Rpc;   // Rpc also has a ProviderConfig - keep it qualified

var profile = Providers.GetProfile(args: args);
Console.WriteLine(profile);

[Description("Current weather conditions for one place.")]
static string GetCurrentWeather([Description("City and region")] string location)
    => $"18C and light rain in {location}";

// %% [markdown]
// ## Hooks and permissions
//
// Same trap as the Python twin (verified on 1.0.14): a pre-tool hook that
// answers "allow" pre-approves the call and the permission handler is never
// asked. The audit hook below therefore returns *no* decision.
//
// Note: in the GA .NET SDK the permission-decision types are still marked
// experimental (GHCP001, "subject to change or removal"). Using them needs the
// pragma below - treat that API as unstable when you build on it.

// %%
Task<PreToolUseHookOutput> Audit(PreToolUseHookInput input, HookInvocation _)
{
    Console.WriteLine($"  [hook] {input.ToolName} {input.ToolArgs}");
    return Task.FromResult(new PreToolUseHookOutput());   // observe only
}

#pragma warning disable GHCP001
// Policy: our own tools yes ("custom-tool"), everything built in no.
Task<Rpc.PermissionDecision> OwnToolsOnly(PermissionRequest request, PermissionInvocation _)
{
    if (request.Kind == "custom-tool")
    {
        Console.WriteLine($"  [permission] approved: {request.Kind}");
        return Task.FromResult<Rpc.PermissionDecision>(new Rpc.PermissionDecisionApproveOnce());
    }
    Console.WriteLine($"  [permission] refused: {request.Kind}");
    return Task.FromResult<Rpc.PermissionDecision>(
        new Rpc.PermissionDecisionReject { Feedback = "Unattended run: only our own tools are allowed." });
}
#pragma warning restore GHCP001

// %% [markdown]
// ## One session on the workshop's model

// %%
await using var client = new CopilotClient(new CopilotClientOptions { WorkingDirectory = Environment.CurrentDirectory });
await client.StartAsync();
Console.WriteLine($"Copilot runtime {(await client.GetStatusAsync()).Version}");

var headers = profile.KeyHeader == "api-key"
    ? new Dictionary<string, string> { ["api-key"] = profile.ApiKey }
    : new Dictionary<string, string>();

await using var session = await client.CreateSessionAsync(new SessionConfig
{
    Model = profile.Model,
    Provider = new ProviderConfig
    {
        Type = "openai",
        WireApi = "completions",
        BaseUrl = profile.BaseUrl,
        ApiKey = profile.ApiKey,
        Headers = headers,
    },
    // Explicit name: a local function's own name is compiler-mangled ("_Main_g_...").
    Tools = [AIFunctionFactory.Create(GetCurrentWeather, name: "get_current_weather")],
    AvailableTools = ["get_current_weather"],
    Hooks = new SessionHooks { OnPreToolUse = Audit },
    OnPermissionRequest = OwnToolsOnly,
});

var reply = await session.SendAndWaitAsync("What is the weather in Lisbon?", TimeSpan.FromSeconds(120));
Console.WriteLine($"\nanswer: {reply?.Data.Content ?? "(no reply)"}");

var events = await session.GetEventsAsync();
Console.WriteLine($"\n{events.Count} session events, e.g.: " +
                  string.Join(", ", events.Select(e => e.GetType().Name).Distinct().Take(6)));
