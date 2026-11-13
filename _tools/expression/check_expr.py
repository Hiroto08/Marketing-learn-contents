#!/usr/bin/env python3
"""表現コード v1 の合否検査（docs/expression/expression-code.md の番号と対応）。

  python3 _tools/expression/check_expr.py <final.mp4> [--html <stage.html|slide.html>] [--json]

測るもの（動画から）：
  S1 統合ラウドネス −14.0±0.5 LUFS      S2 トゥルーピーク −1.0dBTP 以下
  S3 冒頭 0.0〜0.3秒に音がある（−30dB 以上）   S4 声のある所と間の音量差 10〜20dB
  S5 明瞭さの帯域（3〜6kHz）が全体比 −14dB 以上  S6 効果音の本数・間隔（expr_mix.json があれば）
  S7 Shorts：末尾0.5秒が −35dB 以上（くり返し再生のつなぎ目に無音の谷を作らない）
  V4 Shorts（--plan があるとき）：最初のコマと最後のコマの絵が同じ（差 6.0 以下）
  M1 最初の動きが 2.0秒以内               M2 動きの無い時間の最長：長尺 12秒・Shorts 3秒 以内
測るもの（--html があれば、画面の要素から）：
  D1 文字の最小：長尺 42px・Shorts 48px（書き出し解像度で）
  D2 数字は、同じ画面の本文の 1.3 倍以上
旧来のビルド（--expr なし）にも当てられる。その場合は「現状の測定」として使う（不合格でもビルドは止めない）。
"""
import argparse
import json
import os
import re
import subprocess
import sys

import numpy as np

SR = 24000


def _pcm(f):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def _rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) if len(x) else -120.0


def _ebur(f):
    o = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', f, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    t = o[o.rfind('Summary'):]
    g = lambda k: float(re.search(k + r':\s*(-?[\d.]+)', t).group(1))
    return g('I'), g('LRA'), g('Peak')


def _frames(f, w, h, fps=4):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-vf', f'fps={fps},scale={w}:{h}', '-pix_fmt', 'gray',
                          '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(-1, h, w).astype(np.int16)


