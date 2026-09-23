# Segment 2 - Integrating AI (scaffold)

*The context window is the product.* Nothing here is written yet; this is the
planned shape so the numbering and the Python/C#/TS twin rule are fixed before
anyone starts.

## Planned samples

| # | Sample | Shows | Stack (verified 2026-09-20) |
|---|---|---|---|
| 01 | `parse_documents` | PDF/DOCX -> Markdown, and why chunking is where quality is won or lost | Docling 2.129 or MarkItDown 0.1.7; Azure Content Understanding as the managed twin |
| 02 | `chunk_and_embed` | chunk strategies side by side, embed, store | `text-embedding-3-large` (course endpoint) or `bge-m3` (local) |
| 03 | `vector_store` | the same corpus in LanceDB (file, zero setup) and pgvector (Docker) | LanceDB 0.39 / pgvector 0.8.6 |
| 04 | `hybrid_search_rerank` | keyword + vector + a reranker, measured against plain cosine | Cohere Rerank 4, or Azure AI Search semantic ranker |
| 05 | `cited_answers` | answering with citations, and refusing when retrieval is empty | - |
| 06 | `agentic_retrieval` | the managed path: query planning + answer synthesis | Azure AI Search agentic retrieval, GA API `2026-04-01` |
| 07 | `mcp_server` | wrap `search_docs` as an MCP server; use it from Claude Code, Copilot CLI, LM Studio | `mcp` 2.2.0 (py) / `ModelContextProtocol` 2.2.0 (C#) / `@modelcontextprotocol/sdk` 1.30.0 |
| 08 | `mcp_client` | call that server from your own code, not just from an IDE | same |
| 09 | `agent_skill` | the same capability as a `SKILL.md`, picked up by several vendors | [agentskills.io](https://agentskills.io) spec |
| 10 | `prompt_injection` | the attack, live, against sample 05 - then the mitigations that actually help | - |
| 11 | `evaluation` | a retrieval + answer eval that fails the build when quality drops | promptfoo 0.123, Azure AI Evaluation SDK 1.18.5 |

## Notes before building

* MCP spec revision **2026-07-28** is GA: stateless request/response, HTTP+SSE
  deprecated, CIMD instead of DCR. Samples must target that revision, not the
  2024/2025 shape most tutorials still show.
* Kernel Memory is **archived** - do not use it anywhere.
* Ragas' last release was 2026-01-13; prefer promptfoo for the lab.
* Keep a no-GPU, no-Docker path: LanceDB writes to a file and `bge-m3` runs on
  CPU, so the whole segment works on a locked-down laptop.
