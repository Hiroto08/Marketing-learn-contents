#!/usr/bin/env python3
"""表現コード v1 の音素材を合成する（外部素材を使わない＝ライセンスは自作・CC0相当）。

  python3 _tools/expression/synth_v1.py            # _assets/audio/v1/ に書き出す

BGM 3曲（各 60 秒以上・曲の中で同じ4小節を3回以上くり返さない）と、
意味に対応した効果音4種（問い・数字・答え・場面転換）。
仕様は docs/expression/expression-code.md §5〜§7。数値を変えるときは仕様書と同じコミットで直す。
"""
import os
import sys
import wave

import numpy as np

SR = 48000
OUT = os.path.join(os.path.dirname(__file__), '..', '..', '_assets', 'audio', 'v1')

NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def hz(name):
    """'A4' → 440.0"""
    n, o = name[:-1], int(name[-1])
    semi = NOTE[n[0]] + (1 if '#' in n else 0) - (1 if 'b' in n else 0)
    return 440.0 * 2 ** ((semi - 9) / 12 + (o - 4))


def write(path, st, peak):
    st = st / (np.abs(st).max() + 1e-9) * peak
    pcm = (np.clip(st, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def t_axis(dur):
    return np.arange(int(dur * SR)) / SR


def epiano(f, dur, vol=1.0):
    """やわらかいエレピ（FM＋倍音。3〜6kHz にも成分を持たせる）"""
    t = t_axis(dur)
    env = np.minimum(t / 0.006, 1.0) * np.exp(-t / (0.9 + 60 / f))
    mod = np.sin(2 * np.pi * f * 2 * t) * 1.6 * np.exp(-t / 0.25)
    s = np.sin(2 * np.pi * f * t + mod)
    s += 0.25 * np.sin(2 * np.pi * f * 3 * t) * np.exp(-t / 0.12)
    s += 0.30 * np.sin(2 * np.pi * f * 7 * t) * np.exp(-t / 0.05)   # 打鍵のきらめき
    return s * env * vol


def bass(f, dur, vol=1.0):
    t = t_axis(dur)
    env = np.minimum(t / 0.01, 1.0) * np.exp(-t / 0.7)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t)) * env * vol


def shaker(dur, vol, rng):
    """高域のノイズ（6kHz 以上）。BGM がこもって聞こえないための成分"""
    n = int(dur * SR)
    x = rng.standard_normal(n)
    x = np.diff(np.diff(x, prepend=0), prepend=0)        # 2階差分＝強い高域強調
    t = np.arange(n) / SR
    return x / (np.abs(x).max() + 1e-9) * np.exp(-t / 0.03) * vol


def pad(freqs, dur, vol=1.0):
    t = t_axis(dur)
    env = np.minimum(t / 0.6, 1.0) * np.minimum((dur - t) / 0.6, 1.0)
    s = sum(np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t) for f in freqs)
    return s / len(freqs) * env * vol


def place(buf, sig, at, pan=0.0):
    i = int(at * SR)
    n = min(len(sig), buf.shape[0] - i)
    if n <= 0:
        return
    buf[i:i + n, 0] += sig[:n] * (1 - max(pan, 0))
    buf[i:i + n, 1] += sig[:n] * (1 + min(pan, 0))


CH = {  # コード → (ベース音, 構成音)
    'Cmaj7': ('C2', ['E4', 'G4', 'B4', 'D5']), 'Am7': ('A1', ['C4', 'E4', 'G4', 'B4']),
    'Fmaj7': ('F2', ['A3', 'C4', 'E4', 'G4']), 'G6': ('G1', ['B3', 'D4', 'E4', 'G4']),
    'Dm7': ('D2', ['F3', 'A3', 'C4', 'E4']), 'Em7': ('E2', ['G3', 'B3', 'D4', 'E4']),
    'C/E': ('E2', ['G3', 'C4', 'E4', 'G4']), 'Gsus': ('G1', ['C4', 'D4', 'G4', 'A4']),
}


def track(bpm, bars, seed, feel):
    """bars: コード名の並び（1小節1コード）。feel: 'calm' | 'curious' | 'steady'"""
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    bar = 4 * beat
    total = bar * len(bars)
    buf = np.zeros((int(total * SR) + SR, 2))
    for bi, name in enumerate(bars):
        root, tones = CH[name]
        t0 = bi * bar
        place(buf, pad([hz(x) for x in tones[:3]], bar + 0.5, 0.10), t0)
        place(buf, bass(hz(root) * 2, bar * 0.9, 0.20), t0)
        if feel != 'calm':
            place(buf, bass(hz(root) * 2, beat, 0.14), t0 + 2.5 * beat)
        # アルペジオ：小節ごとに順番を変える（同じ音型のくり返しに聞こえないように）
        order = list(rng.permutation(4))
        steps = {'calm': [0, 1, 2, 3], 'curious': [0, 0.75, 1.5, 2.5, 3.25], 'steady': [0, 1, 1.5, 2.5, 3]}[feel]
        for k, st in enumerate(steps):
            f = hz(tones[order[k % 4]]) * (2 if (k + bi) % 5 == 4 else 1)
            place(buf, epiano(f, beat * 2.2, 0.30 + 0.06 * rng.random()), t0 + st * beat,
                  pan=0.25 * (-1) ** k)
        for k in range(8):                                # 8分のシェイカー（裏拍を強く）
            place(buf, shaker(0.12, 0.16 if k % 2 == 0 else 0.30, rng), t0 + k * beat / 2, pan=0.15)
    # ループのつなぎ目：末尾1秒ぶんの余韻を先頭に重ねる
    n = int(total * SR)
    tail = buf[n:n + SR]
    buf[:len(tail)] += tail
    return buf[:n]


