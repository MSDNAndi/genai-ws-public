# Building Stuff with GenAI - samples and labs

Runnable samples for the workshop *"Building Stuff with GenAI - The Open Minded
Workshop beyond OpenAI"*. Python and C# twins of every sample, TypeScript where
a good stack exists, and **one configuration switch between the course endpoint,
OpenAI, OpenRouter, a local Ollama and Foundry Local**.


## The runner - one menu for every demo

You never have to remember a path. This lists every sample, shows what it does,
runs it and frames the output:

```bash
uv run tools/workshop.py                 # interactive menu (number = run it)
uv run tools/workshop.py --list          # what exists
uv run tools/workshop.py --run 1.03      # run one demo by number
uv run tools/workshop.py --segment 3     # run a whole segment
uv run tools/workshop.py --run 3.01 --lang csharp --profile mock
```

The menu reads the samples themselves - title and intro come from each file's
first markdown cell, so a new sample appears without touching the runner.
`p` switches the provider profile mid-session, which is the "same code, different
vendor" moment of the workshop.

## Run something in 60 seconds

No key needed - a local stub endpoint ships with the repo:

```bash
uv run tools/mock_server.py
```

Then, in a second terminal:

```bash
uv run samples/01-foundations/python/01_hello_model.py --profile mock
dotnet run samples/01-foundations/csharp/01_hello_model.cs -- --profile mock
```

With a real endpoint, copy `.env.example` to `.env`, paste the key you were
handed, and drop the `--profile` flag.

## Prerequisites

| Track | Needs |
|---|---|
| Python | [uv](https://docs.astral.sh/uv/) - it fetches its own Python 3.12+ (older system Pythons are ignored) |
| C# | [.NET SDK 10](https://dotnet.microsoft.com/download) |
| TypeScript | Node 20+ |

Nothing is installed globally. Every Python sample declares its own dependencies
inline ([PEP 723](https://peps.python.org/pep-0723/)) and `uv run` resolves them
into a throwaway environment; every C# sample is a .NET 10 file-based app that
builds to a temp folder.

Check a machine, then check that everything still runs:

```bash
uv run tools/check_env.py
uv run tools/smoke_test.py
```

## Configuration: one file, many providers

[`providers.json`](providers.json) defines profiles; `.env` (git-ignored) holds
the secrets. Pick one per run:

```bash
uv run samples/01-foundations/python/07_five_providers.py       # try them all
... --profile foundry        # the course endpoint (APIM in front of Foundry)
... --profile ollama         # whatever is on your laptop
... --profile mock           # the offline stub
```

Precedence: `--profile` > `GENAI_PROFILE` > the `default` in `providers.json`.
Real environment variables always beat `.env`, so a workshop key can be exported
for one shell without touching any file.

Profiles that are not configured are **skipped with a reason**, never crash - so
a comparison sample still works when you only have one key.

## Layout

```
providers.json              provider profiles (the only place endpoints live)
.env.example                copy to .env; never committed
samples/
  01-foundations/           chat, sampling, structured output, tools, embeddings,
    python/ csharp/ typescript/    Responses API, five providers, inspection
  02-integrating/           RAG, MCP servers, skills            (scaffolded)
  03-agents/                MAF, LangChain/LangGraph, A2A, Foundry hosted agents
  04-local-media/           local runners, image, speech        (scaffolded)
shared/
  python/  src/genaiclass/       provider resolution + object inspection helpers
  csharp/  GenAIClass/           the same, for .NET
  typescript/               the same, for Node                  (scaffolded)
tools/
  mock_server.py            offline OpenAI-compatible endpoint
  to_notebook.py            scripts -> .ipynb / .dib
  check_env.py              does this machine have what the labs need
  smoke_test.py             run every sample against the mock, PASS/FAIL
notebooks/                  generated - do not edit by hand
```

## Notebooks

Polyglot Notebooks and .NET Interactive were archived in April 2026. The samples
are therefore plain scripts, marked up with the standard `# %%` / `// %%`
percent-cell markers - so they are *also* notebooks whenever you want one:

```bash
dotnet build shared/csharp/GenAIClass/GenAIClass.csproj   # C# notebooks need the assembly
uv run tools/to_notebook.py                     # -> notebooks/
```

Open the result in [Verso](https://github.com/DataficationSDK/Verso) (maintained
polyglot successor), JupyterLab, or anything that reads `.ipynb`. The scripts
stay the source of truth; regenerate rather than editing notebooks by hand.

## Looking inside the response

Expanding a response object was half of the original workshop. Scripts keep it:

```python
from genaiclass import dump, inspect, raw_json

dump(completion)          # indented tree in the terminal
inspect(completion)       # collapsible HTML page, opens in a browser
print(raw_json(raw))      # the untouched HTTP body + rate-limit headers
```

Worked example: `samples/01-foundations/python/08_inspecting_responses.py`. For
unplanned poking, use the debugger (`.vscode/launch.json` is set up) or a
generated notebook.

## Conventions

* Samples are numbered and **the Python and C# files of the same number are
  twins** - same sections, same order, so a mixed room follows one screen.
* Every sample runs standalone. No sample depends on another having run.
* Comments explain *why*, and flag the thing that will bite in production.
* Versions are pinned. This landscape moves monthly; re-verify before teaching.
