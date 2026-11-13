#!/usr/bin/env python3
"""visual_plan.json（映像意図）の機械検査。ビルドの前に run_shorts.sh／run_episode.sh が呼ぶ。

  python3 _tools/expression/check_visual_plan.py <stage.html|slide.html> <visual_plan.json>

合格の条件（表現コード v1 §8。番号は P1〜P9）：
  P1 全スライドに型（type）と意図（intent。10字以上）がある。型は visuals.TYPES にあり、その形式（Shorts／長尺）で使える
  P2 Shorts は全スライドに絵がある（none は使えない）。長尺は、絵のあるスライドが半分以上
  P3 絵のあるスライドのうち、自作の図解が半分以上（写真だけで作らない）。Shorts の写真は2枚まで
  P4 写真は _assets/photos/assets.json にあり、ライセンスが CC0／Public domain／CC BY。docs/expression/license-ledger.md にも載っている
  P5 図に出す数字・文字（value・n・a・b・a_text・b_text・year・stamp・values）は、そのスライドのナレーションか画面の文字にある
     （compare_bars だけは、1つ前のスライドの数字も使える。比べる相手が前のスライドに出ていることが多いため）
  P6 図に出すラベル（before_label・after_label・a_label・b_label）は、動画全体のナレーションにある語
  P7 sync の要素が、そのスライドにある（STEPS の ids）
  P8 Shorts：最後のスライドは、1枚目と同じ型・同じ値で reset=true（冒頭と同じ絵で終わる）
  P9 answer（答えの文）が、画面の文字にある。answer_narration（省略時は answer）がナレーションにある
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, '_tools', 'video'))
import visuals  # noqa: E402

OK_LIC = re.compile(r'^(CC0|Public domain|PD\b|CC BY( \d|$))')
Z2H = str.maketrans('０１２３４５６７８９．，％', '0123456789.,%')


def norm(s):
    return re.sub(r'[\s、。，,！？!?「」『』・]', '', str(s).translate(Z2H))


def load(html_path):
    import make_video as mv
    sd = mv.extract_slide_data(html_path)
    src = open(html_path, encoding='utf-8').read()
    ids = [m.id for m in sd.meta]
    steps = {}
    for si, idl in re.findall(r"\{si:(\d+),\s*t:[\d.]+,\s*ids:\[([^\]]*)\]", src):
        steps.setdefault(ids[int(si)], []).extend(re.findall(r"'([^']+)'", idl))
    screen = {}
    for sid in ids:
        m = re.search(rf'<section class="slide[^"]*" id="{sid}">(.*?)</section>', src, re.S)
        screen[sid] = re.sub(r'<[^>]+>', '', m.group(1)) if m else ''
    kind = 'short' if 'SHORTS_STAGE_START' in src else 'long'
    return ids, dict(zip(ids, sd.narrations)), steps, screen, kind


def check(html_path, plan_path):
    errs = []
    ids, narr, steps, screen, kind = load(html_path)
    plan = json.load(open(plan_path, encoding='utf-8'))
    sl = plan.get('slides', {})
    allnarr = norm(''.join(narr.values()))
    base = os.path.dirname(os.path.abspath(plan_path))
    col = 2 if kind == 'short' else 3
    with_vis, selfmade = 0, 0
    for sid in ids:
        p = sl.get(sid)
        if not p:
            errs.append(f'P1 {sid}: 型が無い'); continue
        t = p.get('type')
        if t not in visuals.TYPES:
            errs.append(f'P1 {sid}: 型「{t}」は無い（使える型：{"・".join(k for k, v in visuals.TYPES.items() if v[col])}）'); continue
        if not visuals.TYPES[t][col]:
            errs.append(f'P1 {sid}: 型「{t}」は{"Shorts" if kind == "short" else "長尺"}では使えない')
        if len(p.get('intent', '')) < 10:
            errs.append(f'P1 {sid}: intent（なぜその絵か）を10字以上で書く')
        if t == 'none':
            if kind == 'short':
                errs.append(f'P2 {sid}: Shorts は全スライドに絵が要る（none は使えない）')
            continue
        with_vis += 1
        selfmade += 1 if visuals.TYPES[t][1] else 0
        hay = norm(narr[sid]) + norm(screen[sid])
        if p.get('reset') and kind == 'short':      # 締めの1枚は、1枚目の絵をそのまま戻す（P8 が同じ値かを見る）
            hay += norm(narr[ids[0]]) + norm(screen[ids[0]])
        i = ids.index(sid)
        if t == 'compare_bars' and i > 0:          # 比べる相手が「1つ前のスライド」の数字のとき（例：前の1.5ドル ↔ 今の4.6ドル）
            hay += norm(narr[ids[i - 1]]) + norm(screen[ids[i - 1]])
        for k in ('value', 'n', 'a', 'b', 'year', 'stamp', 'a_text', 'b_text'):
            if k in p:
                v = norm(p[k]); v = v[:-2] if v.endswith('.0') else v
                if v not in hay:
                    errs.append(f'P5 {sid}: {k}＝{p[k]} が、このスライドのナレーション・画面に無い')
        for v in p.get('values', []):
            v = norm(v); v = v[:-2] if v.endswith('.0') else v
            if v not in hay:
                errs.append(f'P5 {sid}: values の {v} が、このスライドに無い')
        for k in ('before_label', 'after_label', 'a_label', 'b_label'):
            if k in p and norm(p[k]) not in allnarr:
                errs.append(f'P6 {sid}: {k}＝「{p[k]}」が、ナレーションに無い語')
        if p.get('sync') and p['sync'] not in steps.get(sid, []):
            errs.append(f'P7 {sid}: sync＝{p["sync"]} が、このスライドの要素に無い（あるのは {steps.get(sid, [])}）')
        if t == 'photo':
            base = os.path.join(ROOT, '_assets', 'photos')
            aj = os.path.join(base, 'assets.json')
            led = {d['id']: d for d in json.load(open(aj, encoding='utf-8'))} if os.path.exists(aj) else {}
            a = led.get(p.get('asset'))
            if not a:
                errs.append(f'P4 {sid}: 写真 {p.get("asset")} が _assets/photos/assets.json に無い（fetch_assets.py で取得する）')
            else:
                if not OK_LIC.match(a.get('license', '')) or re.search(r'SA|NC|ND', a.get('license', '')):
                    errs.append(f'P4 {sid}: ライセンス「{a.get("license")}」は使えない')
                if not os.path.exists(os.path.join(base, a['file'])):
                    errs.append(f'P4 {sid}: 写真のファイルが無い {a["file"]}')
                ledger = open(os.path.join(ROOT, 'docs', 'expression', 'license-ledger.md'), encoding='utf-8').read()
                if a.get('page', '') not in ledger:
                    errs.append(f'P4 {sid}: 写真が license-ledger.md に載っていない')
    for sid in sl:
        if sid not in ids:
            errs.append(f'P1 {sid}: そのスライドは無い')
    if kind == 'long' and with_vis * 2 < len(ids):
        errs.append(f'P2 絵のあるスライドが {with_vis}/{len(ids)} 枚（半分以上にする）')
    if kind == 'short' and with_vis - selfmade > 2:
        errs.append(f'P3 写真が {with_vis - selfmade} 枚（Shorts は2枚まで）')
    if with_vis and selfmade * 2 < with_vis:
        errs.append(f'P3 自作の図解が {selfmade}/{with_vis} 枚（半分以上にする）')
    if kind == 'short' and len(ids) >= 2 and ids[0] in sl and ids[-1] in sl:
        a, b = sl[ids[0]], sl[ids[-1]]
        same = all(a.get(k) == b.get(k) for k in set(a) | set(b) if k not in ('intent', 'reset', 'sync'))
        if not (same and b.get('reset') is True):
            errs.append('P8 最後のスライドは、1枚目と同じ型・同じ値にして reset=true を付ける')
    ans = plan.get('answer', '')
    if not ans or norm(ans) not in norm(''.join(screen.values())):
        errs.append(f'P9 answer「{ans}」が画面の文字に無い')
    an = plan.get('answer_narration', ans)
    if not an or norm(an) not in allnarr:
        errs.append(f'P9 answer_narration「{an}」がナレーションに無い')
    return errs, kind, with_vis, len(ids)


def main():
    errs, kind, n, tot = check(sys.argv[1], sys.argv[2])
    print(f'== 映像意図の検査（{kind}・絵 {n}/{tot} 枚）')
    for e in errs:
        print('  FAIL', e)
    print('結果：' + ('PASS' if not errs else f'FAIL（{len(errs)}件）'))
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())
