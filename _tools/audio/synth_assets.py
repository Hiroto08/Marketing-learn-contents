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


def note(freq, dur, vol=1.0, detune=0.15, attack=0.02, tau=0.9):
    """Soft EP-like tone: fundamental + weak octave, slight stereo detune."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    def voice(f):
        return np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * 2 * f * t)
    l = voice(freq * (1 - detune / 1000))
    r = voice(freq * (1 + detune / 1000))
    e = env_ad(n, int(attack * SR), int(tau * SR)) * vol
    return np.stack([l * e, r * e], axis=1)


def pluck(freq, dur=0.5, vol=1.0, pan=0.0):
    """Bright kalimba/music-box pluck: harmonics with fast decay."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = (np.sin(2 * np.pi * freq * t)
         + 0.40 * np.sin(2 * np.pi * 2 * freq * t)
         + 0.12 * np.sin(2 * np.pi * 3 * freq * t))
    s *= env_ad(n, int(0.002 * SR), int(0.16 * SR)) * vol
    l = s * (1 - max(pan, 0) * 0.6)
    r = s * (1 + min(pan, 0) * 0.6)
    return np.stack([l, r], axis=1)


def bgm_loop():
    """~22.7s bright, cozy loop @ 84bpm: | C | G | Am | F | x2 (I–V–vi–IV).

    Higher register, add9 pads with slow attack + light kalimba arpeggio
    for a pleasant/upbeat (not somber) mood."""
    bpm = 84
    bar = 4 * 60 / bpm                              # 2.857s
    C4, D4, E4, F4, G4, A4, B4 = 261.63, 293.66, 329.63, 349.23, 392.0, 440.0, 493.88
    C5, D5, E5, G5, A5 = 523.25, 587.33, 659.25, 783.99, 880.0
    chords = [                                       # bright add9 voicings
        ([C4, E4, G4, D5], 130.81),                  # C add9   / C3
        ([D4, G4, B4, D5], 196.00),                  # G add4   / G3
        ([E4, A4, C5, E5], 220.00),                  # Am add   / A3
        ([F4, A4, C5, G5], 174.61),                  # F add9   / F3
    ]
    arps = [                                         # 8x 8th-note pluck pattern per bar
        [C5, G4, E5, G4, D5, G4, E5, G5],
        [D5, B4, G5, B4, D5, B4, G5, A5],
        [E5, C5, A5, C5, E5, C5, A5, G5],
        [C5, A4, G5, A4, C5, A4, E5, G5],
    ]
    total_n = int(8 * bar * SR)
    mix = np.zeros((total_n, 2))
    eighth = bar / 8
    for rep in range(2):
        for ci, ((ch, bass), arp) in enumerate(zip(chords, arps)):
            start = int(((rep * 4 + ci) * bar) * SR)
            for f in ch:                             # warm pad, slow attack
                seg = note(f, bar * 1.1, vol=0.16, attack=0.35, tau=1.6)
                end = min(start + len(seg), total_n)
                mix[start:end] += seg[: end - start]
            bt = np.arange(int(bar * SR)) / SR       # light bass, not heavy
            bseg = np.sin(2 * np.pi * bass * bt) * env_ad(len(bt), int(0.02 * SR), int(1.2 * SR)) * 0.17
            end = min(start + len(bseg), total_n)
            mix[start:end] += np.stack([bseg, bseg], axis=1)[: end - start]
            for j, f in enumerate(arp):              # sparkle arpeggio
                if f is None:
                    continue
                p = pluck(f, vol=0.30 if j % 2 == 0 else 0.20,
                          pan=0.5 if j % 4 in (1, 3) else -0.3)
                ps = start + int(j * eighth * SR)
                pe = min(ps + len(p), total_n)
                mix[ps:pe] += p[: pe - ps]
    # soft air bed (much lower than before)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal((total_n, 2)) * 0.005
    kernel = np.ones(96) / 96
    for c in range(2):
        noise[:, c] = np.convolve(noise[:, c], kernel, mode="same")
    mix += noise
    # very gentle 2-bar swell
    lfo = 0.95 + 0.05 * np.sin(2 * np.pi * np.arange(total_n) / (2 * bar * SR))
    mix *= lfo[:, None]
    # loop-safe crossfade
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
