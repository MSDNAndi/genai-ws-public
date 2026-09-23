// STARTER - complete the TODO block(s). The finished version is in solution/04_tool_loop.mjs
// Lab 1 · step 4 — the tool-call loop, by hand. This loop is the foundation of every agent you will see today.
//
// model -> "please call get_weather({city: 'Paris'})" -> YOUR code runs it -> result goes back as a "tool" message ->
// model answers (or asks for another tool). Frameworks (AI SDK, Agent Framework, LangChain, ...) run exactly this loop
// for you — see 07_ai_sdk_agent.mjs.
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
// Optional: GENAI_REASONING_EFFORT=low (gpt-5 family) or none (local "thinking" models) keeps answers fast and cheap
const EXTRA = process.env.GENAI_REASONING_EFFORT ? { reasoning_effort: process.env.GENAI_REASONING_EFFORT } : {};

const FAKE_WEATHER = { paris: [19, "light rain"], mannheim: [22, "sunny"], jacksonville: [31, "thunderstorms"] };

function get_weather({ city }) {
  const [temp, sky] = FAKE_WEATHER[city.toLowerCase()] ?? [20, "unknown"];
  return JSON.stringify({ city, temp_c: temp, sky });
}

function to_fahrenheit({ celsius }) {
  return JSON.stringify({ celsius, fahrenheit: Math.round((celsius * 9 / 5 + 32) * 10) / 10 });
}

const TOOLS = [
  { type: "function", function: {
    name: "get_weather", description: "Current weather for a city.",
    parameters: { type: "object", properties: { city: { type: "string" } }, required: ["city"] } } },
  { type: "function", function: {
    name: "to_fahrenheit", description: "Convert a temperature from Celsius to Fahrenheit.",
    parameters: { type: "object", properties: { celsius: { type: "number" } }, required: ["celsius"] } } },
];
const IMPLEMENTATIONS = { get_weather, to_fahrenheit };

const messages = [{ role: "system", content: "Use the tools for facts. Be brief." },
                  { role: "user", content: "What's the weather in Paris, and what is that temperature in Fahrenheit?" }];

const BUDGET = 6;                                   // a budget: agents need a stop condition
let step = 0;
for (; step < BUDGET; step++) {
  const response = await client.chat.completions.create({ model: MODEL, messages, tools: TOOLS, ...EXTRA });
  const msg = response.choices[0].message;
  // TODO 2: append the assistant message; if it has no tool_calls print the answer and stop (break); otherwise run each tool and append a {role: 'tool', ...} message per call
  throw new Error("TODO 2: append the assistant message; if it has no tool_calls print the answer and stop (break); otherwise run each tool and append a {role: 'tool', ...} message per call");
}
if (step === BUDGET) console.log("Stopped: step budget exhausted.");

// Try this:
//  * Ask something that needs no tool ("Tell me a joke") — the model answers directly.
//  * Ask for three cities at once — many models return several tool_calls in ONE turn (parallel tool calls).
//  * Remove the system prompt or a tool description and watch the tool choice get worse.
