// Lab 1 · step 1 — your first call.
//
// The same few lines talk to Azure AI Foundry, the workshop gateway, OpenAI, Ollama, LM Studio, Foundry Local, vLLM ...
// Only three things change between them: baseURL, the key, and the model name.
//   node 01_hello.mjs          (Node 22+; run `npm install` once in labs/)
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import OpenAI from "openai";

// Settings live in labs/.env: walk up to the labs folder (the one with _tools/make_starters.py) and load it.
// Real environment variables win - process.loadEnvFile never overwrites a variable that is already set.
let LABS = import.meta.dirname;
while (!existsSync(join(LABS, "_tools", "make_starters.py")) && LABS !== dirname(LABS)) LABS = dirname(LABS);
// labs/.env, or one .env at the repo root: load every .env from labs/ upward (never overwrites) - nearest wins
for (let dir = LABS; ; dir = dirname(dir)) {
  if (existsSync(join(dir, ".env"))) process.loadEnvFile(join(dir, ".env"));
  if (dirname(dir) === dir) break;
}

const { GENAI_BASE_URL: BASE, GENAI_API_KEY: KEY, GENAI_MODEL: MODEL } = process.env;
if (!BASE || !KEY || !MODEL) throw new Error("Set GENAI_BASE_URL, GENAI_API_KEY and GENAI_MODEL in labs/.env (see .env.example)");
// The workshop gateway (and Foundry keys) expect the key in an "api-key" header, not only as a Bearer token.
const HEADERS = (process.env.GENAI_KEY_HEADER ?? "api-key") === "api-key" ? { "api-key": KEY } : undefined;

const client = new OpenAI({ baseURL: BASE, apiKey: KEY, defaultHeaders: HEADERS });
// Optional: GENAI_REASONING_EFFORT=low (gpt-5 family) or none (local "thinking" models) keeps answers fast and cheap
const EXTRA = process.env.GENAI_REASONING_EFFORT ? { reasoning_effort: process.env.GENAI_REASONING_EFFORT } : {};

const response = await client.chat.completions.create({
  model: MODEL,
  ...EXTRA,
  messages: [
    { role: "system", content: "You are a concise assistant for a developer workshop." },
    { role: "user", content: "In two sentences: what is a token, and why should a developer care?" },
  ],
});

console.log(response.choices[0].message.content);
const usage = response.usage;
console.log(`\n[${response.model}] prompt=${usage?.prompt_tokens} completion=${usage?.completion_tokens} ` +
  `total=${usage?.total_tokens} tokens · finish_reason=${response.choices[0].finish_reason}`);

// Try this:
//  1. Change the system prompt ("answer like a pirate", "answer in German") and run again.
//  2. console.log(JSON.stringify(response, null, 2))  — look at everything that came back (ids, usage, filters...).
//  3. Set GENAI_MODEL=<another deployment> in labs/.env and compare.
