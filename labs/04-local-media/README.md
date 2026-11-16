# Lab 4 — Local & multimodal: the craft lab

**Verified on:** 2026-09-23 against the offline mock and `_tools/comfy_mock.py` with `01_txt2img_sdxl.json`; step 1
also against Ollama 0.34.3 (2026-09-22); step 6 on 2026-11-16 in the workshop dev container against the workshop endpoint
(all 7 chat models as writer, gpt-image-1-mini, gpt-4o-mini-tts) and the ComfyUI stand-in · not yet: a real ComfyUI on a GPU.

**Goal:** run your Lab 1 code on your own machine and measure it, then drive image generation from code the way a
craftsperson does — log the seed, change one knob at a time, keep the pipeline, swap the model. No GPU? Every step
has a cloud path through the same OpenAI-compatible client.

**In a codespace (no GPU, no Ollama):** do steps 4–5, then **step 6, mix and match** — your core exercise; all three use
the workshop endpoint. For steps 2–3 start the ComfyUI stand-in in a second terminal (`python _tools/comfy_mock.py 8188` from `labs/`). Step 1 needs a local
runtime on your own machine; watch it in the instructor demo. Images are limited to 3 per minute per key.

Python only (the media tooling of 2026 is Python-first); the local-model step works in any language because it is
just Lab 1 with a different `base_url`.

| Step | File | Needs |
|---|---|---|
| 1 same code, your machine — speed + tool calling | `01_local_models.py` | Ollama (LM Studio / Foundry Local optional) |
| 2 run a ComfyUI workflow from code, log the seed | `02_comfy_run.py` | ComfyUI + a GPU |
| 3 change ONE knob → contact sheet | `03_one_knob.py` · TODO 1 | ComfyUI + a GPU |
| 4 no GPU: image from the cloud | `04_cloud_image.py` | workshop endpoint |
| 5 text to speech | `05_tts.py` · TODO 1 | workshop endpoint or a local TTS server |
| 6 **mix and match**: swap one block, compare | `06_chain.py` · TODO 1 (with `--check`) | workshop endpoint (+ ComfyUI optional) |

Run from `04-local-media/python` (`python 01_local_models.py` …; finished versions in `solution/`).

## Steps
**1 · Your machine — `01_local_models.py`.** Lists the models of every local runtime in `.env`, streams an answer to
measure *time to first token* and *tokens per second*, and checks tool calling. Foundry Local chooses its port at
start-up: `foundry service status`, then set `FOUNDRY_LOCAL_BASE_URL=http://127.0.0.1:<port>/v1`.
*What to notice:* the first call includes loading the model; "thinking" models are 5–10× slower on a CPU
(`OLLAMA_REASONING_EFFORT=none` switches thinking off); memory, not compute, decides which model fits.

**2 · ComfyUI from code — `02_comfy_run.py`.** The workflows in `../comfyui_workflows/` (from the *Beyond the Slop*
talk) are already saved in ComfyUI's *API format* — the format code can run; for your own graphs use *Workflow → Export
(API)*. Start with the txt2img graph (it expects `sd_xl_base_1.0.safetensors` in `models/checkpoints/` — or edit
`ckpt_name` to a checkpoint you have):
`python 02_comfy_run.py ../comfyui_workflows/01_txt2img_sdxl.json --prompt "a lighthouse in fog, 35 mm photo" --seed 42`.
Every image gets a `.json` next to it with the exact settings. *Craft principle #1: log the seed.*

**3 · One knob — `03_one_knob.py` · TODO 1.** `--knob cfg --values 1.5 3 5 8 --seed 42` renders the same seed (the
random starting noise) with four CFG values (how strictly the image follows the prompt); you build the contact sheet. Then try `--knob steps` and `--knob seed`.
*Craft principle #2: change one thing at a time.*
More graphs from the talk for later: `02_pose_lora_sdxl.json` (pose ControlNet + a character LoRA; needs the
comfyui_controlnet_aux nodes), `03_inpaint.json`, `04_upscale_model.json` (4x-UltraSharp) and `05_image_to_3d.json`
(a template for TRELLIS/Hunyuan3D custom nodes). They read an input picture (`pose_ref.png`, `scene_with_mask.png`,
`keyframe.png`, `subject.png`) from ComfyUI's `input/` folder — open them in the ComfyUI UI first; details in
`../comfyui_workflows/README_EN.md`.

**4 · No GPU — `04_cloud_image.py`.** The same idea with `GENAI_IMAGE_MODEL` (e.g. `gpt-image-1-mini`) on the workshop
endpoint. Notice what you *cannot* control here (no seed) — that is the slot machine vs. the instrument.

