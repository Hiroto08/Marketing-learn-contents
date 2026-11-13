#!/usr/bin/env python3
"""表現コード v1 の音声ミックス（make_video.py --expr v1 から呼ばれる）。

仕様は docs/expression/expression-code.md §5〜§7。ここの数値を変えるときは、仕様書と同じコミットで直す。

  声   ：ハイパス 70Hz → 250Hz −2dB → 3.5kHz +3dB → 8kHz 以上 +2dB → コンプレッサー 3:1
  BGM  ：3曲を回のフォルダ名で回す。0.00秒から鳴らす。声がある間は自動で下げる（サイドチェイン）。
         数字・答えの直前の「間」では、さらに下げる
  効果音：意味ごとに1種（問い・数字・答え・場面転換）。本数の上限つき
  仕上げ：−14.0 LUFS（±0.5）・トゥルーピーク −1.0dBTP 以下
"""
import hashlib
import json
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, '..', '..', '_assets', 'audio', 'v1'))

BGM_TRACKS = ['bgm_a_calm.wav', 'bgm_b_curious.wav', 'bgm_c_steady.wav']
SFX = {  # 意味: (ファイル, 音量 dB)
    'question': ('sfx_question.wav', -9.0),
    'number':   ('sfx_number.wav', -10.0),
    'answer':   ('sfx_answer.wav', -9.0),
    'turn':     ('sfx_turn.wav', -20.0),
}
BGM_DB = -17.0          # BGM の基準音量（声の無い所）。声がある間はサイドチェインでさらに約8dB下がる
DIP_DB = -9.0           # 数字・答えの直前の「間」で BGM を下げる量
DIP_SEC = 0.45
VOICE_CHAIN = ("highpass=f=70,"
               "equalizer=f=250:t=o:w=1.0:g=-2,"
               "equalizer=f=3500:t=o:w=1.2:g=3,"
               "highshelf=f=8000:g=2,"
               "acompressor=threshold=-22dB:ratio=3:attack=8:release=120:makeup=2")
TARGET_I, TOL_I, LIMIT = -14.0, 0.5, 0.7943      # 0.7943 = −2.0 dBFS（AAC 変換後のトゥルーピークを −1.0 以下に収める余裕）

# 数字＋単位（西暦は「数字の見せ場」に数えない）
NUM_RE = re.compile(r'[−\-+]?\d[\d,\.]*\s*(?:%|％|倍|円|ドル|億|万|人|件|回|時間|か月|ヶ月|日|割|店|社|秒|分|個|本|点)')


def has_number(text: str) -> bool:
    return bool(NUM_RE.search(text or ''))


def pick_bgm(key: str) -> str:
    """回のフォルダ名から曲を決める（同じ回は常に同じ曲。回が変わると曲が回る）"""
    m = re.search(r'(\d+)', key)
    i = int(m.group(1)) if m else int(hashlib.md5(key.encode()).hexdigest(), 16)
    return os.path.join(ASSETS, BGM_TRACKS[i % len(BGM_TRACKS)])


def plan_events(step_events, slide_starts, total, vertical, answer_text=''):
    """step_events: [(time, slide_index, step_in_slide, screen_text)]
    戻り値: [(time, kind)]。本数の上限と最小間隔をここで守る。"""
    ev = [(0.0, 'question')]
    seen_slide = set()
    for t, si, k, text in step_events:
        if answer_text and answer_text in re.sub(r'\s', '', text):
            ev.append((t, 'answer'))
        elif has_number(text) and si not in seen_slide and t > 1.0:
            seen_slide.add(si)                 # 数字の音は1枚に1回（最初の数字）
            ev.append((t, 'number'))
    if not vertical:
        for t in slide_starts[1:]:
            ev.append((t, 'turn'))
    ev.sort()
    cap = 5 if vertical else max(6, int(total / 10))
    min_gap = 1.5
    prio = {'question': 0, 'answer': 1, 'number': 2, 'turn': 3}
    kept = []
    for t, kind in sorted(ev, key=lambda e: (prio[e[1]], e[0])):
        if len(kept) >= cap or t > total - 0.4:
            continue
        if all(abs(t - u) >= min_gap for u, _ in kept):
            kept.append((t, kind))
    return sorted(kept)


