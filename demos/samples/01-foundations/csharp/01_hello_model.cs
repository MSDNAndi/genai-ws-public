#:project ../../../shared/csharp/GenAIClass/GenAIClass.csproj

// %% [markdown]
// # 01 - Hello, model
//
// The smallest useful call there is: a list of messages in, one message out.
// Everything later in this workshop is this call with more structure around it.
//
// Run it (no .csproj needed - .NET 10 file-based apps):
//
// ```bash
// dotnet run 01_hello_model.cs                    # uses GENAI_PROFILE from .env
// dotnet run 01_hello_model.cs -- --profile ollama
// ```

// %%
using GenAIClass;
using OpenAI.Chat;

var profile = Providers.GetProfile(args: args);
ChatClient chat = Providers.CreateClient(profile).GetChatClient(profile.Model);
Console.WriteLine(profile);

// %% [markdown]
// ## The call
//
// The message list is the whole conversation - the model is stateless, so *you*
// own the history. System = standing instructions, User = this turn,
// Assistant = what the model said last time.

// %%
ChatCompletion completion = await chat.CompleteChatAsync(
[
    new SystemChatMessage("You are a concise assistant. Answer in one sentence."),
    new UserChatMessage("Why is the sky blue?"),
]);

Console.WriteLine(completion.Content[0].Text);

// %% [markdown]
// ## What else came back
//
// Tokens are the unit you pay in, and `FinishReason` tells you *why* the model
// stopped - `Stop` means it was done, `Length` means you cut it off.

// %%
Console.WriteLine($"finish_reason : {completion.FinishReason}");
Console.WriteLine($"model         : {completion.Model}");
Console.WriteLine($"tokens        : {completion.Usage.InputTokenCount} in + " +
                  $"{completion.Usage.OutputTokenCount} out = {completion.Usage.TotalTokenCount}");

// %% [markdown]
// ## Streaming
//
// Same request, streaming call: you get deltas instead of one blob. Nothing
// about the model changes - this is purely how the HTTP response is framed.

// %%
await foreach (StreamingChatCompletionUpdate update in
    chat.CompleteChatStreamingAsync([new UserChatMessage("Name three blue things. One line.")]))
{
    foreach (ChatMessageContentPart part in update.ContentUpdate)
        Console.Write(part.Text);
}
Console.WriteLine();
