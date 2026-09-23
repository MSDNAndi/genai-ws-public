// Lab 3 · step 2 — give the agent the Lab 2 documents through MCP. No adapter code: an MCP server IS a tool source.
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

// The Lab 2 MCP server — always the finished TypeScript one — started as a child process over stdio.
const LAB2_SERVER = join(LABS, "02-rag-mcp", "typescript", "solution", "04_mcp_server.mjs");
if (!existsSync(join(LABS, "02-rag-mcp", "build", "index.json"))) {
  throw new Error("The Lab 2 index is missing - run labs/02-rag-mcp/typescript/solution/02_embed.mjs first.");
}

const docs = await createMCPClient({
  transport: new Experimental_StdioMCPTransport({ command: process.execPath, args: [LAB2_SERVER],
    env: process.env }),                            // stdio children get a minimal environment otherwise
});
try {
  const agent = new ToolLoopAgent({
    id: "KestrelSupport",
    model: workshop.chatModel(MODEL),
    reasoning: REASONING,
    tools: await docs.tools(),                      // the server's tools (search_docs) as AI SDK tools
    instructions: "You answer questions about Kestrel Drone Logistics. Always call search_docs first and cite the " +
      "chunk ids you used, like (kestrel_operations_handbook#2). If the documents do not answer the question, say so.",
  });
  for (const question of ["Can I fly a K-2 Sparrow at night at 100 m?",
                          "My payload was lost in August. How quickly will someone call me, and what do I get?"]) {
    const result = await agent.generate({ prompt: question });
    console.log(`> ${question}\n  ${result.text.trim()}\n`);
  }
} finally {
  await docs.close();                               // stops the server process
}
