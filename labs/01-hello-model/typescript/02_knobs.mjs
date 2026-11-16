// Lab 1 · step 2 — the sampling knobs: temperature, top_p, seed ... and the models that ignore them.
//
// What this shows: the same prompt asked 3 times per setting, so you can see how "random" each setting makes the answer.
// Reasoning models (gpt-5 family, o-series, many "thinking" models) lock temperature/top_p and offer
// `reasoning_effort` instead — so if the model rejects a knob, the script switches to that experiment.
// Tip: run it once with GENAI_MODEL=gpt-5-nano and once with GENAI_MODEL=$GENAI_MODEL_2 (e.g. DeepSeek-V4.1-Flash-1017) or Ollama.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import OpenAI, { BadRequestError } from "openai";

// ---- 1. Settings and client (same as step 1) ----
let LABS = import.meta.dirname;                     // labs/.env (real environment variables win)
while (!existsSync(join(LABS, "_tools", "make_starters.py")) && LABS !== dirname(LABS)) LABS = dirname(LABS);
// labs/.env, or one .env at the repo root: load every .env from labs/ upward (never overwrites) - nearest wins
for (let dir = LABS; ; dir = dirname(dir)) {
  if (existsSync(join(dir, ".env"))) process.loadEnvFile(join(dir, ".env"));
  if (dirname(dir) === dir) break;
}

const { GENAI_BASE_URL: BASE, GENAI_API_KEY: KEY, GENAI_MODEL: MODEL } = process.env;
if (!BASE || !KEY || !MODEL) throw new Error("Set GENAI_BASE_URL, GENAI_API_KEY and GENAI_MODEL in labs/.env (see .env.example)");
const HEADERS = (process.env.GENAI_KEY_HEADER ?? "api-key") === "api-key" ? { "api-key": KEY } : undefined;
const client = new OpenAI({ baseURL: BASE, apiKey: KEY, defaultHeaders: HEADERS });
// Only "none" is passed on here (local "thinking" models answer much faster without thinking);
// the reasoning_effort experiment itself is further down.
const EXTRA = process.env.GENAI_REASONING_EFFORT === "none" ? { reasoning_effort: "none" } : {};

const PROMPT = "Invent a name for a coffee shop run by robots. Answer with the name only.";

// ---- 2. Helpers: ask the same question with whatever knobs we pass in ----
async function ask(knobs) {
  const r = await client.chat.completions.create({ model: MODEL, messages: [{ role: "user", content: PROMPT }], ...EXTRA, ...knobs });
  return (r.choices[0].message.content ?? "").trim();
}

async function threeTimes(knobs) {                   // one after the other, like a user pressing "regenerate"
  const names = [];
  for (let i = 0; i < 3; i++) names.push(await ask(knobs));
  return JSON.stringify(names);
}

// ---- 3. The experiment: 3 answers per setting ----
try {
  for (const t of [0.0, 1.0, 1.6]) {                 // temperature: 0 = safe/repetitive, higher = more creative
    console.log(`temperature=${t.toFixed(1)}: ${await threeTimes({ temperature: t })}`);
  }
  // top_p=0.1: only pick from the top 10% most likely words
  console.log(`temperature=1.0, top_p=0.1: ${await threeTimes({ temperature: 1.0, top_p: 0.1 })}`);
  // seed: asks for repeatable randomness — most providers only try their best
  console.log(`temperature=1.0, seed=42 (best effort!): ${await threeTimes({ temperature: 1.0, seed: 42 })}`);

// ---- 4. Plan B: the model said "400 Bad Request" to temperature -> try its own knob, reasoning_effort ----
} catch (e) {
  if (!(e instanceof BadRequestError)) throw e;     // any other error (network, 401 ...) is a real problem
  console.log(`'${MODEL}' rejected a sampling knob -> it is probably a reasoning model.\n  ${e.message.slice(0, 200)}`);
  console.log("Reasoning models expose a different knob: reasoning_effort (how long they think).");
  for (const effort of ["minimal", "low", "high"]) {
    const t0 = performance.now();                   // start a stopwatch: more thinking = slower
    let r;
    try {
      r = await client.chat.completions.create({ model: MODEL, reasoning_effort: effort,
        messages: [{ role: "user", content: "Is 1001 prime? One line." }] });
    } catch (e2) {                                  // not every model knows every effort level
      if (!(e2 instanceof BadRequestError)) throw e2;
      console.log(`  reasoning_effort=${effort}: not supported here (${e2.message.slice(0, 80)})`);
      continue;
    }
    const u = r.usage;
    const hidden = u?.completion_tokens_details?.reasoning_tokens;   // the hidden "thinking" tokens (if reported)
    console.log(`  reasoning_effort=${effort.padEnd(7)} ${((performance.now() - t0) / 1000).toFixed(1).padStart(5)}s  ` +
      `completion=${u?.completion_tokens} (reasoning=${hidden})  -> ${(r.choices[0].message.content ?? "").trim().slice(0, 60)}`);
  }
}

// What to notice:
//  * temperature 0 is "mostly the same", not "guaranteed identical"; seed is best-effort on most providers.
//  * top_p=0.1 narrows the choice to the few most likely tokens — similar effect to a low temperature.
//  * reasoning tokens are billed even though you never see them.
