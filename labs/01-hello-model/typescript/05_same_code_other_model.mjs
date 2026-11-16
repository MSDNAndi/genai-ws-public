// Lab 1 · step 5 — same code, different model. The point of the day in one script.
//
// What this shows: one prompt and one tool request, sent unchanged to every endpoint it finds in labs/.env:
//   the workshop endpoint (GENAI_MODEL), a second vendor behind the same key (GENAI_MODEL_2),
//   local Ollama (OLLAMA_BASE_URL / OLLAMA_MODEL) and LM Studio (LMSTUDIO_BASE_URL) if they are running.
// What to notice: only the URL, key and model name differ — compare speed, answer length and tool-calling habits.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import OpenAI from "openai";

// ---- 1. Settings (same as step 1) ----
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

// ---- 2. The list of targets: [label, URL, key, headers, model] — add a line here to add a target ----
const env = process.env;
const [EFFORT, LOCAL_EFFORT] = [env.GENAI_REASONING_EFFORT, env.OLLAMA_REASONING_EFFORT];
const targets = [["workshop endpoint", BASE, KEY, HEADERS, MODEL]];
// same URL and key, just another model name
if (env.GENAI_MODEL_2) targets.push(["2nd vendor, same key", BASE, KEY, HEADERS, env.GENAI_MODEL_2]);
// local runtimes accept any key
if (env.OLLAMA_BASE_URL && env.OLLAMA_MODEL) targets.push(["local Ollama", env.OLLAMA_BASE_URL, "ollama", undefined, env.OLLAMA_MODEL]);
if (env.LMSTUDIO_BASE_URL) targets.push(["local LM Studio", env.LMSTUDIO_BASE_URL, "lm-studio", undefined, env.LMSTUDIO_MODEL ?? ""]);

// One tool, described exactly as in step 4.
const TOOL = { type: "function", function: { name: "get_weather", description: "Current weather for a city.",
  parameters: { type: "object", properties: { city: { type: "string" } }, required: ["city"] } } };
const seconds = (t0) => ((performance.now() - t0) / 1000).toFixed(1).padStart(5);   // stopwatch -> "  1.2"

// ---- 3. The same two calls against every target ----
for (let [label, base, key, headers, model] of targets) {
  // timeout: a laptop model can be slow; maxRetries: 0: if a target is down, say so at once
  const client = new OpenAI({ baseURL: base, apiKey: key, defaultHeaders: headers, timeout: 180_000, maxRetries: 0 });
  // Thinking knob: OLLAMA_REASONING_EFFORT for local models, GENAI_REASONING_EFFORT for the workshop model only
  const effort = label.startsWith("local") ? LOCAL_EFFORT : (label === "workshop endpoint" ? EFFORT : undefined);
  const extra = effort ? { reasoning_effort: effort } : {};
  try {
    if (!model) model = (await client.models.list()).data[0].id;   // LM Studio: take whatever model is loaded
    let t0 = performance.now();                     // call 1: plain chat, timed
    const r = await client.chat.completions.create({ model, ...extra, messages: [
      { role: "user", content: "Explain retrieval-augmented generation to a developer in one sentence." }] });
    const chatS = seconds(t0);
    t0 = performance.now();                         // call 2: does it ask for the tool?
    const r2 = await client.chat.completions.create({ model, tools: [TOOL], ...extra, messages: [
      { role: "user", content: "What's the weather in Mannheim?" }] });
    const calls = r2.choices[0].message.tool_calls ?? [];
    const toolS = seconds(t0);
    // ---- 4. What came back: time, length and answer per target ----
    console.log(`\n== ${label}: ${model}  (${base})`);
    console.log(`   chat  ${chatS}s  ${r.usage?.completion_tokens ?? "?"} tokens: ` +
      `${(r.choices[0].message.content ?? "").trim().slice(0, 160)}`);
    console.log(`   tools ${toolS}s  ` + (calls.map((c) => `${c.function.name}(${c.function.arguments})`).join(", ")
      || `no tool call -> ${(r2.choices[0].message.content ?? "").slice(0, 80)}`));
  } catch (e) {                                     // a missing local runtime must not stop the comparison
    console.log(`\n== ${label}: ${model || "?"}  skipped (${e.constructor.name}: ${String(e.message).slice(0, 120)})`);
  }
}

// What to notice: identical code, different answers, latency and tool-calling habits.
// Independence = being able to make this switch in one line — and knowing what you lose or gain when you do.
