#!/usr/bin/env bash
# Stitch the "extras" clips (with sound) into one video with a title card before each clip.
# usage: overview-extras.sh MP4_DIR OUT.mp4 [SPEED] [HOLD]
#   Each clip = a silent terminal part, then (except the bazaar) a result segment with the generated image / audio.
#   SPLIT = seconds where the terminal part ends (0 = the whole clip is terminal). SPEED > 1 speeds up the terminal
#   part only (never the speech); HOLD = seconds the last terminal frame stays on screen (default 6). Cards: 3 s.
set -eu
DIR=$1; OUT=$2; SPEED=${3:-1}; HOLD=${4:-6}
FONT=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
W=1468; H=1040; TMP=$(mktemp -d)
ENC="-c:v libx264 -preset slow -crf 28 -pix_fmt yuv420p -r 12 -c:a aac -b:a 96k -ar 44100 -ac 2"
CLIPS=(
  "03_bazaar|0|Lab 3 · A2A bazaar: three vendors, one room"
  "04_cloud_image_show|14.09|Lab 4 · Cloud image, and the picture"
  "04_tts_sound|12.93|Lab 4 · Text to speech, with sound"
  "04_chain_sound|19.18|Lab 4 · Chain: text, image, speech"
)
card() { # $1 = text, $2 = output, $3 = seconds, $4 = font size
  printf '%s' "$1" > "$TMP/t.txt"
  ffmpeg -loglevel error -y -f lavfi -i "color=c=0x272822:s=${W}x${H}:d=$3:r=12" -f lavfi -i anullsrc=r=44100:cl=stereo \
    -vf "drawtext=fontfile=$FONT:textfile=$TMP/t.txt:fontsize=$4:fontcolor=white:x=(w-tw)/2:y=(h-th)/2,format=yuv420p" \
    -t "$3" $ENC "$2"
}
i=0; : > "$TMP/list.txt"
card "Building Stuff with GenAI · extras: A2A and sound" "$TMP/c_intro.mp4" 4 46
echo "file '$TMP/c_intro.mp4'" >> "$TMP/list.txt"
for e in "${CLIPS[@]}"; do
  n=${e%%|*}; rest=${e#*|}; S=${rest%%|*}; t=${rest#*|}
  [ -f "$DIR/$n.mp4" ] || { echo "skip $n"; continue; }
  i=$((i+1)); card "$t" "$TMP/c$i.mp4" 3 64
  if [ "$S" = 0 ]; then
    F="[0:v]setpts=PTS/$SPEED,fps=12,tpad=stop_mode=clone:stop_duration=$HOLD,format=yuv420p[v];[0:a]apad=pad_dur=$HOLD[a]"
    ffmpeg -loglevel error -y -i "$DIR/$n.mp4" -filter_complex "$F" -map "[v]" -map "[a]" $ENC "$TMP/v$i.mp4"
  else
    F="[0:v]trim=0:$S,setpts=(PTS-STARTPTS)/$SPEED,fps=12,tpad=stop_mode=clone:stop_duration=$HOLD[v1];"
    F+="[0:v]trim=start=$S,setpts=PTS-STARTPTS,fps=12[v2];"
    F+="[0:a]atrim=0:$S,asetpts=PTS-STARTPTS,atempo=$SPEED,apad=pad_dur=$HOLD[a1];[0:a]atrim=start=$S,asetpts=PTS-STARTPTS[a2];"
    F+="[v1][a1][v2][a2]concat=n=2:v=1:a=1[vc][a];[vc]format=yuv420p[v]"
    ffmpeg -loglevel error -y -i "$DIR/$n.mp4" -filter_complex "$F" -map "[v]" -map "[a]" $ENC "$TMP/v$i.mp4"
  fi
  printf "file '%s'\nfile '%s'\n" "$TMP/c$i.mp4" "$TMP/v$i.mp4" >> "$TMP/list.txt"
done
ffmpeg -loglevel error -y -f concat -safe 0 -i "$TMP/list.txt" -c copy -movflags +faststart "$OUT"
rm -rf "$TMP"
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
