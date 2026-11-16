#:package ModelContextProtocol@2.2.0
#:package Microsoft.Extensions.Hosting@10.0.12
#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// STARTER - complete the TODO block(s). The finished version is in solution/04_mcp_server.cs
// Lab 2 · step 4 — an MCP server is just functions with descriptions.
//
// MCP (Model Context Protocol = plug-in standard for AI tools) lets any host — Claude Code, GitHub Copilot, LM Studio,
// MCP Inspector, the agents in Lab 3 — use our search. We publish three things:
//   tool     search_docs  (a function the model may call; its [Description] is what the model reads)
//   resource kestrel://docs/<name>  (read-only data, here: a whole document)
//   prompt   cite_answer  (a reusable prompt template)
// Notice: never Console.WriteLine() here — with stdio (talking over stdin/stdout) stdout IS the protocol. Log to stderr.
// How hosts start it:  dotnet build 04_mcp_server.cs   (once, and after every change), then
//                      dotnet run --file /full/path/04_mcp_server.cs --no-build
// A plain `dotnet run` may print build output on stdout and break the protocol (05_mcp_client.cs does it right).
using System.ClientModel;
using System.ClientModel.Primitives;
using System.ComponentModel;
using System.Text.Json.Nodes;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using ModelContextProtocol.Server;
using OpenAI;
using OpenAI.Embeddings;

// --- settings: labs/.env is found from THIS file's folder — MCP hosts start us from anywhere. Real env vars win. -----
var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))    // walk up to the labs/ root
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
// labs/.env, or one .env at the repo root: load every .env from labs/ upward - NoClobber, so the nearest wins
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));
static string Env(string name, string? fallback = null) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
    ? value : fallback ?? throw new InvalidOperationException($"{name} is not set - copy labs/.env.example to labs/.env");

// --- the same search as step 3 (only embeddings needed: the HOST's model writes the answer) -------------------------
string key = Env("EMBED_API_KEY", Env("GENAI_API_KEY"));
var clientOptions = new OpenAIClientOptions { Endpoint = new Uri(Env("EMBED_BASE_URL", Env("GENAI_BASE_URL"))) };
if ((Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key")
    clientOptions.AddPolicy(new HeaderPolicy("api-key", key), PipelinePosition.PerCall);   // Azure-style "api-key" header
string lab2 = Path.Combine(labs, "02-rag-mcp"), build = Path.Combine(lab2, "build");
var index = new KestrelIndex(Path.Combine(build, "index.json"), new OpenAIClient(new ApiKeyCredential(key), clientOptions));

// --- tool: the model decides when to call it, based on the name + description + typed arguments --------------------
McpServerTool searchDocs;
// TODO 3: register a tool `search_docs(query, k = 4)` that returns the top-k chunks (id, doc, score, text) - its [Description] becomes the tool description the model sees
throw new NotImplementedException("TODO 3: register a tool `search_docs(query, k = 4)` that returns the top-k chunks (id, doc, score, text) - its [Description] becomes the tool description the model sees");

// --- resource: data the host can read by URI; {name} in the URI becomes the function argument ----------------------
[Description("The full extracted text of one document, e.g. kestrel://docs/kestrel_operations_handbook")]
string GetDocument(string name)
{
    string path = Path.Combine(build, Path.GetFileNameWithoutExtension(name) + ".md");   // keep only the stem: "../x.pdf" -> "x.md"
    return File.ReadAllText(File.Exists(path) ? path : Path.Combine(lab2, "data", "prebuilt", Path.GetFileName(path)));
}

// --- prompt: a ready-made instruction a user can pick in the host ---------------------------------------------------
[Description("A reusable prompt: answer a question with citations from search_docs.")]
string CiteAnswer(string question) => $"Use the search_docs tool, then answer with [doc#chunk] citations. Question: {question}";

// --- wire it up: a generic .NET host + the MCP server over stdio ----------------------------------------------------
var builder = Host.CreateApplicationBuilder(args);
builder.Logging.AddConsole(o => o.LogToStandardErrorThreshold = LogLevel.Trace);   // ALL log output -> stderr
builder.Logging.SetMinimumLevel(LogLevel.Warning);
builder.Services
    .AddMcpServer(o => o.ServerInfo = new() { Name = "kestrel-docs", Version = "1.0.0" })   // the name hosts show
    .WithStdioServerTransport()                                                             // talk over stdin/stdout
    .WithTools([searchDocs])
    .WithResources([McpServerResource.Create(GetDocument, new() { UriTemplate = "kestrel://docs/{name}", Name = "get_document", MimeType = "text/markdown" })])
    .WithPrompts([McpServerPrompt.Create(CiteAnswer, new() { Name = "cite_answer" })]);
await builder.Build().RunAsync();                                                           // wait for requests until stdin closes

// build/index.json (written by 02_embed) -> cosine top-k. The C# twin of kestrel_search.py.
sealed class KestrelIndex
{
    readonly List<(Hit Chunk, float[] Vector)> items = [];
    readonly EmbeddingClient embedder;

    public KestrelIndex(string path, OpenAIClient openai)
    {
        if (!File.Exists(path)) throw new FileNotFoundException($"{path} not found - run 01_ingest.py and 02_embed.cs first");
        JsonNode data = JsonNode.Parse(File.ReadAllText(path))!;
        foreach (JsonNode? item in data["items"]!.AsArray())   // keep each chunk next to its (unit-length) vector
            items.Add((new Hit((string)item!["id"]!, (string)item["doc"]!, 0, (string)item["text"]!),
                       [.. item["vector"]!.AsArray().Select(x => (float)x!)]));
        embedder = openai.GetEmbeddingClient((string)data["embed_model"]!);   // queries need the model the index was built with
    }

    // embed the query, score every chunk by cosine similarity (1 = same meaning), return the k best
    public async Task<List<Hit>> SearchAsync(string query, int k = 4)
    {
        float[] q = (await embedder.GenerateEmbeddingAsync(query)).Value.ToFloats().ToArray();
        if (q.Length != items[0].Vector.Length)          // e.g. the index was built on another endpoint (or the mock)
            throw new InvalidOperationException($"index vectors have {items[0].Vector.Length} dims, this endpoint returns {q.Length} - re-run 02_embed.cs");
        double norm = Math.Sqrt(q.Sum(x => (double)x * x));   // chunk vectors are unit length; divide by the query's length
        return [.. items.Select(item => item.Chunk with { Score = Math.Round(Dot(item.Vector, q) / norm, 3) })
                        .OrderByDescending(hit => hit.Score).Take(k)];
    }

    static double Dot(float[] a, float[] b) { double sum = 0; for (int i = 0; i < a.Length; i++) sum += a[i] * b[i]; return sum; }
}

record Hit(string Id, string Doc, double Score, string Text);   // serialized as {"id", "doc", "score", "text"}

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
