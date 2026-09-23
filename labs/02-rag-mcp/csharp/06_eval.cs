#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 2 · stretch — measure before you tune: a tiny golden set checks retrieval (is the right document in the top k?)
// and answers (does the answer contain the expected fact?). Re-run it after every change to chunking, model or prompt.
// (promptfoo, Microsoft.Extensions.AI.Evaluation and the Azure AI Evaluation SDK do the same at scale.)
using System.ClientModel;
using System.ClientModel.Primitives;
using System.Text.Json.Nodes;
using OpenAI;
using OpenAI.Chat;
using OpenAI.Embeddings;
#pragma warning disable OPENAI001 // ReasoningEffortLevel is still marked "experimental" in the OpenAI .NET SDK 2.13

var labs = AppContext.GetData("EntryPointFileDirectoryPath") as string ?? Directory.GetCurrentDirectory();
while (!File.Exists(Path.Combine(labs, "_tools", "make_starters.py")))    // walk up to the labs/ root
    labs = Path.GetDirectoryName(labs) ?? throw new DirectoryNotFoundException("labs/_tools not found above this file");
// labs/.env, or one .env at the repo root: load every .env from labs/ upward - NoClobber, so the nearest wins
for (var envDir = new DirectoryInfo(labs); envDir is not null; envDir = envDir.Parent)
    if (File.Exists(Path.Combine(envDir.FullName, ".env"))) DotNetEnv.Env.NoClobber().Load(Path.Combine(envDir.FullName, ".env"));   // labs/.env; real environment variables win
static string Env(string name, string? fallback = null) => Environment.GetEnvironmentVariable(name) is { Length: > 0 } value
    ? value : fallback ?? throw new InvalidOperationException($"{name} is not set - copy labs/.env.example to labs/.env");

// Two endpoints: chat, and the embeddings the index was built with (EMBED_BASE_URL/EMBED_API_KEY, see 02_embed)
OpenAIClient Connect(string baseUrl, string key)
{
    var clientOptions = new OpenAIClientOptions { Endpoint = new Uri(baseUrl) };
    if ((Environment.GetEnvironmentVariable("GENAI_KEY_HEADER") ?? "api-key") == "api-key")
        clientOptions.AddPolicy(new HeaderPolicy("api-key", key), PipelinePosition.PerCall);
    return new OpenAIClient(new ApiKeyCredential(key), clientOptions);
}
ChatClient client = Connect(Env("GENAI_BASE_URL"), Env("GENAI_API_KEY")).GetChatClient(Env("GENAI_MODEL"));
var index = new KestrelIndex(Path.Combine(labs, "02-rag-mcp", "build", "index.json"),
                             Connect(Env("EMBED_BASE_URL", Env("GENAI_BASE_URL")), Env("EMBED_API_KEY", Env("GENAI_API_KEY"))));
var options = new ChatCompletionOptions();
if (Env("GENAI_REASONING_EFFORT", "") is { Length: > 0 } effort) options.ReasoningEffortLevel = new ChatReasoningEffortLevel(effort);
Console.OutputEncoding = System.Text.Encoding.UTF8;   // for ✓ and ✗ on Windows consoles

(string Question, string Doc, string[] Facts)[] golden =   // question, document that must be retrieved, facts the answer must contain
[
    ("What is the maximum payload of a K-4 Kestrel in rain?", "kestrel_operations_handbook", ["1.8"]),
    ("How long must drones stay grounded after a lightning strike nearby?", "kestrel_operations_handbook", ["30 min"]),
    ("Which form is required before night flights?", "kestrel_operations_handbook", ["NW-17"]),
    ("What does a customer get when the payload is lost?", "kestrel_customer_service_policy", ["full refund", "15"]),
    ("Which latch firmware version fixed the early-release bug?", "kestrel_incident_review_q3_2026", ["3.1.6"]),
    ("How long are proof-of-delivery photos kept?", "kestrel_customer_service_policy", ["30 days"]),
];

int retrievalOk = 0, answerOk = 0;
foreach (var (question, doc, facts) in golden)
{
    List<Hit> hits = await index.SearchAsync(question, k: 4);
    bool found = hits.Any(h => h.Doc.StartsWith(doc));
    string sources = string.Join("\n\n", hits.Select((h, n) => $"[{n + 1}] {h.Text}"));
    ChatCompletion r = await client.CompleteChatAsync(
    [
        new SystemChatMessage("Answer in one sentence using only these sources:\n" + sources),
        new UserChatMessage(question),
    ], options);
    string reply = r.Content.FirstOrDefault()?.Text ?? "";
    bool correct = facts.All(f => reply.Contains(f, StringComparison.OrdinalIgnoreCase));
    retrievalOk += found ? 1 : 0;
    answerOk += correct ? 1 : 0;
    Console.WriteLine($"{(found ? "✓" : "✗")} retrieval  {(correct ? "✓" : "✗")} answer  {question}\n      -> {Cut(reply.Trim(), 140)}");
}
Console.WriteLine($"\nretrieval hit@4: {retrievalOk}/{golden.Length}   answers correct: {answerOk}/{golden.Length}");

static string Cut(string text, int max) => text.Length <= max ? text : text[..max];

// build/index.json (written by 02_embed) -> cosine top-k. The C# twin of kestrel_search.py.
sealed class KestrelIndex
{
    readonly List<(Hit Chunk, float[] Vector)> items = [];
    readonly EmbeddingClient embedder;

    public KestrelIndex(string path, OpenAIClient openai)
    {
        if (!File.Exists(path)) throw new FileNotFoundException($"{path} not found - run 01_ingest.py and 02_embed.cs first");
        JsonNode data = JsonNode.Parse(File.ReadAllText(path))!;
        foreach (JsonNode? item in data["items"]!.AsArray())
            items.Add((new Hit((string)item!["id"]!, (string)item["doc"]!, 0, (string)item["text"]!),
                       [.. item["vector"]!.AsArray().Select(x => (float)x!)]));
        embedder = openai.GetEmbeddingClient((string)data["embed_model"]!);   // queries need the model the index was built with
    }

    public async Task<List<Hit>> SearchAsync(string query, int k = 4)
    {
        float[] q = (await embedder.GenerateEmbeddingAsync(query)).Value.ToFloats().ToArray();
        if (q.Length != items[0].Vector.Length)          // e.g. the index was built on another endpoint (or the mock)
            throw new InvalidOperationException($"index vectors have {items[0].Vector.Length} dims, this endpoint returns {q.Length} - re-run 02_embed.cs");
        double norm = Math.Sqrt(q.Sum(x => (double)x * x));
        return [.. items.Select(item => item.Chunk with { Score = Math.Round(Dot(item.Vector, q) / norm, 3) })
                        .OrderByDescending(hit => hit.Score).Take(k)];
    }

    static double Dot(float[] a, float[] b) { double sum = 0; for (int i = 0; i < a.Length; i++) sum += a[i] * b[i]; return sum; }
}

record Hit(string Id, string Doc, double Score, string Text);

sealed class HeaderPolicy(string name, string value) : PipelinePolicy   // adds the key header to every request
{
    public override void Process(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); ProcessNext(message, pipeline, index); }
    public override ValueTask ProcessAsync(PipelineMessage message, IReadOnlyList<PipelinePolicy> pipeline, int index)
    { message.Request.Headers.Set(name, value); return ProcessNextAsync(message, pipeline, index); }
}
