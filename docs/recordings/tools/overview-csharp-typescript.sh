#!/usr/bin/env bash
# Stitch the C# and TypeScript clip MP4s into a second overview video with a title card before each clip.
# usage: overview-csharp-typescript.sh MP4_DIR OUT.mp4 [SPEED] [HOLD]
#   SPEED > 1 plays clips faster (default 1); HOLD = seconds the last frame of each clip stays on screen (default 6),
#   so viewers can read the result (or hit pause) before the next title card (3 s).
set -eu
DIR=$1; OUT=$2; SPEED=${3:-1}; HOLD=${4:-6}
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
W=1468; H=1040; TMP=$(mktemp -d)
CLIPS=(
  "01_hello_csharp|Lab 1 · First call (C#)"
  "01_hello_typescript|Lab 1 · First call (TypeScript)"
  "01_tool_loop_csharp|Lab 1 · Tool loop (C#)"
  "01_tool_loop_typescript|Lab 1 · Tool loop (TypeScript)"
  "02_mcp_client_csharp|Lab 2 · MCP client (C#)"
  "02_mcp_client_typescript|Lab 2 · MCP client (TypeScript)"
  "03_agent_csharp|Lab 3 · First agent (C#)"
  "03_agent_typescript|Lab 3 · First agent (TypeScript)"
  "03_workflow_csharp|Lab 3 · Workflow (C#)"
  "03_team|Bonus · Team of four vendors (Python)"
)
i=0; : > "$TMP/list.txt"
card() { # $1 = text, $2 = output, $3 = seconds, $4 = font size
  printf '%s' "$1" > "$TMP/t.txt"
  ffmpeg -loglevel error -y -f lavfi -i "color=c=0x272822:s=${W}x${H}:d=$3:r=12" \
    -vf "drawtext=fontfile=$FONT:textfile=$TMP/t.txt:fontsize=$4:fontcolor=white:x=(w-tw)/2:y=(h-th)/2,format=yuv420p" \
    -c:v libx264 -preset slow -crf 28 "$2"
}
card "Building Stuff with GenAI · C# and TypeScript" "$TMP/c_intro.mp4" 4 46
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