**5 · Speech — `05_tts.py` · TODO 1.** `/audio/speech` through the same client: cloud `GENAI_TTS_MODEL`, or any
local OpenAI-compatible TTS server via `TTS_BASE_URL`, `TTS_MODEL`, `TTS_VOICE` (model and voice names depend on the
server — check its docs).

## 6 · Mix and match — the magic sauce is the pipeline: `06_chain.py`
Four blocks, each one a switch: a **writer** (any chat model) turns your topic into an image prompt and a one-line
narration (structured output, Lab 1) → an **image** model paints it → a **voice** speaks it → optionally **ears**
(`--check`, a transcription model) listen back. Every run is kept, and `out/chain.html` shows all your runs side by side
with their recipe and timings.

| Block | Switch (or env var in `labs/.env`) | Try |
|---|---|---|
| writer | `--writer` (`CHAIN_WRITER`, default `GENAI_MODEL`) · `--style "film noir"` | `gpt-5-mini`, `gpt-4o-mini`, `gpt-oss-120b`, `DeepSeek-V4.1-Flash-1017`, `grok-4-1-fast-non-reasoning`, `Llama-4-Maverick-17B-128E-Instruct-FP8` |
| image | `--image` (`GENAI_IMAGE_MODEL`) · `--image skip` · `--workflow <comfy.json>` | `gpt-image-1-mini`, or ComfyUI / the stand-in |
| voice | `--voice` (`TTS_VOICE`) · `--tone "..."` | `alloy`, `coral`, `onyx`, `nova`, `sage`, `verse` … |
| ears | `--check` (`GENAI_TRANSCRIBE_MODEL`) — **TODO 1** in the starter | `gpt-4o-mini-transcribe` |

**Exercise — swap ONE block, compare.** Run the baseline, then change exactly one switch per run (craft principle #2
again) and compare the cards in `out/chain.html`:
```bash
python 06_chain.py --topic "a lighthouse keeper's last night"                          # 0 · baseline
python 06_chain.py --topic "a lighthouse keeper's last night" --writer grok-4-1-fast-non-reasoning   # A · other vendor writes
python 06_chain.py --topic "a lighthouse keeper's last night" --voice coral --tone "a hushed nature-documentary narrator"   # B · other voice
python 06_chain.py --topic "a lighthouse keeper's last night" --style "1950s sci-fi pulp cover"      # C · same model, other brief
```
*What to notice:* which block changed the result most? Does another vendor write a different *kind* of prompt (length,
detail, mood)? Seconds per block are on every card — which block is the slow one? Then do **TODO 1** in the starter
(transcribe the WAV back) and add `--check`: a fourth modality, and an automatic test that the words survived the voice.
(No transcription model on your endpoint? The script says so and still writes the page.)

Comparing many writers? `--writer-only` stops after the text — no image or voice quota used. Images are limited to
**3 per minute per key**: wait between runs, or use `--image skip`. With ComfyUI (or the stand-in on port 8188) add
`--workflow ../comfyui_workflows/01_txt2img_sdxl.json` — a seed you control, no cloud quota.

**See the result in a codespace:** a codespace's browser cannot open `file://` paths, so serve the folder. In a
**second terminal**: `cd labs/04-local-media/python && python -m http.server 8000 -d out` → click **Open in Browser** on
the pop-up (or *Ports* tab → port 8000 → globe icon) and add **`/chain.html`** to the address. Leave it running and just
reload the page after each run. Quick look without a server: click the `.png` or `.wav` in `out/` in the Explorer — VS
Code shows images and plays audio itself. On your own machine simply open `out/chain.html`.

## Fallback
- **No GPU / no ComfyUI:** steps 4–6 run in the cloud. To see steps 2–3 work end to end anyway, start the
  stand-in `python ../../_tools/comfy_mock.py 8188` — it renders flat images that print the knobs they received.
- **No image or speech model on your endpoint:** use the instructor's pre-rendered contact sheets and audio
  (shown on screen), then continue with step 6 using `--workflow` and ComfyUI or the mock.
- **Ollama too slow (step 1):** use a smaller model (`qwen3.5:2b`, `llama3.2:3b`) and keep `OLLAMA_REASONING_EFFORT=none`.

## Troubleshooting
"UI-format workflow" → export it again with *Export (API)* · ComfyUI returns "value not in list" → the workflow
references a model file you don't have: open it in ComfyUI and pick one · no image returned → check the ComfyUI
console for the node error · the cloud image call returns 404 → your endpoint has no image model; ask the instructor ·
TTS returns 400 → the voice name is unknown to that server.

## Why it matters
Local models are a `base_url` away, and the media world rewards the same habits as code: reproducibility, small
controlled changes, and a pipeline you own. Models will change every month; the loop and the pipeline stay.
