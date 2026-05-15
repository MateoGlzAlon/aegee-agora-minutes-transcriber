#!/usr/bin/env bash

set -e

INPUT_DIR="./input"
OUTPUT_DIR="./output"

mkdir -p "$OUTPUT_DIR"

for file in "$INPUT_DIR"/*; do
  filename=$(basename "$file")
  name="${filename%.*}"
  ext="${filename##*.}"

  if [ "$ext" = "wma" ] || [ "$ext" = "WMA" ]; then
    echo "Convert: $filename"

    ffmpeg -y -i "$file" \
      -vn \
      -ar 44100 \
      -ac 2 \
      -b:a 192k \
      "$OUTPUT_DIR/${name}.mp3"
  else
    echo "Skip: $filename"
  fi
done