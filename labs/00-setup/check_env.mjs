// check_env.mjs — is my laptop ready for the TypeScript track?      node 00-setup/check_env.mjs   (from labs/, after npm install)
import { existsSync } from "node:fs";
import { dirname, join } from "node:path";
import OpenAI from "openai";

let LABS = import.meta.dirname;
while (!existsSync(join(LABS, "_tools", "make_starters.py")) && LABS !== dirname(LABS)) LABS = dirname(LABS);
// labs/.env, or one .env at the repo root: load every .env from labs/ upward (never overwrites) - nearest wins
for (let dir = LABS; ; dir = dirname(dir)) {
  if (existsSync(join(dir, ".env"))) process.loadEnvFile(join(dir, ".env"));
  if (dirname(dir) === dir) break;
}

let fails = 0;
const report = (ok, what, detail = "") => { if (!ok) fails++; console.log(`${ok ? "✅" : "❌"} ${what}${!ok && detail ? "\n     " + detail : ""}`); };
const hint = (e) => e.status === 401 ? "401: key missing or wrong. Check GENAI_API_KEY and GENAI_KEY_HEADER=api-key."
  : e.status === 404 ? "404: model/deployment name or URL wrong (GENAI_BASE_URL must end with /openai/v1 or /v1)."
  : e.status === 429 ? "429: your per-minute token limit was hit - wait a minute, then retry."
  : e.status === 403 ? "403: today's token quota for your key is used up (or the key may not use this model) - ask the instructor."
  : String(e.message).slice(0, 200);

const [major] = process.versions.node.split(".").map(Number);
report(major >= 22, `Node ${process.versions.node}`, "Node 22+ required (24 LTS recommended): https://nodejs.org");
for (const pkg of ["openai", "ai", "@ai-sdk/openai-compatible", "@ai-sdk/mcp", "@modelcontextprotocol/server", "zod"]) {
  try { await import(pkg); } catch { report(false, `package ${pkg} missing`, "run: npm install   (in the labs folder)"); }
}
const need = ["GENAI_BASE_URL", "GENAI_API_KEY", "GENAI_MODEL", "GENAI_EMBED_MODEL"].filter((n) => !process.env[n] || process.env[n].includes("<"));
if (need.length) { report(false, `settings missing: ${need.join(", ")}`, "copy labs/.env.example to labs/.env"); process.exit(1); }
const { GENAI_BASE_URL: BASE, GENAI_API_KEY: KEY, GENAI_MODEL: MODEL, GENAI_EMBED_MODEL: EMBED } = process.env;
console.log(`   endpoint ${BASE} · model ${MODEL} · key …${KEY.slice(-4)}`);
const client = new OpenAI({ baseURL: BASE, apiKey: KEY, timeout: 120_000, maxRetries: 1,
  defaultHeaders: (process.env.GENAI_KEY_HEADER ?? "api-key") === "api-key" ? { "api-key": KEY } : undefined });
const EXTRA = process.env.GENAI_REASONING_EFFORT ? { reasoning_effort: process.env.GENAI_REASONING_EFFORT } : {};

try {
  const r = await client.chat.completions.create({ model: MODEL, ...EXTRA, messages: [{ role: "user", content: "Reply with the word ready." }] });
  report(true, `chat: '${(r.choices[0].message.content ?? "").trim().slice(0, 40)}'`);
} catch (e) { report(false, "chat call failed", hint(e)); process.exit(1); }
try {
  const r = await client.chat.completions.create({ model: MODEL, ...EXTRA, messages: [{ role: "user", content: "What's the weather in Paris?" }],
    tools: [{ type: "function", function: { name: "get_weather", description: "Weather for a city",
      parameters: { type: "object", properties: { city: { type: "string" } }, required: ["city"] } } }] });
  const call = r.choices[0].message.tool_calls?.[0];
  report(true, call ? `tool calling: ${call.function.name}(${call.function.arguments})` : "tool calling: model answered without the tool (try another model)");
} catch (e) { report(false, "tool calling failed", hint(e)); }
try {
  const e = await client.embeddings.create({ model: EMBED, input: ["hello"], encoding_format: "float" });
  report(true, `embeddings: ${EMBED} -> ${e.data[0].embedding.length} dims`);
} catch (e) { report(false, "embeddings failed (needed for Lab 2)", hint(e)); }
if (process.env.OLLAMA_BASE_URL) {
  try {
    const r = await fetch(process.env.OLLAMA_BASE_URL.replace(/\/$/, "") + "/models", { signal: AbortSignal.timeout(10_000) });
    console.log(`✅ Ollama: ${(await r.json()).data.length} model(s) at ${process.env.OLLAMA_BASE_URL}`);
  } catch (e) { console.log(`⚠️  Ollama not reachable (needed for Lab 1 step 5 and Lab 4): ${e.message}`); }
}
console.log(fails === 0 ? "\nAll set - see you at the workshop!" : "\nPlease fix the ❌ items (details above).");
process.exit(fails === 0 ? 0 : 1);
