#:package ModelContextProtocol.Core@2.2.0
#:property PublishAot=false
// Lab 2 · step 5 — talk to your MCP server from code (this is what every MCP host does under the hood).
using System.Diagnostics;
using System.Text.Encodings.Web;
using System.Text.Json;
using ModelContextProtocol.Client;
using ModelContextProtocol.Protocol;

var here = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
string server = Path.Combine(here, "04_mcp_server.cs");

// Gotcha: stdout of the server IS the protocol channel, and `dotnet run` may print build output there.
// So: build the server first (quietly), then start it with --no-build.
using (var build = Process.Start(new ProcessStartInfo("dotnet", ["build", server]) { RedirectStandardOutput = true })!)
{
    string buildLog = await build.StandardOutput.ReadToEndAsync();
    await build.WaitForExitAsync();
    if (build.ExitCode != 0) throw new InvalidOperationException($"dotnet build {server} failed:\n{buildLog}");
}

// The C# SDK passes your environment on to the server (InheritEnvironmentVariables = true); Python's SDK does not.
// Our server also finds labs/.env on its own. The server's log lines (stderr) are shown with a prefix.
await using McpClient session = await McpClient.CreateAsync(new StdioClientTransport(new StdioClientTransportOptions
{
    Name = "kestrel-docs",
    Command = "dotnet",
    Arguments = ["run", "--file", server, "--no-build"],
    StandardErrorLines = line => Console.Error.WriteLine($"  [server] {line}"),
    ShutdownTimeout = TimeSpan.FromSeconds(1),   // SDK 2.2 waits this long for the server to quit on its own, then stops it
}));

IList<McpClientTool> tools = await session.ListToolsAsync();
Console.WriteLine("tools: [" + string.Join(", ", tools.Select(t => $"('{t.Name}', '{t.Description.Split('.')[0]}')")) + "]");

CallToolResult result = await session.CallToolAsync("search_docs", new Dictionary<string, object?> { ["query"] = "night flight altitude limit", ["k"] = 2 });
var readable = new JsonSerializerOptions { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };   // print ' instead of \u0027
foreach (TextContentBlock block in result.Content.OfType<TextContentBlock>())
{
    if (result.IsError == true) throw new InvalidOperationException($"search_docs failed: {block.Text}");
    foreach (JsonElement hit in JsonDocument.Parse(block.Text).RootElement.EnumerateArray())   // our tool returns a JSON list
        Console.WriteLine($"hit: {Cut(JsonSerializer.Serialize(hit, readable), 220)}");
}

ReadResourceResult doc = await session.ReadResourceAsync("kestrel://docs/kestrel_customer_service_policy");
Console.WriteLine($"resource: {Cut(doc.Contents.OfType<TextResourceContents>().First().Text, 120).Replace("\n", " ")} ...");

IList<McpClientPrompt> prompts = await session.ListPromptsAsync();
Console.WriteLine($"prompts: [{string.Join(", ", prompts.Select(p => $"'{p.Name}'"))}]");

static string Cut(string text, int max) => text.Length <= max ? text : text[..max];
