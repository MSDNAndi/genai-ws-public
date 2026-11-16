// Lab 1 · step 4 — the tool-call loop, by hand. This loop is the foundation of every agent you will see today.
//
// What this shows: the model cannot run code — it can only ASK for a tool. The loop is:
// model -> "please call get_weather({city: 'Paris'})" -> YOUR code runs it -> result goes back as a "tool" message ->
// model answers (or asks for another tool). Frameworks (AI SDK, Agent Framework, LangChain, ...) run exactly this loop
// for you — see 07_ai_sdk_agent.mjs.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import OpenAI from "openai";

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

// ---- 2. The tools: plain JavaScript functions (fake data, so the result is predictable) ----
const FAKE_WEATHER = { paris: [19, "light rain"], mannheim: [22, "sunny"], jacksonville: [31, "thunderstorms"] };

function get_weather({ city }) {
  const [temp, sky] = FAKE_WEATHER[city.toLowerCase()] ?? [20, "unknown"];
  return JSON.stringify({ city, temp_c: temp, sky });   // tools return text; JSON is easy for models
}

function to_fahrenheit({ celsius }) {
  return JSON.stringify({ celsius, fahrenheit: Math.round((celsius * 9 / 5 + 32) * 10) / 10 });
}

// What the model SEES of each tool: a name, a description and a JSON Schema for the arguments (not the code).
const TOOLS = [
  { type: "function", function: {
    name: "get_weather", description: "Current weather for a city.",
    parameters: { type: "object", properties: { city: { type: "string" } }, required: ["city"] } } },
  { type: "function", function: {
    name: "to_fahrenheit", description: "Convert a temperature from Celsius to Fahrenheit.",
    parameters: { type: "object", properties: { celsius: { type: "number" } }, required: ["celsius"] } } },
];
const IMPLEMENTATIONS = { get_weather, to_fahrenheit };   // tool name -> our function

// ---- 3. The conversation so far: the model has no memory, so we resend this list every time ----
const messages = [{ role: "system", content: "Use the tools for facts. Be brief." },
                  { role: "user", content: "What's the weather in Paris, and what is that temperature in Fahrenheit?" }];

// ---- 4. The loop: call the model, run what it asks for, send the results back, repeat ----
const BUDGET = 6;                                   // a budget: agents need a stop condition
let step = 0;
for (; step < BUDGET; step++) {
  const response = await client.chat.completions.create({ model: MODEL, messages, tools: TOOLS, ...EXTRA });
  const msg = response.choices[0].message;
  // >>> TODO 2: append the assistant message; if it has no tool_calls print the answer and stop (break); otherwise run each tool and append a {role: "tool", ...} message per call
  messages.push(msg);                               // the assistant turn (incl. its tool_calls) stays in the history
  if (!msg.tool_calls?.length) {                    // no tool requested = this is the final answer
    console.log(`\nANSWER after ${step} tool round(s): ${msg.content}`);
    break;
  }
  for (const call of msg.tool_calls) {              // the model may ask for several tools at once
    const args = JSON.parse(call.function.arguments || "{}");   // arguments arrive as a JSON string
    const result = IMPLEMENTATIONS[call.function.name](args);
    console.log(`  tool call #${step + 1}: ${call.function.name}(${JSON.stringify(args)}) -> ${result}`);
    messages.push({ role: "tool", tool_call_id: call.id, content: result });   // id = which request this answers
  }
  // <<< TODO
}
if (step === BUDGET) console.log("Stopped: step budget exhausted.");   // the loop ran out without a final answer

// Try this:
//  * Ask something that needs no tool ("Tell me a joke") — the model answers directly.
//  * Ask for three cities at once — many models return several tool_calls in ONE turn (parallel tool calls).
//  * Remove the system prompt or a tool description and watch the tool choice get worse.
