#!/usr/bin/env bash
# Record every workshop clip. Run from labs/ inside the codespace / dev container:
#   REC_SECRET="$GENAI_API_KEY" bash ../docs/recordings/tools/clips.sh /tmp/rec/cast [clip-name ...]
# Needs GENAI_API_KEY, GENAI_MODEL=gpt-5-nano, GENAI_MODEL_2=DeepSeek-V4.1-Flash-1017 in the environment.
set -u
OUT=${1:-/tmp/rec/cast}; shift || true
REC="python3 $(dirname "$0")/record.py"
mkdir -p "$OUT"
ONLY="$*"
clip() { local name=$1 title=$2; shift 2; if [ -z "$ONLY" ] || [[ " $ONLY " == *" $name "* ]]; then
  $REC "$OUT/$name.cast" "$title" "$@"; sleep ${PAUSE:-5}; fi; }

clip 00_check_env "Lab 0 · Check your setup" \
  "# Is everything ready? (key, endpoint, models)" "python 00-setup/check_env.py"
clip 01_hello_python "Lab 1 · First call (Python)" \
  "# Lab 1: your first model call, in Python" "python 01-hello-model/python/solution/01_hello.py"
clip 01_hello_csharp "Lab 1 · First call (C#)" \
  "# Lab 1: the same call in C#" "dotnet run --file 01-hello-model/csharp/solution/01_hello.cs"
clip 01_hello_typescript "Lab 1 · First call (TypeScript)" \
  "# Lab 1: the same call in TypeScript" "node 01-hello-model/typescript/solution/01_hello.mjs"
clip 01_knobs_deepseek "Lab 1 · Knobs on DeepSeek" \
  "# Temperature on a non-reasoning model (DeepSeek); no reasoning_effort" \
  "GENAI_MODEL=DeepSeek-V4.1-Flash-1017 GENAI_REASONING_EFFORT= python 01-hello-model/python/solution/02_knobs.py"
clip 01_tool_loop "Lab 1 · Tool loop" \
  "# The model asks for a tool, we run it, it answers" "python 01-hello-model/python/solution/04_tool_loop.py"
clip 01_tool_loop_csharp "Lab 1 · Tool loop (C#)"   "# The same tool loop in C#" "dotnet run --file 01-hello-model/csharp/solution/04_tool_loop.cs"
clip 01_tool_loop_typescript "Lab 1 · Tool loop (TypeScript)"   "# The same tool loop in TypeScript" "node 01-hello-model/typescript/solution/04_tool_loop.mjs"
clip 01_other_model "Lab 1 · Same code, other model" \
  "# Same code, two vendors: only the model name changes" "python 01-hello-model/python/solution/05_same_code_other_model.py"
clip 02_ingest_embed "Lab 2 · Ingest and embed" \
  "# Lab 2: PDFs -> chunks -> vectors" "python 02-rag-mcp/python/solution/01_ingest.py" "python 02-rag-mcp/python/solution/02_embed.py"
clip 02_ask "Lab 2 · Grounded answers" \
  "# Ask questions; answers cite the manual, or refuse" "python 02-rag-mcp/python/solution/03_ask.py"
clip 02_mcp_client "Lab 2 · MCP client" \
  "# Our search as an MCP server; a client lists and calls its tools" "python 02-rag-mcp/python/solution/05_mcp_client.py"
clip 02_mcp_client_csharp "Lab 2 · MCP client (C#)"   "# The C# client starts the C# MCP server (needs build/index.json from 02_embed)" "dotnet run --file 02-rag-mcp/csharp/solution/05_mcp_client.cs"
clip 02_mcp_client_typescript "Lab 2 · MCP client (TypeScript)"   "# The TypeScript client starts the TypeScript MCP server" "node 02-rag-mcp/typescript/solution/05_mcp_client.mjs"
clip 03_agent "Lab 3 · First agent" \
  "# Lab 3: an agent with a tool and session memory" "python 03-agents/python/solution/01_agent.py"
clip 03_agent_csharp "Lab 3 · First agent (C#)"   "# The same agent in C#" "dotnet run --file 03-agents/csharp/solution/01_agent.cs"
clip 03_agent_typescript "Lab 3 · First agent (TypeScript)"   "# The same agent in TypeScript" "node 03-agents/typescript/solution/01_agent.mjs"
clip 03_agent_mcp "Lab 3 · Agent + MCP" \
  "# The agent uses the Lab 2 MCP server as its tool" "python 03-agents/python/solution/02_agent_with_mcp.py"
clip 03_workflow "Lab 3 · Workflow" \
  "# Researcher -> writer workflow" "python 03-agents/python/solution/03_workflow.py"
clip 03_workflow_csharp "Lab 3 · Workflow (C#)" \
  "# The same workflow in C#" "dotnet run --file 03-agents/csharp/solution/03_workflow.cs"
clip 03_critic "Lab 3 · Writer and critic" \
  "# A writer drafts, a critic reviews, until APPROVED" "python 03-agents/python/solution/04_critic.py"
clip 03_team "Lab 3 · Team of four vendors"   "# Stretch: a team of agents on four vendors' models" "cd 03-agents/python" "python solution/08_team.py"
clip 04_cloud_image "Lab 4 · Cloud image" \
  "# Lab 4 runs from its python folder" "cd 04-local-media/python" "python solution/04_cloud_image.py"
clip 04_tts "Lab 4 · Text to speech" \
  "cd 04-local-media/python" "python solution/05_tts.py" "ls -lh out/*.wav"
clip 04_chain "Lab 4 · Chain: text, image, speech" \
  "cd 04-local-media/python" "python solution/06_chain.py" "ls out"
