# Lab recordings

Short terminal recordings of the finished (`solution/`) labs, run in the workshop codespace setup with the
default model `gpt-5-nano` (second vendor: `DeepSeek-V4.1-Flash-1017`). Each command is typed from `labs/`
exactly as you would type it. Long model waits are cut to 2 s, so the real runs take longer than the clips.
Model answers are different every run, so your output won't match word for word.

**Start with the overview:** [overview.mp4](overview.mp4) (about 7.5 min, all clips with title cards, normal speed; the result of every step stays on screen for 6 s so you can read it or pause).

| Clip | Shows | Command (from `labs/`) |
|---|---|---|
| [00_check_env](00_check_env.mp4) ([GIF](00_check_env.gif)) | the setup check: 8 green ticks | `python 00-setup/check_env.py` |
| [01_hello_python](01_hello_python.mp4) ([GIF](01_hello_python.gif)) | first model call, with token usage | `python 01-hello-model/python/solution/01_hello.py` |
| [01_hello_csharp](01_hello_csharp.mp4) ([GIF](01_hello_csharp.gif)) | the same call in C# | `dotnet run --file 01-hello-model/csharp/solution/01_hello.cs` |
| [01_hello_typescript](01_hello_typescript.mp4) ([GIF](01_hello_typescript.gif)) | the same call in TypeScript | `node 01-hello-model/typescript/solution/01_hello.mjs` |
| [01_knobs_deepseek](01_knobs_deepseek.mp4) | temperature, top_p and seed on a non-reasoning model | `GENAI_MODEL=DeepSeek-V4.1-Flash-1017 GENAI_REASONING_EFFORT= python 01-hello-model/python/solution/02_knobs.py` |
| [01_tool_loop](01_tool_loop.mp4) | the model calls two tools, then answers | `python 01-hello-model/python/solution/04_tool_loop.py` |
| [01_other_model](01_other_model.mp4) | same code, two vendors, only the model name changes | `python 01-hello-model/python/solution/05_same_code_other_model.py` |
| [02_ingest_embed](02_ingest_embed.mp4) | PDFs to chunks to vectors | `python 02-rag-mcp/python/solution/01_ingest.py`, then `02_embed.py` |
| [02_ask](02_ask.mp4) | grounded answers with sources, and a refusal | `python 02-rag-mcp/python/solution/03_ask.py` |
| [02_mcp_client](02_mcp_client.mp4) | an MCP client lists and calls the search server | `python 02-rag-mcp/python/solution/05_mcp_client.py` |
| [03_agent](03_agent.mp4) | an agent with a tool and session memory | `python 03-agents/python/solution/01_agent.py` |
| [03_agent_mcp](03_agent_mcp.mp4) | the agent uses the Lab 2 MCP server and cites it | `python 03-agents/python/solution/02_agent_with_mcp.py` |
| [03_workflow](03_workflow.mp4) | researcher, then writer workflow | `python 03-agents/python/solution/03_workflow.py` |
| [03_workflow_csharp](03_workflow_csharp.mp4) | the same workflow in C# | `dotnet run --file 03-agents/csharp/solution/03_workflow.cs` |
| [03_critic](03_critic.mp4) | writer and critic loop until the critic approves | `python 03-agents/python/solution/04_critic.py` |
| [04_cloud_image](04_cloud_image.mp4) | one image from the cloud model, saved to `out/` | `cd 04-local-media/python`, then `python solution/04_cloud_image.py` |
| [04_tts](04_tts.mp4) | text to speech, saved as `out/welcome.wav` | `cd 04-local-media/python`, then `python solution/05_tts.py` |
| [04_chain](04_chain.mp4) | text, then image, then speech, collected in `out/chain.html` | `cd 04-local-media/python`, then `python solution/06_chain.py` |

`cast/` holds the raw asciicast files (play them with `asciinema play cast/<name>.cast`).

## Re-recording

The scripts are in `tools/`. Run them inside the codespace (or the dev container), from `labs/`, with
`GENAI_API_KEY`, `GENAI_MODEL=gpt-5-nano` and `GENAI_MODEL_2=DeepSeek-V4.1-Flash-1017` set. You also need
`ffmpeg`, `fonts-dejavu-core` and [agg](https://github.com/asciinema/agg/releases) 1.5.0.

```bash
REC_SECRET="$GENAI_API_KEY" bash ../docs/recordings/tools/clips.sh /tmp/rec/cast   # add clip names to record only those
AGG=/path/to/agg bash ../docs/recordings/tools/render.sh /tmp/rec/cast /tmp/rec/out  # GIF + MP4 per clip
bash ../docs/recordings/tools/overview.sh /tmp/rec/out /tmp/rec/out/overview.mp4 1.2
```

`record.py` replaces the value of `REC_SECRET` with `***` in everything it records, and it refuses to write a
file if the value (or its last 8 characters) is still there.
