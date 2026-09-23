#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 2 · step 2 — embed every chunk and keep the vectors in one plain JSON file (the simplest "vector store").
//
// Same OpenAI-compatible client as Lab 1, different endpoint: /embeddings. Works with Foundry (text-embedding-3-*)
// and with Ollama (bge-m3, nomic-embed-text ...) — just change GENAI_EMBED_MODEL, or set EMBED_BASE_URL/EMBED_API_KEY
// to embed locally while chatting in the cloud. build/index.json has the same format in every language of the labs.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Diagnostics;
using System.Text.Json.Nodes;
using OpenAI;
using OpenAI.Embeddings;

var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))    // walk up to the labs/ root
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
// labs/.env, or one .env at the repo root: load every .env from labs/ upward - NoClobber, so the nearest wins
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));   // labs/.env; real environment variables win
static string Env(string name, string? fallback = null) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
    ? value : fallback ?? throw new InvalidOperationException($"{name} is not set - copy labs/.env.example to labs/.env");

string key = Env("EMBED_API_KEY", Env("GENAI_API_KEY")), embedModel = Env("GENAI_EMBED_MODEL");
var clientOptions = new OpenAIClientOptions { Endpoint = new Uri(Env("EMBED_BASE_URL", Env("GENAI_BASE_URL"))) };
if ((Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key")
    clientOptions.AddPolicy(new HeaderPolicy("api-key", key), PipelinePosition.PerCall);
EmbeddingClient client = new OpenAIClient(new ApiKeyCredential(key), clientOptions).GetEmbeddingClient(embedModel);

string build = Path.Combine(labs, "02-rag-mcp", "build");
string source = File.Exists(Path.Combine(build, "chunks.jsonl")) ? Path.Combine(build, "chunks.jsonl")
    : Path.Combine(labs, "02-rag-mcp", "data", "prebuilt", "chunks.jsonl");
// one chunk per line: {"id", "doc", "chunk", "text"} — kept as JSON objects, so every field lands in the index unchanged
List<JsonObject> chunks = [.. File.ReadLines(source).Where(line => line.Trim() != "").Select(line => JsonNode.Parse(line)!.AsObject())];

var clock = Stopwatch.StartNew();
var vectors = new List<float[]>();
foreach (JsonObject[] batch in chunks.Chunk(32))       // batch: one request per 32 chunks
{
    OpenAIEmbeddingCollection result = await client.GenerateEmbeddingsAsync(batch.Select(c => (string)c["text"]!));
    vectors.AddRange(result.Select(e => e.ToFloats().ToArray()));
}

var items = new JsonArray();
foreach (var (chunk, vector) in chunks.Zip(vectors))
{
    double norm = Math.Sqrt(vector.Sum(x => (double)x * x));   // normalise once -> cosine similarity = dot product
    chunk["vector"] = new JsonArray([.. vector.Select(x => (JsonNode)Math.Round(x / norm, 6))]);
    items.Add(chunk);
}
var index = new JsonObject { ["embed_model"] = embedModel, ["dims"] = vectors[0].Length, ["items"] = items };
Directory.CreateDirectory(build);
File.WriteAllText(Path.Combine(build, "index.json"), index.ToJsonString());   // one plain file = our "vector store"
Console.WriteLine($"{chunks.Count} chunks x {vectors[0].Length} dims with '{embedModel}' in {clock.Elapsed.TotalSeconds:F1}s " +
                  "-> build/index.json");

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
