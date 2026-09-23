#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 1 · step 1 — your first call.                                     Run: dotnet run --file 01_hello.cs
//
// The same few lines talk to Azure AI Foundry, the workshop gateway, OpenAI, Ollama, LM Studio, Foundry Local, vLLM ...
// Only three things change between them: the endpoint, the key, and the model name.
using System.ClientModel;
using System.ClientModel.Primitives;
using OpenAI;
using OpenAI.Chat;
#pragma warning disable OPENAI001 // ReasoningEffortLevel is still marked "experimental" in the OpenAI .NET SDK 2.13

// Settings come from labs/.env (found by walking up from this file); real environment variables win over the file.
var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))    // walk up to the labs/ root
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
// labs/.env, or one .env at the repo root: load every .env from labs/ upward - NoClobber, so the nearest wins
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));
static string Env(string name, string? fallback = null) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
    ? value : fallback ?? throw new InvalidOperationException($"{name} is not set - copy labs/.env.example to labs/.env");

string key = Env("GENAI_API_KEY"), model = Env("GENAI_MODEL");
var clientOptions = new OpenAIClientOptions { Endpoint = new Uri(Env("GENAI_BASE_URL")) };
// The workshop gateway (and Foundry keys) expect the key in an "api-key" header, not only as a Bearer token.
if ((Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key")
    clientOptions.AddPolicy(new HeaderPolicy("api-key", key), PipelinePosition.PerCall);
ChatClient client = new OpenAIClient(new ApiKeyCredential(key), clientOptions).GetChatClient(model);
// Optional: GENAI_REASONING_EFFORT=low (gpt-5 family) or none (local "thinking" models) keeps answers fast and cheap
var options = new ChatCompletionOptions();
if (Env("GENAI_REASONING_EFFORT", "") is { Length: > 0 } effort) options.ReasoningEffortLevel = new ChatReasoningEffortLevel(effort);

ChatCompletion response = await client.CompleteChatAsync(
[
    new SystemChatMessage("You are a concise assistant for a developer workshop."),
    new UserChatMessage("In two sentences: what is a token, and why should a developer care?"),
], options);

Console.WriteLine(response.Content[0].Text);
ChatTokenUsage usage = response.Usage;
Console.WriteLine($"\n[{response.Model}] prompt={usage.InputTokenCount} completion={usage.OutputTokenCount} " +
                  $"total={usage.TotalTokenCount} tokens · finish_reason={response.FinishReason}");

// Try this:
//  1. Change the system prompt ("answer like a pirate", "answer in German") and run again.
//  2. Keep the ClientResult (var result = await client.CompleteChatAsync(...)) and print result.GetRawResponse().Content
//     — everything that came back (ids, usage, content filters ...).
//  3. Set GENAI_MODEL=<another deployment> in labs/.env and compare.

// Puts the key into an extra request header (a System.ClientModel pipeline policy runs on every request).
sealed class HeaderPolicy(string name, string value) : PipelinePolicy
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
