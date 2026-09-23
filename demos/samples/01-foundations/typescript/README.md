# TypeScript track (scaffold)

Not written yet. Decisions fixed so it stays a twin of the Python and C# files
rather than a separate dialect.

## Stack

| Concern | Pick | Version (2026-09-20) |
|---|---|---|
| Runtime | Node 20+ | |
| Runner | `tsx` (single file, no build step) | 4.23.15 |
| Client | `openai` npm, pointed at `base_url` - the twin of the other tracks | |
| Schemas | `zod` | 4.6.5 |
| Agents (Segment 3) | Vercel AI SDK 7 (`ai`) - **Microsoft Agent Framework has no TS SDK** | 7.0.107 |
| MCP | `@modelcontextprotocol/sdk` | 1.30.0 |

Unlike Python and C#, TypeScript has no single-file dependency declaration, so
this track gets one `package.json` for the whole folder and samples run with
`npx tsx 01_hello_model.ts`.

## To do

1. `shared/typescript/` - the `providers.json` loader and the `dump`/`inspect`
   helpers, matching `genaiclass` and `GenAIClass` (same function names).
2. Twins of `01_hello_model`, `03_structured_output` (zod), `04_tool_calling`,
   `08_inspecting_responses`.
3. Decide Node vs Bun before the setup guide goes out.

`inspect()` is easiest here - the HTML view is the same file format, and Node
can open it the same way.
