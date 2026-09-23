# ComfyUI-Workflows (Begleitmaterial zum Vortrag)

Diese `*.json`-Dateien sind im **ComfyUI-API-/Prompt-Format** (Node-ID → `class_type` + `inputs`).
Sie entsprechen 1:1 den Diagrammen im Deck und dienen als **lauffähige Vorlagen**.

## Laden / Ausführen
- **Per API:** an `POST http://127.0.0.1:8188/prompt` mit `{"prompt": <inhalt der json>}` schicken.
- **In der UI:** ComfyUI-Menü → *Load* akzeptiert API-Format-JSON (bzw. per „Load (API)“ in neueren Builds).
- **Modelldateien anpassen:** die `ckpt_name` / `lora_name` / `control_net_name` sind Platzhalter —
  auf die tatsächlichen Dateinamen in deinem `models/`-Ordner umstellen.

## Übersicht
| Datei | Was | Benötigte Custom-Nodes |
|---|---|---|
| `01_txt2img_sdxl.json` | Anatomie eines txt2img-Graphen (Checkpoint → CLIP → KSampler → VAE) | – (Core) |
| `02_pose_lora_sdxl.json` | Pose-Matching (DWPose + OpenPose-ControlNet) + Character-LoRA | `comfyui_controlnet_aux` (DWPreprocessor) |
| `03_inpaint.json` | Inpainting über maskierten Latent (`VAEEncodeForInpaint`) | – (Core); Maske = Alpha des Eingangsbilds |
| `04_upscale_model.json` | GAN-Upscale mit `4x-UltraSharp` | – (Core); Upscale-Modell in `models/upscale_models/` |

## Modelle (Beispiele, frei ersetzbar)
- **Checkpoint:** `sd_xl_base_1.0.safetensors` (oder ein Flux-Checkpoint — dann DiT-taugliche Nodes nutzen).
- **ControlNet (OpenPose, SDXL):** z. B. `controlnet-openpose-sdxl-1.0.safetensors`.
- **DWPose-Modelle:** `yolox_l.onnx` + `dw-ll_ucoco_384.onnx` (lädt `comfyui_controlnet_aux` i. d. R. automatisch).
- **Upscaler:** `4x-UltraSharp.pth`.

## Hinweis
Video-/Audio-/Lipsync-Stufen (Wan 2.2 I2V, Wan 2.2 S2V, InfiniteTalk, ACE-Step) laufen über
eigene Custom-Node-Packs; die offiziellen ComfyUI-Beispiel-Workflows dazu sind unter
`docs.comfy.org/tutorials/video/wan` bzw. `blog.comfy.org` verlinkt und werden je nach
installierter Version geladen. Die hier enthaltenen Bild-Workflows sind der stabile Kern.
