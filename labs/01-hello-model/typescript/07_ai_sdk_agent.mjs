// Lab 1 · step 7 (TypeScript) — the same weather task as step 4, but the framework runs the loop for you.
//
// AI SDK 7 (package `ai`) + @ai-sdk/openai-compatible: ToolLoopAgent calls the model, runs your tools, appends the
// results and calls the model again, until it answers or the budget (stopWhen) is spent. Compare with 04_tool_loop.mjs:
// no message bookkeeping, no JSON parsing — tools are declared with a zod schema and an execute function.
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
// One provider per endpoint; chatModel(<deployment>) speaks Chat Completions, like the OpenAI SDK in steps 1-5.
const workshop = createOpenAICompatible({ name: "workshop", baseURL: BASE, apiKey: KEY, headers: HEADERS });
// Optional GENAI_REASONING_EFFORT -> sent as reasoning_effort. AI SDK 7 has a portable call setting for it (`reasoning`);
// the provider-specific spelling does the same: providerOptions: { workshop: { reasoningEffort: "low" } }
const REASONING = process.env.GENAI_REASONING_EFFORT;

const FAKE_WEATHER = { paris: [19, "light rain"], mannheim: [22, "sunny"], jacksonville: [31, "thunderstorms"] };

const agent = new ToolLoopAgent({
  model: workshop.chatModel(MODEL),
  reasoning: REASONING,
  instructions: "Use the tools for facts. Be brief.",
  tools: {
    get_weather: tool({
      description: "Current weather for a city.",
      inputSchema: z.object({ city: z.string() }),
      execute: async ({ city }) => {
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

const result = await agent.generate({ prompt: "What's the weather in Paris, and what is that temperature in Fahrenheit?" });

// Every model call is a step; the framework kept the tool calls and results for you.
for (const [i, step] of result.steps.entries()) {
  for (const call of step.toolCalls) {
    const output = step.toolResults.find((r) => r.toolCallId === call.toolCallId)?.output;
    console.log(`  tool call #${i + 1}: ${call.toolName}(${JSON.stringify(call.input)}) -> ${JSON.stringify(output)}`);
  }
}
if (result.finishReason === "tool-calls") console.log("Stopped: step budget exhausted.");
else console.log(`\nANSWER after ${result.steps.length - 1} tool round(s): ${result.text}`);
console.log(`[${result.steps.length} model calls, ${result.usage.totalTokens} tokens in total]`);

// Try this:
//  * stopWhen: isStepCount(1) — the agent stops after the first tool call: the budget is YOUR stop condition.
//  * const s = await agent.stream({ prompt }); for await (const t of s.textStream) process.stdout.write(t);
//  * Structured final answer: new ToolLoopAgent({ ..., output: Output.object({ schema: z.object({ ... }) }) }) -> result.output
//    (the openai-compatible provider needs supportsStructuredOutputs: true to send the JSON Schema).
