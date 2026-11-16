// STARTER - complete the TODO block(s). The finished version is in solution/03_structured.mjs
// Lab 1 · step 3 — structured output: a JSON Schema is a contract, not a hope.
//
// What this shows: we describe the shape we want (a zod schema), the SDK turns it into a JSON Schema, the service
// forces the model's answer to fit it, and we get a validated object back — no regex, no "please answer in JSON".
// What to notice: you can do maths on the result (total minutes) because the fields are real numbers.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import OpenAI from "openai";
import { zodResponseFormat } from "openai/helpers/zod";
import { z } from "zod";

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
// Optional "think less" knob (GENAI_REASONING_EFFORT=low); only sent when set (see step 1).
const EXTRA = process.env.GENAI_REASONING_EFFORT ? { reasoning_effort: process.env.GENAI_REASONING_EFFORT } : {};

// The free text we want to turn into data.
const TEXT = "Tomorrow at 10:50 the second segment starts: a 40-minute talk called 'The context window is the product', " +
  "covering embeddings, RAG, MCP and prompt injection, followed by a 30-minute hands-on lab.";

// ---- 2. The shape we want back: field names, types and descriptions all go into the JSON Schema ----
// zod tip: use z.number() for numbers here — z.int() also sends minimum/maximum (±2^53), which strict mode may reject.
let Session;
// TODO 1: describe the shape you want back — a Session with title, start time, talk minutes, lab minutes and a list of topics
throw new Error("TODO 1: describe the shape you want back — a Session with title, start time, talk minutes, lab minutes and a list of topics");

// ---- 3. The call: parse() sends the schema and checks the JSON answer against it ----
const format = zodResponseFormat(Session, "session");   // -> { type: "json_schema", json_schema: { strict: true, schema } }
const completion = await client.chat.completions.parse({
  model: MODEL,
  ...EXTRA,
  messages: [{ role: "system", content: "Extract the session described by the user." },
             { role: "user", content: TEXT }],
  response_format: format,
});

// ---- 4. What came back: a real object, not a string ----
const message = completion.choices[0].message;
const session = message.parsed;                         // a validated object (or null if the model refused)
console.log(session ? JSON.stringify(session, null, 2) : message.refusal);
console.log("\nThe JSON Schema that was sent:", Object.keys(format.json_schema.schema.properties));
console.log(session ? `Total minutes: ${session.talk_minutes + session.lab_minutes}` : "");   // numbers, so + is maths

// Try this: add `room: z.string().nullable()` or an enum field (level: z.enum(["beginner", "advanced"])) and see what
// the model does with information that is NOT in the text. (Strict mode: every field is required; use .nullable().)
