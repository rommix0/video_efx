#!/bin/bash

ffmpeg -f rawvideo -pix_fmt rgb24 -video_size 64x64 -r 30 -i "$1" -f u8 -ar 368640 -ac 1 -i "$1" -af "volume=0.4" -ar 48000 -c:a aac -b:a 128k -vf scale=-1:480:flags=neighbor,format=yuv420p -c:v libx264 -crf 20 "${1%.*}_dumped.mp4"