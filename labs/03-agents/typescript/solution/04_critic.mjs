// Lab 3 · step 4 — add a critic: researcher -> writer -> critic -> writer (revise), as a group chat with a fixed
// speaking order and a hard round limit. The critic can end it early by saying APPROVED.
//
// Agent Framework declares this (GroupChatBuilder with a selection function, max_rounds, a termination condition);
// with the AI SDK it is a loop over a shared transcript that every agent reads.
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

const TASK = "Write the FAQ entry: 'Can I send a 150 Wh power bank with Kestrel, and what happens if my parcel is lost?'";
const MAX_ROUNDS = 5;                               // a hard limit: the conversation always ends

function nextSpeaker(round) {
  // >>> TODO 2: return who speaks next - round 0 the researcher, then writer and critic take turns
  if (round === 0) return "researcher";
  return round % 2 ? "writer" : "critic";
  // <<< TODO
}

const docs = await createMCPClient({
  transport: new Experimental_StdioMCPTransport({ command: process.execPath, args: [LAB2_SERVER], env: process.env }),
});
try {
  const model = workshop.chatModel(MODEL);
  const agents = {
    researcher: new ToolLoopAgent({ id: "researcher", model, reasoning: REASONING, tools: await docs.tools(),
      instructions: "Collect the facts with search_docs. Bullet list with chunk ids." }),
    writer: new ToolLoopAgent({ id: "writer", model, reasoning: REASONING,
      instructions: "Write or revise the FAQ entry (max 90 words) from the researcher's facts and the critic's feedback." }),
    critic: new ToolLoopAgent({ id: "critic", model, reasoning: REASONING,
      instructions: "Check the latest FAQ draft against the researcher's facts. If it is correct, complete and under " +
        "90 words, reply only APPROVED. Otherwise list the fixes." }),
  };

  const transcript = [{ author: "user", text: TASK }];   // the shared group chat: every agent reads all of it
  const drafts = [];
  for (let round = 0; round < MAX_ROUNDS; round++) {
    const speaker = nextSpeaker(round);
    const prompt = transcript.map((m) => `[${m.author}]\n${m.text}`).join("\n\n");
    const { text } = await agents[speaker].generate({ prompt });
    transcript.push({ author: speaker, text });
    if (speaker === "writer") drafts.push(text);
    if (speaker === "critic" && text.includes("APPROVED")) break;   // the termination condition
  }
  console.log(`${drafts.length} writer draft(s). Final:\n${drafts.at(-1) ?? "(none)"}`);
} finally {
  await docs.close();
}
