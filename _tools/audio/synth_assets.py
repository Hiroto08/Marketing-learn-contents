#!/usr/bin/env python3
"""Procedurally synthesize the channel's audio assets (BGM loop + SFX).

All output is generated from scratch by this script — no third-party
recordings or compositions are used, so the resulting files carry no
external copyright (treat as CC0 / self-made). Re-run to regenerate.

Usage: python3 _tools/audio/synth_assets.py  (writes into _assets/audio/)
"""
import os
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), "..", "..", "_assets", "audio")


def write_wav(path, stereo, peak=0.9):
    """stereo: float array shape (n, 2) in [-1, 1]."""
    m = np.max(np.abs(stereo)) or 1.0
    data = (stereo / m * peak * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    print(f"  wrote {os.path.relpath(path)}  {len(stereo)/SR:.2f}s")


def env_ad(n, a, d):
    """attack/decay envelope (samples)."""
    e = np.ones(n)
    a = min(a, n)
    e[:a] = np.linspace(0, 1, a)
    if d > 0:
        e *= np.exp(-np.arange(n) / d)
    return e


def note(freq, dur, vol=1.0, detune=0.15):
    """Soft EP-like tone: fundamental + weak octave, slight stereo detune."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    def voice(f):
        return np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    l = voice(freq * (1 - detune / 1000))
    r = voice(freq * (1 + detune / 1000))
    e = env_ad(n, int(0.02 * SR), int(0.9 * SR)) * vol
    return np.stack([l * e, r * e], axis=1)


def bgm_loop():
    """~33.7s calm chord-pad loop @ 76bpm: | Fmaj7 | Am7 | Dm7 | Cmaj7 | x2."""
    bpm = 76
    bar = 4 * 60 / bpm                       # 3.158s
    chords = [
        [174.61, 220.0, 261.63, 329.63],     # Fmaj7  (F3 A3 C4 E4)
        [220.0, 261.63, 329.63, 392.0],      # Am7    (A3 C4 E4 G4)
        [146.83, 220.0, 261.63, 349.23],     # Dm7    (D3 A3 C4 F4)
        [130.81, 196.0, 246.94, 329.63],     # Cmaj7  (C3 G3 B3 E4)
    ]
    basses = [87.31, 110.0, 73.42, 65.41]    # F2 A2 D2 C2
    total_n = int(8 * bar * SR)
    mix = np.zeros((total_n, 2))
    for rep in range(2):
        for ci, (ch, bass) in enumerate(zip(chords, basses)):
            start = int(((rep * 4 + ci) * bar) * SR)
            for f in ch:
                seg = note(f, bar * 1.05, vol=0.22)
                end = min(start + len(seg), total_n)
                mix[start:end] += seg[: end - start]
            bt = np.arange(int(bar * SR)) / SR
            bseg = np.sin(2 * np.pi * bass * bt) * env_ad(len(bt), int(0.03 * SR), int(1.4 * SR)) * 0.30
            end = min(start + len(bseg), total_n)
            mix[start:end] += np.stack([bseg, bseg], axis=1)[: end - start]
    # vinyl-ish air: very low filtered noise bed
    rng = np.random.default_rng(7)
    noise = rng.standard_normal((total_n, 2)) * 0.012
    kernel = np.ones(96) / 96
    for c in range(2):
        noise[:, c] = np.convolve(noise[:, c], kernel, mode="same")
    mix += noise
    # gentle 2-bar volume swell (breathing)
    lfo = 0.92 + 0.08 * np.sin(2 * np.pi * np.arange(total_n) / (2 * bar * SR))
    mix *= lfo[:, None]
    # make loop-safe: crossfade tail into head
    xf = int(0.4 * SR)
    ramp = np.linspace(0, 1, xf)[:, None]
    mix[:xf] = mix[:xf] * ramp + mix[-xf:] * (1 - ramp)
    return mix[: total_n - xf]


def sfx_pop():
    """55ms soft pop for element reveals."""
    n = int(0.055 * SR)
    t = np.arange(n) / SR
    f = np.linspace(880, 620, n)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_ad(n, int(0.002 * SR), int(0.012 * SR))
    return np.stack([s, s], axis=1)


def sfx_whoosh():
    """220ms airy whoosh for slide transitions (band-swept noise)."""
    n = int(0.22 * SR)
    rng = np.random.default_rng(3)
    s = rng.standard_normal(n)
    win = np.hanning(n)
    out = np.zeros(n)
    width = np.linspace(120, 8, n).astype(int)  # lowpass opening → closing
    csum = np.cumsum(np.concatenate([[0.0], s]))
    for i in range(n):
        w = max(2, width[i])
        a, b = max(0, i - w), i
        out[i] = (csum[b + 1] - csum[a]) / (b + 1 - a)
    out *= win
    return np.stack([out, out], axis=1)


def sfx_ding():
    """650ms soft chime for key-number reveals."""
    n = int(0.65 * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * 1046.5 * t)
         + 0.5 * np.sin(2 * np.pi * 1568.0 * t)
         + 0.25 * np.sin(2 * np.pi * 2093.0 * t))
    s *= env_ad(n, int(0.003 * SR), int(0.16 * SR))
    return np.stack([s, s], axis=1)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    print("synthesizing audio assets ...")
    write_wav(os.path.join(OUT, "bgm_calm_loop.wav"), bgm_loop(), peak=0.5)
    write_wav(os.path.join(OUT, "sfx_pop.wav"), sfx_pop(), peak=0.6)
    write_wav(os.path.join(OUT, "sfx_whoosh.wav"), sfx_whoosh(), peak=0.5)
    write_wav(os.path.join(OUT, "sfx_ding.wav"), sfx_ding(), peak=0.55)
    print("done.")
