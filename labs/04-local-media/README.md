# Lab 4 — Local & multimodal: the craft lab (core + stretch)

**Verified on:** 2026-09-23 against the offline mock and `_tools/comfy_mock.py` with `01_txt2img_sdxl.json`; step 1
also against Ollama 0.34.3 (2026-09-22) · not yet: a real ComfyUI on a GPU, the workshop image and speech models.

**Goal:** run your Lab 1 code on your own machine and measure it, then drive image generation from code the way a
craftsperson does — log the seed, change one knob at a time, keep the pipeline, swap the model. No GPU? Every step
has a cloud path through the same OpenAI-compatible client.

Python only (the media tooling of 2026 is Python-first); the local-model step works in any language because it is
just Lab 1 with a different `base_url`.

| Step | File | Needs |
|---|---|---|
| 1 same code, your machine — speed + tool calling | `01_local_models.py` | Ollama (LM Studio / Foundry Local optional) |
| 2 run a ComfyUI workflow from code, log the seed | `02_comfy_run.py` | ComfyUI + a GPU |
| 3 change ONE knob → contact sheet | `03_one_knob.py` · TODO 1 | ComfyUI + a GPU |
| 4 no GPU: image from the cloud | `04_cloud_image.py` | workshop endpoint |
| 5 text to speech | `05_tts.py` · TODO 1 | workshop endpoint or a local TTS server |
| stretch: the pipeline | `06_chain.py` | workshop endpoint (+ ComfyUI optional) |

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

**3 · One knob — `03_one_knob.py` · TODO 1.** `--knob cfg --values 1.5 3 5 8 --seed 42` renders the same seed with
four CFG values; you build the contact sheet. Then try `--knob steps` and `--knob seed`.
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

## Stretch — the magic sauce is the pipeline: `06_chain.py`
The chat model writes an image prompt and a one-line narration (structured output, Lab 1), the image comes from ComfyUI
(`--workflow ../comfyui_workflows/01_txt2img_sdxl.json`) or the cloud, the narration is spoken, and `out/chain.html` plays it. Swap any block — the
pipeline stays. That is the idea behind the music-video chain in the talk.

## Fallback
- **No GPU / no ComfyUI:** steps 4–5 and the stretch run in the cloud. To see steps 2–3 work end to end anyway, start the
  stand-in `python ../../_tools/comfy_mock.py 8188` — it renders flat images that print the knobs they received.
- **No image or speech model on your endpoint:** use the instructor's pre-rendered contact sheets and audio
  (shown on screen), then continue with the stretch using ComfyUI or the mock.
- **Ollama too slow (step 1):** use a smaller model (`qwen3.5:2b`, `llama3.2:3b`) and keep `OLLAMA_REASONING_EFFORT=none`.

## Troubleshooting
"UI-format workflow" → export it again with *Export (API)* · ComfyUI returns "value not in list" → the workflow
references a model file you don't have: open it in ComfyUI and pick one · no image returned → check the ComfyUI
console for the node error · the cloud image call returns 404 → your endpoint has no image model; ask the instructor ·
TTS returns 400 → the voice name is unknown to that server.

## Why it matters
Local models are a `base_url` away, and the media world rewards the same habits as code: reproducibility, small
controlled changes, and a pipeline you own. Models will change every month; the loop and the pipeline stay.
