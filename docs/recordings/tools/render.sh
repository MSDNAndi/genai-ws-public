#!/usr/bin/env bash
# Render casts to GIF (agg) and MP4 (ffmpeg, H.264).  usage: render.sh CAST_DIR OUT_DIR [name ...]
# Needs agg (github.com/asciinema/agg) on PATH or in $AGG, ffmpeg, and fonts-dejavu-core.
set -eu
CAST=$1; OUT=$2; shift 2
AGG=${AGG:-agg}
mkdir -p "$OUT" "$OUT/.gif"
names=${*:-$(cd "$CAST" && ls *.cast | sed 's/\.cast$//')}
for n in $names; do
  "$AGG" --font-size 24 --font-family "DejaVu Sans Mono" --theme monokai --idle-time-limit 2 \
         --last-frame-duration 5 --fps-cap 15 "$CAST/$n.cast" "$OUT/.gif/$n.gif" >/dev/null 2>&1
  ffmpeg -loglevel error -y -i "$OUT/.gif/$n.gif" -vf "fps=12,scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p" \
         -c:v libx264 -preset slow -crf 28 -movflags +faststart "$OUT/$n.mp4"
  echo "$n: $(du -h "$OUT/$n.mp4" | cut -f1)"
done
