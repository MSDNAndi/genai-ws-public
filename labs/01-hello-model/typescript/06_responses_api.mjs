// Lab 1 · stretch — the Responses API: the newer dialect at OpenAI and Foundry (/openai/v1/responses).
//
// Differences to Chat Completions you can see here: `input` + `instructions` instead of messages; server-side
// conversation state via `previous_response_id`; typed output items; streaming as semantic events.
// Works on Foundry and OpenAI. Local runners and gateways may only speak Chat Completions — that is why every
// other lab uses Chat Completions (see research/2026-09-22_framework-snippet-verification.md).
import { existsSync } from "node:fs";
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
const HEADERS = (process.env.GENAI_KEY_HEADER ?? "api-key") === "api-key" ? { "api-key": KEY } : undefined;
const client = new OpenAI({ baseURL: BASE, apiKey: KEY, defaultHeaders: HEADERS });
// The Responses API spells the reasoning knob differently: reasoning: { effort: ... }
const EXTRA = process.env.GENAI_REASONING_EFFORT ? { reasoning: { effort: process.env.GENAI_REASONING_EFFORT } } : {};

const first = await client.responses.create({ model: MODEL, instructions: "Be brief.", ...EXTRA,
  input: "Name one advantage of running a model locally." });
console.log("1:", first.output_text);

// The service keeps the conversation: refer to the previous turn by id instead of resending the history.
// (Needs the endpoint to store responses; if yours does not, resend the history as input items instead.)
try {
  const second = await client.responses.create({ model: MODEL, previous_response_id: first.id, ...EXTRA,
    input: "And one disadvantage? Same length." });
  console.log("2:", second.output_text);
} catch (e) {
  console.log("2: previous_response_id not supported here ->", String(e.message).slice(0, 120));
}

process.stdout.write("3 (streamed): ");
const stream = client.responses.stream({ model: MODEL, input: "Count from 1 to 5, comma separated.", ...EXTRA });
for await (const event of stream) {
  if (event.type === "response.output_text.delta") process.stdout.write(event.delta);
}
console.log();
