#:package OpenAI@2.13.0
#:package DotNetEnv@3.2.0
#:property PublishAot=false
// Lab 2 · step 3 — retrieve, then answer WITH citations (or admit that the documents don't say).
//
// dotnet run --file 03_ask.cs -- "What is the maximum payload of a K-4 in rain?"
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

// Two endpoints this time: chat, and the embeddings the index was built with (EMBED_BASE_URL/EMBED_API_KEY, see 02_embed)
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
// Optional: GENAI_REASONING_EFFORT=low (gpt-5 family) or none (local "thinking" models) keeps answers fast and cheap
var options = new ChatCompletionOptions();
if (Env("GENAI_REASONING_EFFORT", "") is { Length: > 0 } effort) options.ReasoningEffortLevel = new ChatReasoningEffortLevel(effort);

string[] questions = args.Length > 0 ? args :
[
    "What is the maximum payload of a K-4 Kestrel in rain?",
    "A Standard delivery arrived 41 minutes late. What does the customer get?",
    "Which latch firmware version fixed the early-release bug?",
    "Who is the CEO of Kestrel?",                          // not in the documents -> must say so
];

foreach (string question in questions)
{
    List<Hit> hits = await index.SearchAsync(question, k: 4);
    string sources = string.Join("\n\n", hits.Select((h, n) => $"[{n + 1}] ({h.Doc})\n{h.Text}"));
    string system;
    // >>> TODO 2: write the grounding instructions: answer only from the numbered sources, cite them like [2], say "not in the documents" otherwise
    system = "You answer questions about Kestrel Drone Logistics using ONLY the numbered sources below. " +
             "Cite every fact with its source number in square brackets, e.g. [2]. If the sources do not contain " +
             "the answer, reply exactly: Not in the documents.\n\nSOURCES:\n" + sources;
    // <<< TODO
    ChatCompletion r = await client.CompleteChatAsync([new SystemChatMessage(system), new UserChatMessage(question)], options);
    Console.WriteLine($"\nQ: {question}\nA: {r.Content[0].Text.Trim()}");
    Console.WriteLine("   sources: " + string.Join("; ", hits.Select((h, n) => $"[{n + 1}] {h.Id} ({h.Score})")));
}

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
