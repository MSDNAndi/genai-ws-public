"""Which settings do the labs actually use - and where does each one come from?

    python 00-setup/settings.py

Rule in every lab (Python, C#, TypeScript): a REAL ENVIRONMENT VARIABLE WINS over the same line in labs/.env.
So if GENAI_API_KEY / GENAI_BASE_URL / GENAI_MODEL ... are set in your environment (a Codespaces secret, your shell
profile, Windows "Environment Variables"), editing labs/.env changes nothing. This script shows the winner per setting
and prints how to drop the environment variables so labs/.env takes over again (see 00-setup/use-dotenv.*).
"""
import os
from pathlib import Path

LABS = Path(__file__).resolve().parents[1]
ENV_FILE = LABS / ".env"
SECRET = ("_KEY", "TOKEN", "SECRET", "PASSWORD")


def read_dotenv(path: Path) -> dict[str, str]:
    values = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                values[k.strip().removeprefix("export ").strip()] = v.split(" #")[0].strip().strip('"').strip("'")
    return values


def show(name: str, value: str | None) -> str:
    if not value:
        return "-"
    if name.endswith(SECRET) or "API_KEY" in name:
        return f"...{value[-4:]}" if len(value) > 8 else "(set)"
    return value if len(value) <= 60 else value[:57] + "..."


dotenv = read_dotenv(ENV_FILE)
names = sorted({n for n in [*dotenv, *os.environ] if n.startswith(("GENAI_", "OLLAMA_", "LMSTUDIO_", "FOUNDRY_LOCAL_",
                                                                     "COMFYUI_", "TTS_"))})
print(f"labs/.env: {'found' if ENV_FILE.is_file() else 'NOT found'} ({ENV_FILE})\n")
print(f"{'setting':<26} {'used by the labs':<44} source")
overridden = []
for n in names:
    env, file = os.environ.get(n), dotenv.get(n)
    if env is not None:
        src = "ENVIRONMENT" + ("  (labs/.env line ignored!)" if file is not None and file != env else "")
        if file is not None and file != env:
            overridden.append(n)
        print(f"{n:<26} {show(n, env):<44} {src}")
    else:
        print(f"{n:<26} {show(n, file):<44} labs/.env")

env_only = [n for n in names if n in os.environ]
if not env_only:
    print("\nEverything comes from labs/.env - edit that file to change settings.")
else:
    print(f"\n{len(env_only)} setting(s) come from environment variables"
          + (f"; {len(overridden)} of them hide a different value in labs/.env: {', '.join(overridden)}" if overridden else "")
          + ".\nTo use labs/.env instead:")
    print("  bash / zsh / Codespaces terminal:  source 00-setup/use-dotenv.sh")
    print("  Windows PowerShell:                . .\\00-setup\\use-dotenv.ps1            (add -Persist to also remove them")
    print("                                                                            from your Windows user profile)")
    if os.getenv("CODESPACES") == "true" and "GENAI_API_KEY" in os.environ:
        print("  Codespaces: GENAI_API_KEY is a codespace secret and comes back in new terminals - remove it at\n"
              "  https://github.com/settings/codespaces (Secrets) and rebuild/restart the codespace to make it permanent.")
