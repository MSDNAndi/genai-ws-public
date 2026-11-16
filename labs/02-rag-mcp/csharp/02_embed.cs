#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 2 · step 2 — embed: chunk -> vector -> store.
//
// An embedding (text as a list of numbers) puts similar meanings close together, so "search" becomes "find the
// nearest vectors". We embed every chunk with the /embeddings endpoint (same OpenAI client as Lab 1) and save chunks +
// vectors in build/index.json — the simplest possible vector store (a searchable file of vectors).
// Notice: we batch 32 chunks per request, and normalise each vector once so search is a plain dot product.
// Input: build/chunks.jsonl from the Python step 1, or the prebuilt copy in data/prebuilt/ (same format).
// Optional: EMBED_BASE_URL / EMBED_API_KEY / GENAI_EMBED_MODEL embed locally (e.g. Ollama bge-m3) while chatting in the cloud.
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Diagnostics;
using System.Text.Json.Nodes;
using OpenAI;
using OpenAI.Embeddings;

// --- settings: find labs/ and load labs/.env (your key, endpoint and model names) -----------------------------------
var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))    // walk up to the labs/ root
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
// labs/.env, or one .env at the repo root: load every .env from labs/ upward - NoClobber, so the nearest wins
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));   // labs/.env; real environment variables win
static string Env(string name, string? fallback = null) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
    ? value : fallback ?? throw new InvalidOperationException($"{name} is not set - copy labs/.env.example to labs/.env");

// EMBED_* only if you embed somewhere else; otherwise the normal GENAI_* settings
string key = Env("EMBED_API_KEY", Env("GENAI_API_KEY")), embedModel = Env("GENAI_EMBED_MODEL");
var clientOptions = new OpenAIClientOptions { Endpoint = new Uri(Env("EMBED_BASE_URL", Env("GENAI_BASE_URL"))) };
if ((Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key")
    clientOptions.AddPolicy(new HeaderPolicy("api-key", key), PipelinePosition.PerCall);   // Azure-style "api-key" header
EmbeddingClient client = new OpenAIClient(new ApiKeyCredential(key), clientOptions).GetEmbeddingClient(embedModel);

// --- input: your chunks from step 1, or the prebuilt copy ------------------------------------------------------------
string build = Path.Combine(labs, "02-rag-mcp", "build");
string source = File.Exists(Path.Combine(build, "chunks.jsonl")) ? Path.Combine(build, "chunks.jsonl")
    : Path.Combine(labs, "02-rag-mcp", "data", "prebuilt", "chunks.jsonl");
// one chunk per line: {"id", "doc", "chunk", "text"} — kept as JSON objects, so every field lands in the index unchanged
List<JsonObject> chunks = [.. File.ReadLines(source).Where(line => line.Trim() != "").Select(line => JsonNode.Parse(line)!.AsObject())];

// --- embed: text in, one vector per text out -------------------------------------------------------------------------
var clock = Stopwatch.StartNew();
var vectors = new List<float[]>();
foreach (JsonObject[] batch in chunks.Chunk(32))       // batch: one request per 32 chunks
{
    OpenAIEmbeddingCollection result = await client.GenerateEmbeddingsAsync(batch.Select(c => (string)c["text"]!));
    vectors.AddRange(result.Select(e => e.ToFloats().ToArray()));   // same order as the input
}

// --- store: chunks + vectors + the model name (queries must use the SAME model) --------------------------------------
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