def measure(mp4):
    v = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                        '-of', 'csv=p=0', mp4], capture_output=True, text=True).stdout.strip().split(',')
    W, H = int(v[0]), int(v[1])
    vertical = H > W
    x = _pcm(mp4)
    I, LRA, TP = _ebur(mp4)
    n = int(0.05 * SR)
    m = len(x) // n
    r = 20 * np.log10(np.sqrt((x[:m * n].reshape(m, n) ** 2).mean(1)) + 1e-9)
    quiet = r < np.percentile(r, 50) - 6
    segs, s = [], None
    for i, q in enumerate(list(quiet) + [False]):
        if q and s is None:
            s = i
        if not q and s is not None:
            if i - s >= 5 and s * 0.05 > 0.6 and i * 0.05 < len(x) / SR - 1.5:
                segs.append(r[s:i].mean())
            s = None
    gap = float(r[~quiet].mean() - np.mean(segs)) if segs else float('nan')
    X = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    clarity = float(10 * np.log10(X[(fr >= 3000) & (fr < 6000)].sum() / X.sum() + 1e-12))
    head3 = _rms_db(x[:int(0.3 * SR)])
    head5, tail5 = _rms_db(x[:int(0.5 * SR)]), _rms_db(x[-int(0.5 * SR):])

    # 動き：進行バー（飾りでなく情報だが、動きの判定からは外す）を除いて測る
    w, h = (180, 320) if vertical else (320, 180)
    f = _frames(mp4, w, h)
    if vertical:
        f = np.concatenate([f[:, :int(h * 0.775)], f[:, int(h * 0.80):]], axis=1)
    else:
        f = f[:, :int(h * 0.975)]
    # 「動いた」＝明るさが 12 以上変わった画素が、画面の 0.15% 以上（圧縮のゆらぎは数えない）
    d = (np.abs(np.diff(f, axis=0)) > 12).mean((1, 2))
    moving = d >= 0.0015
    first = next((i for i, mv in enumerate(moving) if mv), None)
    run = mx = 0
    for mv in moving:
        run = 0 if mv else run + 1
        mx = max(mx, run)
    # ループの継ぎ目（Shorts）：映像の枠（帯の下〜文字の上）の、最初のコマと最後のコマの差
    seam = None
    if vertical:
        def one(args):
            raw = subprocess.run(['ffmpeg', '-v', 'error', *args, '-i', mp4, '-frames:v', '1', '-vf', 'scale=180:320',
                                  '-pix_fmt', 'gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
            return np.frombuffer(raw, dtype=np.uint8).reshape(320, 180).astype(np.int16)[48:126]
        seam = float(np.abs(one(['-ss', '0.05']) - one(['-sseof', '-0.08'])).mean())
    return {'vertical': vertical, 'dur': round(len(x) / SR, 2), 'seam_diff': None if seam is None else round(seam, 1),
            'I': I, 'LRA': LRA, 'TP': TP, 'head_0_3': round(head3, 1), 'voice_minus_gap': round(gap, 1),
            'clarity_3_6k': round(clarity, 1), 'head_0_5': round(head5, 1), 'tail_0_5': round(tail5, 1),
            'first_motion': None if first is None else round((first + 1) / 4, 2),
            'longest_still': round(mx / 4, 2)}


def check_html(html, vertical):
    """画面の要素の文字サイズを、書き出し解像度に直して調べる（Playwright）。"""
    js = r"""
const {chromium}=require('playwright');
(async()=>{const [,,html,w,h]=process.argv;const b=await chromium.launch();
const p=await b.newPage({viewport:{width:+w,height:+h}});await p.goto('file://'+html);await p.waitForTimeout(1200);
const out=await p.evaluate(()=>{const res=[];document.querySelectorAll('section.slide').forEach(s=>{
 document.querySelectorAll('section.slide').forEach(x=>x.classList.toggle('active',x===s));
 let min=1e9,minTxt='',num=0,body=0;
 const walk=document.createTreeWalker(s,NodeFilter.SHOW_TEXT);
 while(walk.nextNode()){const t=walk.currentNode;const txt=t.textContent.trim();if(!txt)continue;
  const e=t.parentElement;const cs=getComputedStyle(e);if(cs.display==='none'||e.closest('[style*="display:none"]'))continue;
  let hidden=false;for(let a=e;a&&a!==s;a=a.parentElement){if(getComputedStyle(a).display==='none'){hidden=true;break;}}
  if(hidden)continue;
  const fs=parseFloat(cs.fontSize);if(fs<min){min=fs;minTxt=txt.slice(0,14);}
  const isNum=e.matches('.hi:not(.ex-year),.jv,b.c-accent,.ex-num,.k-num,.ex-delta')&&/\d/.test(txt);
  if(isNum)num=Math.max(num,fs);else if(!e.closest('.ex-band,.ex-end,.ex-vis'))body=Math.max(body,fs);}
 res.push({id:s.id,min:min===1e9?null:min,minTxt,num,body});});return res;});
console.log(JSON.stringify(out));await b.close();})();
"""
    w, h, scale = (1080, 1920, 1.0) if vertical else (1280, 720, 1.5)
    tmp = os.path.join(os.path.dirname(os.path.abspath(html)), '.check_expr.js')
    open(tmp, 'w').write(js)
    try:
        out = subprocess.run(['node', tmp, os.path.abspath(html), str(w), str(h)], capture_output=True, text=True)
        rows = json.loads(out.stdout.strip().splitlines()[-1])
    finally:
        os.remove(tmp)
    for r in rows:
        for k in ('min', 'num', 'body'):
            if r[k]:
                r[k] = round(r[k] * scale, 1)
    return rows


def judge(m, mix=None, html_rows=None, has_plan=False):
    v = m['vertical']
    res = []
    add = lambda code, ok, text: res.append((code, bool(ok), text))
    add('S1', abs(m['I'] + 14.0) <= 0.5, f"統合ラウドネス {m['I']:.1f} LUFS（基準 −14.0±0.5）")
    add('S2', m['TP'] <= -1.0, f"トゥルーピーク {m['TP']:.1f} dBTP（基準 −1.0 以下）")
    add('S3', m['head_0_3'] >= -30, f"冒頭0.3秒の音量 {m['head_0_3']:.1f} dB（基準 −30 以上）")
    add('S4', 10 <= m['voice_minus_gap'] <= 20, f"声のある所−間 {m['voice_minus_gap']:.1f} dB（基準 10〜20）")
    add('S5', m['clarity_3_6k'] >= -14, f"3〜6kHz の比率 {m['clarity_3_6k']:.1f} dB（基準 −14 以上）")
    if mix is not None:
        ev = mix['events']
        cap = 5 if v else max(6, int(mix['total'] / 10))
        gaps = [b[0] - a[0] for a, b in zip(ev, ev[1:])]
        add('S6', len(ev) <= cap and (not gaps or min(gaps) >= 1.5) and ev and ev[0] == [0.0, 'question'],
            f"効果音 {len(ev)}個（上限 {cap}）・最小間隔 {min(gaps) if gaps else 0:.1f}秒（基準 1.5 以上）・0.0秒に問いの音")
    else:
        add('S6', False, '効果音の記録（expr_mix.json）が無い＝意味に対応した効果音ではない')
    if v:
        add('S7', m['tail_0_5'] >= -35,
            f"つなぎ目：末尾0.5秒 {m['tail_0_5']:.1f} dB（基準 −35 以上＝無音の谷を作らない）")
    add('M1', m['first_motion'] is not None and m['first_motion'] <= 2.0, f"最初の動き {m['first_motion']}秒（基準 2.0 以内）")
    lim = 3.0 if v else 12.0
    add('M2', m['longest_still'] <= lim, f"動きの無い時間の最長 {m['longest_still']}秒（基準 {lim:.0f} 以内）")
    if v and has_plan:
        add('V4', m['seam_diff'] is not None and m['seam_diff'] <= 6.0,
            f"ループの継ぎ目の絵：最初と最後のコマの差 {m['seam_diff']}（基準 6.0 以下＝同じ絵で終わる）")
    if html_rows is not None:
        floor = 48 if v else 42
        mins = [(r['min'], r['id'], r['minTxt']) for r in html_rows if r['min']]
        lo = min(mins) if mins else (0, '', '')
        add('D1', lo[0] >= floor, f"文字の最小 {lo[0]}px（{lo[1]}「{lo[2]}」。基準 {floor} 以上）")
        bad = [f"{r['id']}（数字 {r['num']}／本文 {r['body']}）" for r in html_rows
               if r['num'] and r['body'] and r['num'] < 1.3 * r['body'] - 0.5]
        withnum = sum(1 for r in html_rows if r['num'])
        add('D2', withnum > 0 and not bad, f"数字が本文の1.3倍以上：数字のある {withnum}枚のうち不合格 {len(bad)}枚 {' '.join(bad[:4])}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mp4')
    ap.add_argument('--html')
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--plan', help='visual_plan.json（あれば、ループの継ぎ目の絵 V4 も検査する）')
    ap.add_argument('--record', help='結果を JSON で書き出す（quality_record.py が読む。コミットする）')
    a = ap.parse_args()
    m = measure(a.mp4)
    mixp = os.path.join(os.path.dirname(a.mp4), 'expr_mix.json')
    mix = json.load(open(mixp, encoding='utf-8')) if os.path.exists(mixp) else None
    rows = check_html(a.html, m['vertical']) if a.html else None
    res = judge(m, mix, rows, has_plan=bool(a.plan))
    if a.record:
        json.dump({'video': os.path.basename(a.mp4), 'measure': m, 'mix': mix,
                   'result': [{'code': c, 'ok': o, 'text': t} for c, o, t in res],
                   'pass': all(o for _, o, _ in res)}, open(a.record, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=float)
    if a.json:
        print(json.dumps({'measure': m, 'result': res}, ensure_ascii=False, default=float))
    else:
        print(f"== 表現コード v1 検査：{os.path.basename(a.mp4)}（{m['dur']}秒・{'Shorts' if m['vertical'] else '長尺'}）")
        for code, ok, text in res:
            print(f"  {'PASS' if ok else 'FAIL'} {code} {text}")
        print('結果：' + ('PASS' if all(ok for _, ok, _ in res) else 'FAIL'))
    return 0 if all(ok for _, ok, _ in res) else 1


if __name__ == '__main__':
    sys.exit(main())
