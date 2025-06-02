#!/bin/sh

# Check if input file is provided
if [ -z "$INPUT_FILE" ]; then
    echo "Please provide an input file by setting the INPUT_FILE environment variable"
    exit 1
fi

# Create output directory
mkdir -p /app/output

# Process the video
#ffmpeg -i "$INPUT_FILE" -c:v libx264 -c:a aac -hls_time 10 -hls_list_size 0 -hls_segment_filename "/app/output/segment%03d.ts" /app/output/playlist.m3u8
ffmpeg -i "$INPUT_FILE" -c:v libx264 -movflags frag_keyframe+empty_moov+default_base_moof -c:a aac /app/output/output.mp4
# Serve the files
cd /app/output
python3 -m http.server 8080
