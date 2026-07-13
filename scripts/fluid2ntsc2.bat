@echo off
echo Converting Widescreen YouTube 60p to 30i for NTSC DVDs
ffmpeg -y -i "%1" -vf scale=720:480,fps=60000/1001,tinterlace=interleave_top:low_pass_filter -dc 9 -async 1 -target ntsc-dvd -aspect 16:9 -flags +ilme+ildct -alternate_scan 1 "%~n1_dvd.vob"