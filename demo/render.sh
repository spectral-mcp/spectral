#!/bin/sh
set -eu

cd "$(dirname "$0")"

agg --font-size 28 --theme monokai --last-frame-duration 5 demo.cast demo.gif
ffmpeg -y -i demo.gif \
    -movflags faststart -pix_fmt yuv420p \
    -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black" \
    -c:v libx264 -preset slow -crf 18 -r 30 \
    demo.mp4
rm demo.gif

echo "Done: demo.mp4"
