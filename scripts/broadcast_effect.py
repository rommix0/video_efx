###########################################################
#                                                         #
#  BROADCAST VIDEO EFFECT                                 #
#                                                         #
#  AUTHOR: ANTHONY C. BARTMAN                             #
#  DATE:   11/26/2022, 7/12/2026                          #
#                                                         #
###########################################################

from scipy.signal import lfilter, hilbert, butter
from scipy.interpolate import interp1d
from tqdm import tqdm
from sys import argv
import cv2, numpy as np

def db2f(val):
    # decibel to float
    return 10 ** (val / 20)

def u2f(data):
    # uint8 to float
    return np.float32(np.int8(data-128)/128)

def f2u(data):
    # float to uint8
    return np.uint8(np.clip((data*128)+128, 0, 255))

def pink_noise(l, db=-15):
    # pink noise generation using filters
    b = np.array([0.049922035,-0.095993537,0.050612699,-0.004408786])
    a = np.array([1.0,-2.494956002,2.017265875,-0.522189400])
    pn = lfilter(b, a, np.random.uniform(-1.0, 1.0, size=l))
    pn /= np.amax(np.abs(pn)); pn *= db2f(db)
    return pn

def create_img_jitter(img, a=2.5):
    # create image jitter effect
    x_r = np.arange(img.shape[1])
    for y in range(img.shape[0]):
        for ch in range(3):
            intp = interp1d(x_r, img[y,:,ch], fill_value='extrapolate')
            x_rr = (x_r + np.random.uniform(-a, a, size=len(x_r))) % len(x_r)
            img[y,:,ch] = intp(x_rr)
    return img

def create_analog_jitter(sig, a=0.15):
    # create analog jitter effect
    x_r = np.arange(len(sig))
    intp = interp1d(x_r, sig, fill_value='extrapolate')
    x_rr = (x_r + np.random.uniform(-a, a, size=len(x_r))) % len(x_r)
    return intp(x_rr)

def simulate_interference(r_size, s_size, a=3):
    # simulate analog broadcast interference
    x = np.unique((np.arange(s_size) + np.random.uniform(-0.75, 0.75, size=s_size)) % s_size)
    y = np.random.uniform(-a, a, size=len(x))
    intp = interp1d(x, y, kind='cubic', fill_value='extrapolate')
    return np.clip(np.abs(intp(np.linspace(0, s_size, r_size))), -a, a)

def bfilter(data, freq=1250, ftype='lowpass', sr=8000):
    # splitter filter to split QAM signal (color)
    # from the FM signal (luma)
    b, a = butter(6, freq, ftype, fs=sr)
    return lfilter(b, a, data)

def sig2FM(data, cart=1000, dev=400, sr=8000, db=0):
    # convert signal to FM audio
    phase = np.cumsum(data * np.pi * dev / sr) % (2 * np.pi)
    i, q = np.cos(phase), np.sin(phase)
    car = 2 * np.pi * cart * (np.arange(len(data)) / sr)
    fm = i * np.cos(car) - q * np.sin(car)
    return fm * db2f(db)

def FM2sig(data, cart=1000, dev=400, sr=8000):
    # convert FM audio back to signal
    i, q = S2IQ(data, cart, sr)
    angle = np.arctan2(q, i)
    angle_change = np.append(0, np.diff(angle))
    angle_change[np.where(angle_change > np.pi)] -= 2 * np.pi
    angle_change[np.where(angle_change < -np.pi)] += 2 * np.pi
    outp = angle_change / (np.pi * dev / sr)
    return np.clip(outp, -1.0, 1.0)

def sig2QAM(data1, data2, cart=3000, sr=8000, db=0):
    # convert signals I and Q to QAM (for encoding color channels)
    if len(data1) != len(data2): return None
    car = 2 * np.pi * cart * (np.arange(len(data1)) / sr)
    iq = (np.sin(car) * data1) - (np.cos(car) * data2)
    return iq * db2f(db)

def QAM2sig(data, cart=3000, sr=8000, poly_fix=False):
    # convert QAM back to signals I and Q
    i, q = S2IQ(data, cart, sr)
    if poly_fix:
        return fix_sig(i), fix_sig(q)
    return i, q

def fix_sig(data):
    # interpolate to fit data
    ply = np.poly1d(np.polyfit(np.arange(len(data)), data, 3))
    data -= ply(np.arange(len(data)))
    return data

def S2IQ(data, cart=3000, sr=8000):
    # signal to IQ channel (for color encoding)
    rx = hilbert(data) * np.exp(-1j * 2 * np.pi * cart * np.arange(len(data)) / sr)
    return np.real(rx), np.imag(rx)

def splitYUV(img):
    # split image channels to YUV
    img = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)
    y, u, v = cv2.split(img)
    y = u2f(y).flatten()
    u = u2f(u).flatten()
    v = u2f(v).flatten()
    return y, u, v

def constructAnalogSignal(img, db=-20):
    # do main video to FM+QAM conversion here
    y, u, v = splitYUV(img)
    y, iq = sig2FM(y), sig2QAM(u, v)
    final_outp = y + iq
    final_outp += pink_noise(len(final_outp), db=db)
    return final_outp

def reconstructImage(sig, img_shp):
    # reconstruct image/frame from FM+QAM signal
    fm_s = bfilter(sig)
    iq_s = bfilter(sig, 2750, 'highpass')

    y = f2u(FM2sig(fm_s))
    v, u = QAM2sig(iq_s)
    u, v = f2u(u), f2u(v)

    y = y.reshape(img_shp)
    u = u.reshape(img_shp)
    v = v.reshape(img_shp)
    return cv2.cvtColor(cv2.merge((y,u,v)), cv2.COLOR_YUV2BGR)

def init_video(video_file):
    # load in video file
    cap = cv2.VideoCapture(video_file)
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    sxx = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    syy = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    return cap, total_frames, fps, sxx, syy

def init_writer(video_file, fps, sx, sy):
    # initialize the video writer
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    return cv2.VideoWriter(video_file, fourcc, fps, (sx, sy))

file = argv[1]
fname = '.'.join(file.split('.')[:-1])

print('+ Applying analog broadcast effect to video...')
cap, tf, fps, sx, sy = init_video(file)
out = init_writer(fname + '_broadcast.mp4', fps, sx, sy)
img_j = simulate_interference(tf, 200, a=4)
anl_j = simulate_interference(tf, 20, a=0.7)

for i in tqdm(range(tf)):
    ret, frame = cap.read()
    if not ret: break
    #frame = cv2.resize(frame, (sx, sy))

    sig = create_analog_jitter(constructAnalogSignal(frame), a=anl_j[i])
    frame = create_img_jitter(reconstructImage(sig, (sy, sx)), a=img_j[i])
    frame = cv2.blur(frame, (2, 2))

    out.write(frame)
    #cv2.imshow('frame', frame)
    #cv2.waitKey(1)
cap.release(); out.release()

print('...Done!')
