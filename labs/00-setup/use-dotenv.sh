# Drop the lab settings from THIS shell's environment, so labs/.env wins again.
# Usage (must be sourced, not run):   source 00-setup/use-dotenv.sh
# Only affects the current terminal. In a codespace, GENAI_API_KEY is a secret and returns in new terminals:
# remove it at https://github.com/settings/codespaces to make that permanent.
for __v in $(env | grep -oE '^(GENAI_|OLLAMA_|LMSTUDIO_|FOUNDRY_LOCAL_|COMFYUI_|TTS_)[A-Za-z0-9_]*'); do
  unset "$__v" && echo "  unset $__v"
done
unset __v
echo "  Now labs/.env is used. Check with:  python 00-setup/settings.py"