def _measure(path):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-i', path, '-af',
                          'loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    return float(json.loads(out[out.rindex('{'):out.rindex('}') + 1])['input_i'])


def _true_peak(path):
    out = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', path, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                         capture_output=True, text=True).stderr
    t = out[out.rfind('Summary'):]
    return float(re.search(r'Peak:\s*(-?[\d.]+)', t).group(1))


def mix(src, dst, total, events, key, vertical, report=None):
    """src: ナレーションだけの mp4。dst: 完成 mp4（映像はコピー）。"""
    bgm = pick_bgm(key)
    kinds = [k for k in SFX if any(e[1] == k for e in events)]
    inputs = ['-i', src, '-stream_loop', '-1', '-i', bgm]
    for k in kinds:
        inputs += ['-i', os.path.join(ASSETS, SFX[k][0])]

    fade_in = 0.05
    fade_out = 0.15 if vertical else 3.0     # Shorts は末尾で消さない（くり返し再生のつなぎ目に谷を作らない）
    dips = ''.join(f",volume=enable='between(t,{max(0, t - DIP_SEC):.2f},{t:.2f})':volume={DIP_DB}dB"
                   for t, kind in events if kind in ('number', 'answer'))
    flt = [f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,{VOICE_CHAIN},asplit=2[v][vsc]",
           f"[1:a]atrim=0:{total:.3f},afade=t=in:d={fade_in},"
           f"afade=t=out:st={max(0.0, total - fade_out):.3f}:d={fade_out},volume={BGM_DB}dB{dips}[b0]",
           "[b0][vsc]sidechaincompress=threshold=0.02:ratio=5:attack=15:release=400[bgm]"]
    ins = ['[v]', '[bgm]']
    idx = 2
    for k in kinds:
        evs = [e for e in events if e[1] == k]
        names = ''.join(f'[{k}{j}]' for j in range(len(evs)))
        flt.append(f"[{idx}:a]volume={SFX[k][1]}dB,asplit={len(evs)}{names}")
        for j, (t, _) in enumerate(evs):
            flt.append(f"[{k}{j}]adelay={int(t * 1000)}:all=1[{k}d{j}]")
            ins.append(f'[{k}d{j}]')
        idx += 1
    flt.append(f"{''.join(ins)}amix=inputs={len(ins)}:duration=first:normalize=0[m]")

    tmp = dst + '.exmix.wav'
    subprocess.run(['ffmpeg', '-y', *inputs, '-filter_complex', ';'.join(flt),
                    '-map', '[m]', '-ar', '48000', tmp], check=True, capture_output=True)
    cur = _measure(tmp)
    gain = TARGET_I - cur
    limit = LIMIT
    for _ in range(6):
        subprocess.run(['ffmpeg', '-y', '-i', src, '-i', tmp, '-map', '0:v', '-map', '1:a',
                        '-af', f"volume={gain:.2f}dB,alimiter=level_in=1:level_out=1:limit={limit:.4f}:"
                               f"attack=4:release=60:level=false,aresample=48000",
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', dst],
                       check=True, capture_output=True)
        out_i = _measure(dst)
        tp = _true_peak(dst)
        if abs(TARGET_I - out_i) <= TOL_I * 0.6 and tp <= -1.0:
            break
        gain += TARGET_I - out_i
        if tp > -1.0:                      # AAC 変換でピークが伸びたぶん、リミッターを下げる
            limit *= 10 ** ((-1.2 - tp) / 20)
    os.remove(tmp)
    rec = {'bgm': os.path.basename(bgm), 'events': [[round(t, 2), k] for t, k in events],
           'integrated_lufs': round(out_i, 2), 'true_peak': tp, 'vertical': vertical, 'total': round(total, 2)}
    if report:
        with open(report, 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
    print(f"  expr v1 mix: bgm={rec['bgm']} sfx={len(events)} "
          f"({', '.join(f'{k}×{sum(1 for e in events if e[1]==k)}' for k in kinds)}) "
          f"loudness {cur:.1f}→{out_i:.1f} LUFS")
    return rec
