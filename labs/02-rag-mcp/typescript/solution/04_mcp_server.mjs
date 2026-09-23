// Lab 2 · step 4 — expose the retrieval as an MCP server (stdio). Any MCP host can now use your documents:
// Claude Code, GitHub Copilot (VS Code / CLI), LM Studio, MCP Inspector ... and the agents in Lab 3.
//
// Never console.log() in a stdio MCP server — stdout carries the protocol. Log with console.error (stderr).
// MCP TypeScript SDK v2 (@modelcontextprotocol/server 2.0): registerTool / registerResource / registerPrompt.
//   Try it: npx @modelcontextprotocol/inspector node 04_mcp_server.mjs
import { existsSync, readFileSync } from "node:fs";
import { dirname, join, parse } from "node:path";
import { McpServer, ResourceTemplate } from "@modelcontextprotocol/server";
import { serveStdio } from "@modelcontextprotocol/server/stdio";
import OpenAI from "openai";
import { z } from "zod";

let LABS = import.meta.dirname;                     // labs/.env, found from THIS file's folder: MCP hosts start us anywhere
while (!existsSync(join(LABS, "_tools", "make_starters.py")) && LABS !== dirname(LABS)) LABS = dirname(LABS);
// labs/.env, or one .env at the repo root: load every .env from labs/ upward (never overwrites) - nearest wins
for (let dir = LABS; ; dir = dirname(dir)) {
  if (existsSync(join(dir, ".env"))) process.loadEnvFile(join(dir, ".env"));
  if (dirname(dir) === dir) break;
}
const LAB2 = join(LABS, "02-rag-mcp");
const BUILD = join(LAB2, "build");

// --- retrieval, same as 03_ask.mjs: build/index.json + a query embedding, cosine top-k ----------------------------
const INDEX = join(BUILD, "index.json");
if (!existsSync(INDEX)) {
  console.error(`${INDEX} not found - run 02_embed.mjs first`);
  process.exit(1);
}
const index = JSON.parse(readFileSync(INDEX, "utf8"));
const KEY = process.env.EMBED_API_KEY || process.env.GENAI_API_KEY;
const embedder = new OpenAI({ baseURL: process.env.EMBED_BASE_URL || process.env.GENAI_BASE_URL, apiKey: KEY,
  defaultHeaders: (process.env.GENAI_KEY_HEADER ?? "api-key") === "api-key" ? { "api-key": KEY } : undefined });

async function search(query, k = 4) {
  const r = await embedder.embeddings.create({ model: index.embed_model, input: [query], encoding_format: "float" });
  const q = r.data[0].embedding;
  if (q.length !== index.dims) throw new Error(`index has ${index.dims} dims, query has ${q.length} - re-run 02_embed.mjs`);
  const length = Math.hypot(...q);
  return index.items
    .map(({ vector, ...chunk }) => ({ ...chunk, score: vector.reduce((sum, x, i) => sum + x * q[i], 0) / length }))
    .sort((a, b) => b.score - a.score)
    .slice(0, k)
    .map((hit) => ({ ...hit, score: Math.round(hit.score * 1000) / 1000 }));
}

// --- the MCP server --------------------------------------------------------------------------------------------------
function createServer() {
  const server = new McpServer({ name: "kestrel-docs", version: "1.0.0" });

  // >>> TODO 3: register a tool `search_docs(query, k=4)` that returns the top-k chunks (id, doc, score, text) — the description is what the model sees
  server.registerTool("search_docs", {
    description: "Search the Kestrel Drone Logistics documents (operations handbook, customer service policy, Q3 incident " +
      "review). Returns the k most relevant text chunks with their document name, chunk id and similarity score.",
    inputSchema: z.object({
      query: z.string().describe("What to look for, in plain words"),
      k: z.number().int().min(1).max(10).default(4).describe("How many chunks to return"),
    }),
  }, async ({ query, k }) => {
    const hits = await search(query, k);
    // one text block per hit (the Python server returns a list, which FastMCP sends the same way)
    return { content: hits.map(({ id, doc, score, text }) => ({ type: "text", text: JSON.stringify({ id, doc, score, text }) })) };
  });
  // <<< TODO

  server.registerResource("document", new ResourceTemplate("kestrel://docs/{name}", { list: undefined }),
    { description: "The full extracted text of one document, e.g. kestrel://docs/kestrel_operations_handbook", mimeType: "text/markdown" },
    async (uri, { name }) => {
      const file = `${parse(String(name)).name}.md`;   // keep only the stem: "../x.pdf" -> "x.md"
      const path = existsSync(join(BUILD, file)) ? join(BUILD, file) : join(LAB2, "data", "prebuilt", file);
      return { contents: [{ uri: uri.href, mimeType: "text/markdown", text: readFileSync(path, "utf8") }] };
    });

  server.registerPrompt("cite_answer", {
    description: "A reusable prompt: answer a question with citations from search_docs.",
    argsSchema: z.object({ question: z.string() }),
  }, ({ question }) => ({
    messages: [{ role: "user", content: { type: "text",
      text: `Use the search_docs tool, then answer with [doc#chunk] citations. Question: ${question}` } }],
  }));
  return server;
}

// serveStdio builds a server per connection from the factory and answers both MCP protocol eras (2025-11-25 clients
// that send `initialize`, 2026-07-28 clients that send `server/discover`). Errors go to stderr, never to stdout.
serveStdio(createServer, { onerror: (error) => console.error("[kestrel-docs]", error) });
