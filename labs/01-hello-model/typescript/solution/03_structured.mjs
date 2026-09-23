// Lab 1 · step 3 — structured output: a JSON Schema is a contract, not a hope.
//
// We describe the shape with zod; the SDK turns it into a JSON Schema, the service constrains decoding to it,
// and we get a validated object back (no regex, no "please answer in JSON").
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import OpenAI from "openai";
import { zodResponseFormat } from "openai/helpers/zod";
import { z } from "zod";

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
// Optional: GENAI_REASONING_EFFORT=low (gpt-5 family) or none (local "thinking" models) keeps answers fast and cheap
const EXTRA = process.env.GENAI_REASONING_EFFORT ? { reasoning_effort: process.env.GENAI_REASONING_EFFORT } : {};

const TEXT = "Tomorrow at 10:50 the second segment starts: a 40-minute talk called 'The context window is the product', " +
  "covering embeddings, RAG, MCP and prompt injection, followed by a 30-minute hands-on lab.";

// zod tip: use z.number() for numbers here — z.int() also sends minimum/maximum (±2^53), which strict mode may reject.
let Session;
// >>> TODO 1: describe the shape you want back — a Session with title, start time, talk minutes, lab minutes and a list of topics
Session = z.object({
  title: z.string(),
  start: z.string().describe("start time as HH:MM"),
  talk_minutes: z.number(),
  lab_minutes: z.number(),
  topics: z.array(z.string()),
});
// <<< TODO

const format = zodResponseFormat(Session, "session");   // -> { type: "json_schema", json_schema: { strict: true, schema } }
const completion = await client.chat.completions.parse({
  model: MODEL,
  ...EXTRA,
  messages: [{ role: "system", content: "Extract the session described by the user." },
             { role: "user", content: TEXT }],
  response_format: format,
});
const message = completion.choices[0].message;
const session = message.parsed;                         // a validated object (or null if the model refused)
console.log(session ? JSON.stringify(session, null, 2) : message.refusal);
console.log("\nThe JSON Schema that was sent:", Object.keys(format.json_schema.schema.properties));
console.log(session ? `Total minutes: ${session.talk_minutes + session.lab_minutes}` : "");

// Try this: add `room: z.string().nullable()` or an enum field (level: z.enum(["beginner", "advanced"])) and see what
// the model does with information that is NOT in the text. (Strict mode: every field is required; use .nullable().)
