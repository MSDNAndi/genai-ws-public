// Lab 2 · step 2 — embed every chunk and keep the vectors in one plain JSON file (the simplest "vector store").
//
// Same OpenAI-compatible client as Lab 1, different endpoint: /embeddings. Works with Foundry (text-embedding-3-*)
// and with Ollama (bge-m3, nomic-embed-text ...) — just change GENAI_EMBED_MODEL, or set EMBED_BASE_URL/EMBED_API_KEY
// to embed locally while chatting in the cloud.
// Step 1 (PDF -> chunks) is Python-only: ../../python/solution/01_ingest.py writes build/chunks.jsonl. Without it,
// this script uses the prebuilt chunks in data/prebuilt/ — same format, so the C#, Python and TypeScript labs can share it.
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import OpenAI from "openai";

let LABS = import.meta.dirname;                     // labs/.env (real environment variables win)
while (!existsSync(join(LABS, "_tools", "make_starters.py")) && LABS !== dirname(LABS)) LABS = dirname(LABS);
// labs/.env, or one .env at the repo root: load every .env from labs/ upward (never overwrites) - nearest wins
for (let dir = LABS; ; dir = dirname(dir)) {
  if (existsSync(join(dir, ".env"))) process.loadEnvFile(join(dir, ".env"));
  if (dirname(dir) === dir) break;
}

const KEY = process.env.EMBED_API_KEY || process.env.GENAI_API_KEY;
const BASE = process.env.EMBED_BASE_URL || process.env.GENAI_BASE_URL;
const EMBED_MODEL = process.env.GENAI_EMBED_MODEL;
if (!BASE || !KEY || !EMBED_MODEL) throw new Error("Set GENAI_BASE_URL, GENAI_API_KEY and GENAI_EMBED_MODEL in labs/.env (see .env.example)");
const HEADERS = (process.env.GENAI_KEY_HEADER ?? "api-key") === "api-key" ? { "api-key": KEY } : undefined;
const client = new OpenAI({ baseURL: BASE, apiKey: KEY, defaultHeaders: HEADERS });

const BUILD = join(LABS, "02-rag-mcp", "build");
const source = existsSync(join(BUILD, "chunks.jsonl")) ? join(BUILD, "chunks.jsonl")
  : join(LABS, "02-rag-mcp", "data", "prebuilt", "chunks.jsonl");
const chunks = readFileSync(source, "utf8").split("\n").filter((line) => line.trim()).map((line) => JSON.parse(line));

const t0 = performance.now();
const vectors = [];
for (let i = 0; i < chunks.length; i += 32) {       // batch: one request per 32 chunks
  const batch = chunks.slice(i, i + 32);
  // encoding_format "float": the Node SDK asks for base64 by default, which some local servers reject
  const r = await client.embeddings.create({ model: EMBED_MODEL, input: batch.map((c) => c.text), encoding_format: "float" });
  vectors.push(...r.data.map((d) => d.embedding));
}
// normalise once -> cosine similarity = dot product
const unit = vectors.map((v) => { const length = Math.hypot(...v); return v.map((x) => x / length); });

mkdirSync(BUILD, { recursive: true });
const index = { embed_model: EMBED_MODEL, dims: unit[0].length,
  items: chunks.map((c, i) => ({ ...c, vector: unit[i].map((x) => Math.round(x * 1e6) / 1e6) })) };
writeFileSync(join(BUILD, "index.json"), JSON.stringify(index), "utf8");   // one plain file = our "vector store"
console.log(`${chunks.length} chunks x ${index.dims} dims with '${EMBED_MODEL}' in ` +
  `${((performance.now() - t0) / 1000).toFixed(1)}s -> build/index.json`);
