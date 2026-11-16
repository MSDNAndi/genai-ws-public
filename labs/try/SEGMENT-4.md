# Segment 4 · try it yourself

The Segment 4 demos run on the instructor laptop (GPU, Ollama, ComfyUI, a microphone). Your codespace has none of
these, so each demo below is either the **honest cloud equivalent** through the workshop gateway, or **Watch only**.
Run every command from `labs/` (`cd labs` in the terminal). Output files land in `labs/out/`: click a `.wav` or `.png`
in the Explorer to play or view it.

## S4 · a Qwen3.8-27B tool call on Ollama (slide 169)

Try it:
```bash
GENAI_MODEL=gpt-oss-120b python 01-hello-model/python/solution/04_tool_loop.py
```
What to notice: the Lab 1 tool loop is unchanged. Only the model changed, and gpt-oss-120b is open weights: you could
host this same model yourself. On your laptop it is the same command with `GENAI_BASE_URL=http://localhost:11434/v1`
and an Ollama model tag. The checkpoint is 19 °C → 66.2 °F after two tool calls.

## S4 · one model, two servers, eight clients (slide 170)

Try it:
```bash
python try/s4_eight_clients.py gpt-oss-120b
```
What to notice: first one client, then eight at the same moment. Each request's tok/s stays about the same, but the
total for all eight is several times higher, because the server batches them. The gateway hides its hardware. Point
`GENAI_BASE_URL` at llama.cpp and then at vLLM and the same script shows the batching gap.

## S4 · Foundry Local on the Windows NPU (slide 171)

Watch only. Foundry Local needs a Windows, macOS or Linux machine with the runtime installed (a codespace has no NPU and no GPU).
What to notice: it picks GPU, NPU or CPU by itself and still speaks the OpenAI API. At home, set
`FOUNDRY_LOCAL_BASE_URL` in `labs/.env` and run `04-local-media/python/solution/01_local_models.py`.

## S4 · a coding agent on a model you host (slide 179)

Watch only. This needs a local model server (Ollama / LM Studio) and a 27B-class model.
What to notice: it is the same agent harness, with only the endpoint changed. Watch where it struggles (long context, many tools).
The closest thing you can run here is the S4 tool loop above (slide 169): it is the same loop with a different model.

## S4 · Gemma 4 E4B hears you (slide 180)

Try it (cloud, not local):
```bash
python try/s4_hear.py "Which planet has the most moons?"
```
What to notice: a TTS voice speaks your question to `out/question.wav`, a transcription model hears it, and the chat
model answers what it heard. That takes three cloud models. Gemma 4 E4B does the hearing and the answering in one
local model, offline.

## S4 · Z-Image-Turbo in ComfyUI: seed and CFG live (slide 186)

Watch only for the real images (they need ComfyUI on a GPU). The method runs here with the ComfyUI stand-in:
```bash
python _tools/comfy_mock.py 8188 >/dev/null 2>&1 & M=$!; sleep 2; python 04-local-media/python/solution/03_one_knob.py 04-local-media/comfyui_workflows/01_txt2img_sdxl.json --knob seed --values 42 42 7; python 04-local-media/python/solution/03_one_knob.py 04-local-media/comfyui_workflows/01_txt2img_sdxl.json --knob cfg --values 2 7 15 --seed 42; kill $M
```
What to notice: the stand-in draws flat tiles that show the knobs it received, not real images. In
`out/one_knob/contact_seed.png` the same seed gives the same tile twice. In `contact_cfg.png` only CFG changes. Changing one knob at a time is the
craft principle, whatever the renderer.

## S4 · pose swap with ControlNet (slide 191)

Watch only. This needs SDXL, ControlNet and DWPose on a GPU in ComfyUI. The graph is
`04-local-media/comfyui_workflows/02_pose_lora_sdxl.json` if you want to read it.
What to notice: the skeleton says where, the prompt says who. At ControlNet strength 0.6 the prompt gets more say.

## S4 · Qwen3-TTS voice clone + Parakeet live captions (slide 201)

Try it (cloud voices, no cloning, no microphone):
```bash
python 04-local-media/python/solution/06_chain.py --topic "a radio host welcoming listeners" --image skip --voice coral --tone "a calm late-night radio host, slightly amused" --check
```
What to notice: `--tone` works like VoiceDesign. You describe a voice in words and hear it. `--check` is the caption
step: a transcription model writes down what it heard and counts the matching words. Voice cloning stays on stage, and
only with the speaker's own consent.

## S4 · the music-video chain, stage by stage + Wan2GP (slide 215)

Try it (text → image → voice → ears; no video and no Wan2GP, which need a GPU):
```bash
python 04-local-media/python/solution/06_chain.py --topic "a singer on stage at a tech conference" --writer Llama-4-Maverick-17B-128E-Instruct-FP8 --check
```
What to notice: each stage writes a file that the next stage reads (`out/chain_*.png`, `.wav`, `.json`). Swap one block
(`--writer`, `--voice`, `--tone`, `--image skip`) and the chain still works. Compare your runs in `out/chain.html`. You get
3 images per minute per key.

## S4 · Closer: an ACE-Step song about today (slide 223)

Try it (spoken, not sung):
```bash
python try/s4_song.py --tone "a slow, gravelly blues singer"
```
What to notice: block 1 is Lab 1 code. The agenda becomes tagged lyrics in `out/lyrics.txt`. Then gpt-4o-mini-tts
performs them as `out/song.wav`, with the recipe in `out/song.json`. On stage, ACE-Step 1.5 sings the same lyrics on one GPU.
