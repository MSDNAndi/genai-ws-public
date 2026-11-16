# Building Stuff with GenAI - workshop material

## Fastest start: in your browser, nothing to install

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/msdnAndi/genai-ws-public?quickstart=1)

Click the button, paste the key from your card into the **GENAI_API_KEY** box, click **Create codespace**. Step by step with screenshots: [docs/WALKTHROUGH.md](docs/WALKTHROUGH.md).
Prefer your own machine? Follow `labs/00-setup/SETUP.md` below.
How the workshop endpoint is built (gateway, limits, identity) and how the same labs run on a local model: [docs/HOW-ITS-DEPLOYED.md](docs/HOW-ITS-DEPLOYED.md).


Two folders:

| Folder | What it is | Start here |
|---|---|---|
| `labs/` | the hands-on labs you do on the day (Python, C#, TypeScript): starters with `TODO`s, `solution/` next to them | `labs/00-setup/SETUP.md` - do it **before** the day |
| `demos/` | the instructor's demos, runnable by you: one menu for all of them | `demos/README.md` |

Settings live in a `.env` file you create from `.env.example` in each folder. Never commit it.
On the day you get a card with the endpoint URL and your personal key.
