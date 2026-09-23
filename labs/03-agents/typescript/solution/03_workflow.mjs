// Lab 3 · step 3 — two agents, one workflow: a researcher (with the MCP tool) hands its notes to a writer.
//
// The AI SDK has no workflow builder — Agent Framework has SequentialBuilder / GroupChatBuilder, LangGraph draws graphs.
// Here the workflow is plain code: one agent's output becomes the next agent's input.
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { createMCPClient } from "@ai-sdk/mcp";
import { Experimental_StdioMCPTransport } from "@ai-sdk/mcp/mcp-stdio";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { ToolLoopAgent } from "ai";

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
const workshop = createOpenAICompatible({ name: "workshop", baseURL: BASE, apiKey: KEY, headers: HEADERS });
const REASONING = process.env.GENAI_REASONING_EFFORT;   // -> reasoning_effort (unset = not sent)

const LAB2_SERVER = join(LABS, "02-rag-mcp", "typescript", "solution", "04_mcp_server.mjs");   // the finished Lab 2 server
if (!existsSync(join(LABS, "02-rag-mcp", "build", "index.json"))) {
  throw new Error("The Lab 2 index is missing - run labs/02-rag-mcp/typescript/solution/02_embed.mjs first.");
}

const TASK = "Customer question: 'My Standard delivery arrived 41 minutes late - what do I get, and why was it late?'";

const docs = await createMCPClient({
  transport: new Experimental_StdioMCPTransport({ command: process.execPath, args: [LAB2_SERVER], env: process.env }),
});
try {
  const model = workshop.chatModel(MODEL);
  let researcher, writer;
  // >>> TODO 1: create the researcher (uses the docs tools, returns cited facts only) and the writer (turns the facts into a friendly 80-word reply)
  researcher = new ToolLoopAgent({ id: "researcher", model, reasoning: REASONING, tools: await docs.tools(),
    instructions: "Find the facts needed to answer the customer. Call search_docs. Return a bullet list of facts, " +
      "each with the chunk id it came from. No prose." });
  writer = new ToolLoopAgent({ id: "writer", model, reasoning: REASONING,
    instructions: "You write replies to Kestrel customers: friendly, at most 80 words, only facts from the " +
      "researcher's notes, no chunk ids in the text." });
  // <<< TODO
  const research = await researcher.generate({ prompt: TASK });
  const reply = await writer.generate({ prompt: `${TASK}\n\nThe researcher's notes:\n${research.text}` });
  console.log("RESEARCHER NOTES:\n", research.text.slice(0, 800), "\n");
  console.log("WRITER:\n", reply.text);
} finally {
  await docs.close();
}
