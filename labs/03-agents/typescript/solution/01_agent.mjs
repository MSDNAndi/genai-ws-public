// Lab 3 · step 1 — an agent is the Lab 1 tool loop + a runtime: instructions, tools, memory (the history), a budget.
//
// AI SDK 7: ToolLoopAgent runs the loop from Lab 1 step 4 for you. Memory is explicit: YOU keep the messages array and
// pass it back in (Agent Framework keeps it in a session object; same idea).
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { ToolLoopAgent, isStepCount, tool } from "ai";
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
// Chat Completions through the OpenAI-compatible provider: every endpoint of the day speaks it (Foundry, the gateway,
// Ollama, LM Studio, the offline mock).
const workshop = createOpenAICompatible({ name: "workshop", baseURL: BASE, apiKey: KEY, headers: HEADERS });
// sent with every request as reasoning_effort (low for gpt-5 models, none for local thinking models); unset = not sent
const REASONING = process.env.GENAI_REASONING_EFFORT;

const FAKE_WEATHER = { paris: [19, "light rain"], mannheim: [22, "sunny"], jacksonville: [31, "thunderstorms"] };

const get_weather = tool({
  description: "Current weather for a city (temperature in Celsius and sky).",
  inputSchema: z.object({ city: z.string() }),
  execute: async ({ city }) => {
    const [temp, sky] = FAKE_WEATHER[city.toLowerCase()] ?? [20, "unknown"];
    return { city, temp_c: temp, sky };
  },
});

const to_fahrenheit = tool({
  description: "Convert Celsius to Fahrenheit.",
  inputSchema: z.object({ celsius: z.number() }),
  execute: async ({ celsius }) => ({ fahrenheit: Math.round((celsius * 9 / 5 + 32) * 10) / 10 }),
});

const agent = new ToolLoopAgent({
  id: "WeatherAgent",
  model: workshop.chatModel(MODEL),
  reasoning: REASONING,
  instructions: "You are a travel assistant. Use the tools for facts; answer in one or two sentences.",
  tools: { get_weather, to_fahrenheit },
  stopWhen: isStepCount(5),                         // the budget (default: 20 steps)
});

const messages = [];                                // the conversation memory lives here
for (const question of ["What's the weather in Mannheim?", "And what is that in Fahrenheit?", "Which city did I ask about?"]) {
  messages.push({ role: "user", content: question });
  const result = await agent.generate({ messages });
  messages.push(...result.responseMessages);       // what the agent added: tool calls, tool results, the answer
  console.log(`> ${question}\n  ${result.text.trim()}`);
}
// No history -> no memory: the agent cannot know what "that" refers to.
console.log("\nWithout the history:", (await agent.generate({ prompt: "And what is that in Fahrenheit?" })).text.trim().slice(0, 160));