TRACKS = {
    # 曲名: (bpm, 小節の並び, 種, 型)。どれも 24小節＝60秒以上
    'bgm_a_calm':    (84, ['Cmaj7', 'Am7', 'Fmaj7', 'G6', 'Em7', 'Am7', 'Dm7', 'Gsus',
                           'Cmaj7', 'C/E', 'Fmaj7', 'G6', 'Am7', 'Em7', 'Fmaj7', 'Gsus',
                           'Dm7', 'G6', 'Cmaj7', 'Am7', 'Fmaj7', 'Em7', 'Dm7', 'G6'], 11, 'calm'),
    'bgm_b_curious': (92, ['Am7', 'Fmaj7', 'Cmaj7', 'G6', 'Dm7', 'Em7', 'Fmaj7', 'Gsus',
                           'Am7', 'C/E', 'Fmaj7', 'Dm7', 'Am7', 'G6', 'Fmaj7', 'Em7',
                           'Dm7', 'Am7', 'Fmaj7', 'G6', 'Cmaj7', 'Em7', 'Am7', 'Gsus',
                           'Fmaj7', 'G6', 'Am7', 'Am7'], 23, 'curious'),
    'bgm_c_steady':  (88, ['Fmaj7', 'G6', 'Em7', 'Am7', 'Dm7', 'G6', 'Cmaj7', 'C/E',
                           'Fmaj7', 'Em7', 'Dm7', 'Gsus', 'Am7', 'Fmaj7', 'Cmaj7', 'G6',
                           'Dm7', 'Em7', 'Fmaj7', 'G6', 'Am7', 'G6', 'Fmaj7', 'Gsus'], 37, 'steady'),
}


def mallet(f, dur, vol=1.0):
    t = t_axis(dur)
    env = np.minimum(t / 0.003, 1.0) * np.exp(-t / (dur / 3.5))
    s = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.08) \
        + 0.2 * np.sin(2 * np.pi * 4.07 * f * t) * np.exp(-t / 0.03)
    return s * env * vol


def thump(dur=0.16, f0=110, f1=48, vol=1.0):
    t = t_axis(dur)
    f = f1 + (f0 - f1) * np.exp(-t / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.06) * vol


def tick(rng, vol=1.0):
    n = int(0.012 * SR)
    x = np.diff(rng.standard_normal(n), prepend=0)
    return x / np.abs(x).max() * np.exp(-np.arange(n) / SR / 0.003) * vol


def sfx_question():
    """問い：上がって終わる2音（A4→E5）。解決しない＝続きを待たせる。動画の 0.00 秒に置く"""
    buf = np.zeros((int(0.9 * SR), 2))
    place(buf, thump(vol=0.8), 0.0)
    place(buf, mallet(hz('A4'), 0.5, 0.7), 0.0, pan=-0.15)
    place(buf, mallet(hz('E5'), 0.7, 0.8), 0.14, pan=0.15)
    return buf


def sfx_number():
    """数字：低い打音＋短いクリック＋高い1音（E6）。数字が出る瞬間に置く"""
    rng = np.random.default_rng(5)
    buf = np.zeros((int(0.5 * SR), 2))
    place(buf, thump(vol=1.0), 0.0)
    place(buf, tick(rng, 0.35), 0.0)
    place(buf, mallet(hz('E6'), 0.35, 0.28), 0.0)
    return buf


def sfx_answer():
    """答え：下がって落ち着く3音（G5→E5→C5）＋和音。問いの音と対になる"""
    buf = np.zeros((int(1.3 * SR), 2))
    for k, n in enumerate(['G5', 'E5', 'C5']):
        place(buf, mallet(hz(n), 0.6, 0.6), 0.09 * k, pan=0.2 - 0.2 * k)
    place(buf, pad([hz('C4'), hz('E4'), hz('G4')], 1.0, 0.5), 0.18)
    place(buf, thump(vol=0.6), 0.18)
    return buf


def sfx_turn():
    """場面転換：0.3秒のやわらかい息。長尺だけで使う"""
    rng = np.random.default_rng(9)
    n = int(0.32 * SR)
    x = rng.standard_normal(n)
    k = np.ones(24) / 24
    x = np.convolve(x, k, 'same') - np.convolve(x, np.ones(200) / 200, 'same')   # 帯域を中域に寄せる
    t = np.arange(n) / SR
    env = np.sin(np.pi * t / t[-1]) ** 2
    s = x / np.abs(x).max() * env
    return np.stack([s, s[::-1] * 0.9], 1)


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, (bpm, bars, seed, feel) in TRACKS.items():
        st = track(bpm, bars, seed, feel)
        write(os.path.join(OUT, name + '.wav'), st, 0.5)
        print(f'{name}.wav  {len(st)/SR:.1f}s  {bpm}bpm  {len(bars)}小節')
    for name, fn, peak in [('sfx_question', sfx_question, 0.8), ('sfx_number', sfx_number, 0.8),
                           ('sfx_answer', sfx_answer, 0.8), ('sfx_turn', sfx_turn, 0.4)]:
        st = fn()
        write(os.path.join(OUT, name + '.wav'), st, peak)
        print(f'{name}.wav  {len(st)/SR:.2f}s')


if __name__ == '__main__':
    sys.exit(main())
