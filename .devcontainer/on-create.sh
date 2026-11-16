#!/usr/bin/env bash
# Runs once when the codespace is created (and in a prebuild, if the repo owner enables one).
# Installs every lab dependency, so the first `python`, `dotnet run` or `node` call is instant.
set -uo pipefail
cd "$(dirname "$0")/../labs"

echo "== Python: labs/.venv + requirements.txt"
python -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt

echo "== Node: npm install in labs/"
npm install --no-fund --no-audit --loglevel=error

echo "== .NET: restore the NuGet packages the C# labs use (first run is then fast)"
for f in 00-setup/check_env.cs 01-hello-model/csharp/solution/03_structured.cs \
         02-rag-mcp/csharp/solution/04_mcp_server.cs 02-rag-mcp/csharp/solution/05_mcp_client.cs \
         03-agents/csharp/solution/03_workflow.cs 03-agents/csharp/solution/05_tracing.cs; do
  [ -f "$f" ] && dotnet build "$f" -v q -nologo >/dev/null 2>&1 && echo "   restored $f" || echo "   (skipped $f)"
done

echo "== PATH: labs/.venv first in every shell (login shells reset PATH via /etc/profile, so remoteEnv alone is not enough)"
VENV_LINE="export PATH=\"$PWD/.venv/bin:\$PATH\"  # genai-workshop"
for rc in ~/.profile ~/.bashrc ~/.zshrc; do
  [ -f "$rc" ] || touch "$rc"
  grep -q 'genai-workshop' "$rc" || echo "$VENV_LINE" >> "$rc"
done

echo "== labs/.env: workshop settings (no key in it; the key comes from the codespace secret)"
[ -f .env ] || cp ../.devcontainer/workshop.env .env

echo "== done"
