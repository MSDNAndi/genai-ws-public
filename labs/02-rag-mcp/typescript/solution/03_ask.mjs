// Lab 2 · step 3 — retrieve, then answer WITH citations (or admit that the documents don't say).
//
//   node 03_ask.mjs "What is the maximum payload of a K-4 in rain?"
import { existsSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import OpenAI from "openai";

let LABS = import.meta.dirname;                     // labs/.env (real environment variables win)
while (!existsSync(join(LABS, "_tools", "make_starters.py")) && LABS !== dirname(LABS)) LABS = dirname(LABS);
// labs/.env, or one .env at the repo root: load every .env from labs/ upward (never overwrites) - nearest wins
for (let dir = LABS; ; dir = dirname(dir)) {
  if (existsSync(join(dir, ".env"))) process.loadEnvFile(join(dir, ".env"));
  if (dirname(dir) === dir) break;
}

const { GENAI_BASE_URL: BASE, GENAI_API_KEY: KEY, GENAI_MODEL: MODEL } = process.env;
if (!BASE || !KEY || !MODEL) throw new Error("Set GENAI_BASE_URL, GENAI_API_KEY and GENAI_MODEL in labs/.env (see .env.example)");
const API_KEY_HEADER = (process.env.GENAI_KEY_HEADER ?? "api-key") === "api-key";
const client = new OpenAI({ baseURL: BASE, apiKey: KEY, defaultHeaders: API_KEY_HEADER ? { "api-key": KEY } : undefined });
// Optional: GENAI_REASONING_EFFORT=low (gpt-5 family) or none (local "thinking" models) keeps answers fast and cheap
const EXTRA = process.env.GENAI_REASONING_EFFORT ? { reasoning_effort: process.env.GENAI_REASONING_EFFORT } : {};

// --- retrieval: load build/index.json (written by 02_embed.mjs) and search it (cosine top-k) -----------------------
const INDEX = join(LABS, "02-rag-mcp", "build", "index.json");
if (!existsSync(INDEX)) throw new Error(`${INDEX} not found - run 02_embed.mjs first`);
const index = JSON.parse(readFileSync(INDEX, "utf8"));   // { embed_model, dims, items: [{ id, doc, chunk, text, vector }] }
const EMBED_KEY = process.env.EMBED_API_KEY || KEY;      // embeddings may come from another endpoint (EMBED_BASE_URL)
const embedder = new OpenAI({ baseURL: process.env.EMBED_BASE_URL || BASE, apiKey: EMBED_KEY,
  defaultHeaders: API_KEY_HEADER ? { "api-key": EMBED_KEY } : undefined });

async function search(query, k = 4) {
  const r = await embedder.embeddings.create({ model: index.embed_model, input: [query], encoding_format: "float" });
  const q = r.data[0].embedding;                         // the query must be embedded with the SAME model as the chunks
  if (q.length !== index.dims) throw new Error(`index has ${index.dims} dims, query has ${q.length} - re-run 02_embed.mjs`);
  const length = Math.hypot(...q);
  return index.items
    .map(({ vector, ...chunk }) => ({ ...chunk, score: vector.reduce((sum, x, i) => sum + x * q[i], 0) / length }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k)
    .map((hit) => ({ ...hit, score: Math.round(hit.score * 1000) / 1000 }));
}

// --- ask ------------------------------------------------------------------------------------------------------------
const QUESTIONS = process.argv.length > 2 ? process.argv.slice(2) : [
  "What is the maximum payload of a K-4 Kestrel in rain?",
  "A Standard delivery arrived 41 minutes late. What does the customer get?",
  "Which latch firmware version fixed the early-release bug?",
  "Who is the CEO of Kestrel?",                          // not in the documents -> must say so
];

for (const question of QUESTIONS) {
  const hits = await search(question, 4);
  const sources = hits.map((h, n) => `[${n + 1}] (${h.doc})\n${h.text}`).join("\n\n");
  let system;
  // >>> TODO 2: write the grounding instructions: answer only from the numbered sources, cite them like [2], say "not in the documents" otherwise
  system = "You answer questions about Kestrel Drone Logistics using ONLY the numbered sources below. " +
    "Cite every fact with its source number in square brackets, e.g. [2]. If the sources do not contain " +
    "the answer, reply exactly: Not in the documents.\n\nSOURCES:\n" + sources;
  // <<< TODO
  const r = await client.chat.completions.create({ model: MODEL, ...EXTRA, messages: [{ role: "system", content: system },
                                                                                     { role: "user", content: question }] });
  console.log(`\nQ: ${question}\nA: ${(r.choices[0].message.content ?? "").trim()}`);
  console.log("   sources: " + hits.map((h, n) => `[${n + 1}] ${h.id} (${h.score})`).join("; "));
}
