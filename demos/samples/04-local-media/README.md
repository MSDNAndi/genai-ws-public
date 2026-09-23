# Segment 4 - Local AI, media, beyond the West (scaffold)

*Slot machine to instrument, on your own machine.* Nothing here is written yet.

The cheapest win in this segment is already done: **every sample in Segment 1
runs locally today** with `--profile ollama`, `--profile lmstudio` or
`--profile foundry-local`. Start the segment by re-running sample 01 against a
laptop model - no new code, which is the point.

## Planned samples

| # | Sample | Shows | Notes |
|---|---|---|---|
| 01 | `local_runners` | the same script against Ollama, LM Studio and Foundry Local, with tokens/sec | uses the existing profiles |
| 02 | `local_tool_calling` | whether a small local model can actually drive the Segment-1 tool loop (sometimes it cannot - that is the lesson) | |
| 03 | `image_generation` | one image, then the four knobs: seed, steps, CFG, denoise | cloud path: Foundry `gpt-image-*` / FLUX; local path: ComfyUI API |
| 04 | `comfyui_api` | drive the workshop ComfyUI workflows from code | workflows already exist in the course folder under `labs/04-local-media/comfyui_workflows/` |
| 05 | `control_and_loras` | LoRA, ControlNet/pose, IP-Adapter, inpainting - "prompt = what, ControlNet = where" | |
| 06 | `speech` | TTS and transcription both ways | Qwen3-TTS / Parakeet local; `gpt-4o-mini-tts` as the cloud twin |
| 07 | `pipeline` | chaining text -> image -> speech -> video, with the cloud twin of the same chain | pre-rendered fallback required |

## Notes before building

* **Every sample needs a no-GPU path.** Cloud twin via the course endpoint, or a
  pre-rendered output committed next to it.
* Media model facts drift monthly (licences especially - Hunyuan3D excludes the
  EU/UK; several "open" models exclude hyperscalers). Re-verify the week before.
* This segment is demo-heavy by design; the lab is a craft lab - change one knob
  at a time and log the seed.
* Source material for the narrative lives in the course folder:
  `research/2026-09-19_local-ai-media-beyond-west.md` and the Beyond-the-Slop
  assets.
