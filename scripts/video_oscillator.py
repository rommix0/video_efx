###########################################################
#                                                         #
#  VIDEO OSCILLATOR EFFECT                                #
#                                                         #
#  AUTHOR: ANTHONY C. BARTMAN                             #
#  DATE:   11/19/2022, 7/12/2026                          #
#                                                         #
#  requires FFMPEG to be installed and put on $PATH       #
#                                                         #
###########################################################

from scipy.interpolate import CubicSpline
from subprocess import call
from os import remove
from sys import argv
from tqdm import tqdm
import cv2, numpy as np
import soundfile as sf

def init_video(video_file):
    # initialize video
    cap = cv2.VideoCapture(video_file)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sxx = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    syy = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return cap, fps, total_frames, sxx, syy

def init_writer(video_file, fps, sx, sy):
    # initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    return cv2.VideoWriter(video_file, fourcc, fps, (sx, sy))

file = argv[1]

# extract audio into tmp.wav
call(['ffmpeg','-y','-hide_banner','-loglevel','panic','-i',file,'-c:a','pcm_f32le','-ar','48000','-ac','1','tmp.wav'])

# load video
cap, fps, t_frames, sx, sy = init_video(file)
out = init_writer('tmp.mp4', fps, sx, sy)
aud_blk = 48000 // fps

# perform the oscillation effect
with sf.SoundFile('tmp.wav','r') as f:
    for i in tqdm(range(t_frames)):
        ret, frame = cap.read()
        if not ret: break

        buff = np.zeros(aud_blk, dtype='uint16')
        aud = np.uint16(np.abs(f.read(aud_blk) * sx))
        buff[:len(aud)] = aud

        spl = CubicSpline(np.arange(len(buff)), buff)
        osc = np.uint16(np.abs(spl(np.linspace(0, aud_blk, sy))))

        for y, j in enumerate(osc):
            if j == 0: continue
            frame_chunk = frame[y, j:sx - j]
            if len(frame_chunk) == 0:
                frame_chunk = frame[y, j:j+8]
            frame[y] = cv2.resize(frame_chunk, (3, sx))
        out.write(frame)

cap.release()
out.release()

# mux the video and audio together
call(['ffmpeg','-y','-hide_banner','-loglevel','panic','-i','tmp.mp4','-i','tmp.wav','-c:v','copy','-c:a','aac','-b:a','128k','-map','0:v','-map','1:a','-shortest','osc.mp4'])
#call(['rm','-f','tmp.mp4','tmp.wav'])
remove('tmp.mp4')
remove('tmp.wav')
