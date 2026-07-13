# VIDEO LOW PASS FILTER EFFECT
#
# AUTHOR: ANTHONY C. BARTMAN
# DATE:   11/25/2022

from scipy.signal.windows import hann
from scipy.fft import dct, idct
from tqdm import tqdm
import cv2, numpy as np
import sys
def u2f(data):
    return np.float32(np.int8(data - 128) / 128)
def f2u(data):
    return np.uint8(np.clip((data * 128) + 128, 0, 255))
def lpf(data, size=None):
    if size is None: size = len(data)
    dt = dct(data, norm='ortho')
    wind = hann(size * 2)[size:]
    
    if size < len(data): dt[size:] = 0.0
    dt[:size] *= wind
    
    return idct(dt, norm='ortho')
def init_video(video_file):
    cap = cv2.VideoCapture(video_file)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sxx = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    syy = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    return cap, total_frames, fps, sxx, syy
def init_writer(video_file, fps, sx, sy):
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    return cv2.VideoWriter(video_file, fourcc, fps, (sx, sy))

print('+ Loading in video...')
cap, tf, fps, sx, sy = init_video(sys.argv[1])
buf = np.zeros([tf, sy, sx, 3], dtype='uint8')
for i in tqdm(range(tf)):
    ret, frame = cap.read()
    if not ret: break
    buf[i] = frame
cap.release()
buf = buf.T

print('+ LPF video...')
for y in tqdm(range(sy)):
    for x in range(sx):
        for ch in range(3):
            buf[ch, x,y] = f2u(lpf(u2f(buf[ch, x,y]), 16))
buf = buf.T

out = init_writer('lpf_video_test.mp4', fps, sx, sy)
for i in tqdm(range(tf)):
    out.write(buf[i])
out.release()
