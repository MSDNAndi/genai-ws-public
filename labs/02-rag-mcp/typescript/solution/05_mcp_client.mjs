// Lab 2 · step 5 — talk to your MCP server from code (this is what every MCP host does under the hood).
import { join } from "node:path";
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const SERVER = join(import.meta.dirname, "04_mcp_server.mjs");

// Gotcha: stdio MCP clients start the server with a MINIMAL environment (HOME, LOGNAME, PATH, SHELL, TERM, USER) — pass
// yours on, or make sure the server can find labs/.env on its own (ours can). MCP hosts have an "env" field for this.
const transport = new StdioClientTransport({ command: process.execPath, args: [SERVER], env: process.env });
const client = new Client({ name: "lab2-client", version: "1.0.0" });
await client.connect(transport);                    // starts `node 04_mcp_server.mjs` and does the MCP handshake
try {
  const { tools } = await client.listTools();
  console.log("tools:", JSON.stringify(tools.map((t) => [t.name, (t.description ?? "").split(".")[0]])));
  const result = await client.callTool({ name: "search_docs", arguments: { query: "night flight altitude limit", k: 2 } });
  if (result.isError) throw new Error(`search_docs failed: ${result.content[0]?.text}`);
  for (const block of result.content) {
    console.log("hit:", JSON.stringify(JSON.parse(block.text)).slice(0, 220));
  }
  const doc = await client.readResource({ uri: "kestrel://docs/kestrel_customer_service_policy" });
  console.log("resource:", doc.contents[0].text.slice(0, 120).replaceAll("\n", " "), "...");
  const { prompts } = await client.listPrompts();
  console.log("prompts:", prompts.map((p) => p.name));
} finally {
  await client.close();                             // also stops the server process
}
