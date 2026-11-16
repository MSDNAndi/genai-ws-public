// Lab 1 · step 7 (TypeScript) — the same weather task as step 4, but the framework runs the loop for you.
//
// What this shows: AI SDK 7 (package `ai`) + @ai-sdk/openai-compatible. ToolLoopAgent calls the model, runs your tools,
// appends the results and calls the model again, until it answers or the budget (stopWhen) is spent.
// What to notice, compared with 04_tool_loop.mjs: no message list, no JSON parsing — each tool is a zod schema plus
// an execute function.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { ToolLoopAgent, isStepCount, tool } from "ai";
import { z } from "zod";

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

// ---- 2. The provider: AI SDK's name for "client" ----
// One provider per endpoint; chatModel(<deployment>) speaks Chat Completions, like the OpenAI SDK in steps 1-5.
const workshop = createOpenAICompatible({ name: "workshop", baseURL: BASE, apiKey: KEY, headers: HEADERS });
// Optional GENAI_REASONING_EFFORT -> sent as reasoning_effort. AI SDK 7 has a portable call setting for it (`reasoning`);
// the provider-specific spelling does the same: providerOptions: { workshop: { reasoningEffort: "low" } }
const REASONING = process.env.GENAI_REASONING_EFFORT;

const FAKE_WEATHER = { paris: [19, "light rain"], mannheim: [22, "sunny"], jacksonville: [31, "thunderstorms"] };

// ---- 3. The agent: model + instructions + tools + a step budget, all in one object ----
const agent = new ToolLoopAgent({
  model: workshop.chatModel(MODEL),
  reasoning: REASONING,
  instructions: "Use the tools for facts. Be brief.",   // = the system prompt
  tools: {
    get_weather: tool({
      description: "Current weather for a city.",
      inputSchema: z.object({ city: z.string() }),      // becomes the JSON Schema the model sees
      execute: async ({ city }) => {                    // the code that runs when the model asks
        const [temp, sky] = FAKE_WEATHER[city.toLowerCase()] ?? [20, "unknown"];
        return { city, temp_c: temp, sky };
      },
    }),
    to_fahrenheit: tool({
      description: "Convert a temperature from Celsius to Fahrenheit.",
      inputSchema: z.object({ celsius: z.number() }),
      execute: async ({ celsius }) => ({ celsius, fahrenheit: Math.round((celsius * 9 / 5 + 32) * 10) / 10 }),
    }),
  },
  stopWhen: isStepCount(6),                         // the budget from step 4 (ToolLoopAgent's default is 20 steps)
});

// ---- 4. One call runs the whole loop ----
const result = await agent.generate({ prompt: "What's the weather in Paris, and what is that temperature in Fahrenheit?" });

// ---- 5. What came back: every step, the final text and the total token count ----
// Every model call is a step; the framework kept the tool calls and results for you.
for (const [i, step] of result.steps.entries()) {
  for (const call of step.toolCalls) {
    const output = step.toolResults.find((r) => r.toolCallId === call.toolCallId)?.output;   // match result to call by id
    console.log(`  tool call #${i + 1}: ${call.toolName}(${JSON.stringify(call.input)}) -> ${JSON.stringify(output)}`);
  }
}
// finishReason "tool-calls" = the last step still wanted a tool, i.e. the budget ran out
if (result.finishReason === "tool-calls") console.log("Stopped: step budget exhausted.");
else console.log(`\nANSWER after ${result.steps.length - 1} tool round(s): ${result.text}`);
console.log(`[${result.steps.length} model calls, ${result.usage.totalTokens} tokens in total]`);

// Try this:
//  * stopWhen: isStepCount(1) — the agent stops after the first tool call: the budget is YOUR stop condition.
//  * const s = await agent.stream({ prompt }); for await (const t of s.textStream) process.stdout.write(t);
//  * Structured final answer: new ToolLoopAgent({ ..., output: Output.object({ schema: z.object({ ... }) }) }) -> result.output
//    (the openai-compatible provider needs supportsStructuredOutputs: true to send the JSON Schema).
