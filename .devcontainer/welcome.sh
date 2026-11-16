#!/usr/bin/env bash
# Runs every time VS Code attaches: a one-line health check, so attendees see green or exactly what to fix.
cd "$(dirname "$0")/../labs" || exit 0
echo
echo "  Building Stuff with GenAI — your lab environment"
echo "  Python, C# and TypeScript are installed. Start with labs/START-HERE.md"
# Open the instructions (Codespaces' openFiles is skipped when the trust prompt shows first)
command -v code >/dev/null 2>&1 && code START-HERE.md >/dev/null 2>&1
echo
if [ -z "${GENAI_API_KEY:-}" ] && ! grep -q '^GENAI_API_KEY=.\+' .env 2>/dev/null; then
  echo "  ⚠  No workshop key yet. Open labs/.env and add:  GENAI_API_KEY=<the key from your card>"
  echo "     then run:  python 00-setup/check_env.py"
  exit 0
fi
# MCP hosts (Inspector, Copilot's mcp.json) start the lab servers WITHOUT the codespace secret: give them the key via
# labs/.env too (git-ignored, stays inside this codespace). Only when .env has no key yet.
if [ -n "${GENAI_API_KEY:-}" ] && ! grep -q '^GENAI_API_KEY=.\+' .env 2>/dev/null; then
  printf '\n# copied from the codespace secret, so MCP hosts see it too\nGENAI_API_KEY=%s\n' "$GENAI_API_KEY" >> .env
fi
python 00-setup/check_env.py || true
