# ComfyUI workflow handouts (from "Beyond the Slop", July 2026) — Lab 4 material
API/prompt-format JSON (node id → class_type + inputs), 1:1 with the talk's diagrams. Run: `POST http://127.0.0.1:8188/prompt` with `{"prompt": <json>}`
or load in the ComfyUI UI (Load / "Load (API)"). Replace the placeholder `ckpt_name` / `lora_name` / `control_net_name` with files in your `models/` folder.
| File | What | Custom nodes |
|---|---|---|
| 01_txt2img_sdxl.json | anatomy of a txt2img graph (checkpoint → CLIP → KSampler → VAE) | core |
| 02_pose_lora_sdxl.json | pose matching (DWPose + OpenPose ControlNet) + character LoRA | comfyui_controlnet_aux (DWPreprocessor) |
| 03_inpaint.json | inpainting over a masked latent (VAEEncodeForInpaint) | core; mask = alpha of the input image |
| 04_upscale_model.json | GAN upscale with 4x-UltraSharp | core; model in models/upscale_models/ |
| 05_image_to_3d.json | image → 3D (from the German v9 deck) | see the German README |
Lab plan: txt2img → log the seed → change ONE knob → add a controller (pose ControlNet or a Civitai LoRA) → inpaint one detail → upscale the winner.
Before the workshop: re-test on ComfyUI v0.36+ (V3 API schema) and pin model file names; SDXL is the safe base (8 GB), FLUX.2 klein 4B / Z-Image-Turbo for ≥ 13–16 GB.
German original: README.md.
