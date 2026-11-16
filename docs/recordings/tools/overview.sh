#!/usr/bin/env bash
# Stitch the clip MP4s into one overview video with a title card before each clip.
# usage: overview.sh MP4_DIR OUT.mp4 [SPEED] [HOLD]
#   SPEED > 1 plays clips faster (default 1); HOLD = seconds the last frame of each clip stays on screen (default 6),
#   so viewers can read the result (or hit pause) before the next title card (3 s).
set -eu
DIR=$1; OUT=$2; SPEED=${3:-1}; HOLD=${4:-6}
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
W=1468; H=1040; TMP=$(mktemp -d)
CLIPS=(
  "00_check_env|Lab 0 · Check your setup"
  "01_hello_python|Lab 1 · First call (Python)"
  "01_hello_csharp|Lab 1 · First call (C#)"
  "01_hello_typescript|Lab 1 · First call (TypeScript)"
  "01_knobs_deepseek|Lab 1 · Knobs on DeepSeek"
  "01_tool_loop|Lab 1 · Tool loop"
  "01_other_model|Lab 1 · Same code, other model"
  "02_ingest_embed|Lab 2 · Ingest and embed"
  "02_ask|Lab 2 · Grounded answers"
  "02_mcp_client|Lab 2 · MCP client"
  "03_agent|Lab 3 · First agent"
  "03_agent_mcp|Lab 3 · Agent + MCP"
  "03_workflow|Lab 3 · Workflow"
  "03_workflow_csharp|Lab 3 · Workflow (C#)"
  "03_critic|Lab 3 · Writer and critic"
  "04_cloud_image|Lab 4 · Cloud image"
  "04_tts|Lab 4 · Text to speech"
  "04_chain|Lab 4 · Chain: text, image, speech"
)
i=0; : > "$TMP/list.txt"
card() { # $1 = text, $2 = output, $3 = seconds, $4 = font size
  printf '%s' "$1" > "$TMP/t.txt"
  ffmpeg -loglevel error -y -f lavfi -i "color=c=0x272822:s=${W}x${H}:d=$3:r=12" \
    -vf "drawtext=fontfile=$FONT:textfile=$TMP/t.txt:fontsize=$4:fontcolor=white:x=(w-tw)/2:y=(h-th)/2,format=yuv420p" \
    -c:v libx264 -preset slow -crf 28 "$2"
}
card "Building Stuff with GenAI · the labs, step by step" "$TMP/c_intro.mp4" 4 46
echo "file '$TMP/c_intro.mp4'" >> "$TMP/list.txt"
for e in "${CLIPS[@]}"; do
  n=${e%%|*}; t=${e#*|}; [ -f "$DIR/$n.mp4" ] || { echo "skip $n"; continue; }
  i=$((i+1)); card "$t" "$TMP/c$i.mp4" 3 72
  ffmpeg -loglevel error -y -i "$DIR/$n.mp4" -vf "setpts=PTS/$SPEED,fps=12,tpad=stop_mode=clone:stop_duration=$HOLD,format=yuv420p" \
    -c:v libx264 -preset slow -crf 28 "$TMP/v$i.mp4"
  printf "file '%s'\nfile '%s'\n" "$TMP/c$i.mp4" "$TMP/v$i.mp4" >> "$TMP/list.txt"
done
ffmpeg -loglevel error -y -f concat -safe 0 -i "$TMP/list.txt" -c copy -movflags +faststart "$OUT"
rm -rf "$TMP"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
