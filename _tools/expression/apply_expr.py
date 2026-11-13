#!/usr/bin/env python3
"""表現コード v1 を、stage.html／slide.html の「写し」に当てる（元のファイルは変えない）。

  python3 _tools/expression/apply_expr.py <元の html> <出力 html> --kind short|long --series "売れる仕組みの裏側" --no "#01" [--color "#E11D48"]

- </head> の直前に expr_v1_<kind>.css を差し込む
- 各スライドに、番組名の帯と進行バーを足す（ナレーションの対象外の要素）
- 西暦の .hi に ex-year を付ける（西暦は「数字の見せ場」に数えない）
台本（NARRATIONS）・STEPS・エンジンには触れない。
"""
import argparse
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--kind', choices=['short', 'long'], required=True)
    ap.add_argument('--series', required=True)
    ap.add_argument('--no', default='')
    ap.add_argument('--color', default='#E11D48')
    ap.add_argument('--visuals', help='visual_plan.json（映像意図。Shorts）')
    a = ap.parse_args()

    html = open(a.src, encoding='utf-8').read()
    css = open(os.path.join(HERE, f'expr_v1_{a.kind}.css'), encoding='utf-8').read()

    # スライドごとの開始・終了（SLIDES_META）→ 進行バーの区間
    meta = [(float(s), float(e)) for s, e in
            re.findall(r"\{\s*id:\s*'[^']+',\s*(?:title:\s*'[^']*',\s*)?start:\s*([\d.]+),\s*end:\s*([\d.]+)", html)]
    ids = re.findall(r'<section class="slide[^"]*" id="([^"]+)"', html)
    total = meta[-1][1] if meta else 1.0
    per = ''
    for i, sid in enumerate(ids):
        if i < len(meta):
            s, e = meta[i]
            per += f'#{sid}{{--p0:{s/total:.4f};--p1:{e/total:.4f};--sd:{e-s:.2f}s}}\n'
    css += f'\n:root{{--ex-series:{a.color};}}\n' + per

    first = ids[0] if ids else None
    if first:
        steps = re.findall(r"\{si:0,\s*t:([\d.]+),\s*ids:\[([^\]]*)\]", html)
        css += (f'#{first} .hi:not(.ex-year),#{first} .ex-num{{display:inline-block;'
                f'animation:exHit .30s .4s cubic-bezier(.2,.8,.2,1) both !important;}}\n')
        if a.kind == 'long':
            seen_num = False
            for t, idl in steps:
                for eid in re.findall(r"'([^']+)'", idl):
                    if seen_num and float(t) > 1.0:
                        css += f'#{eid}{{animation:exRise .30s {float(t) + 0.3:.2f}s cubic-bezier(.2,.8,.2,1) both !important;}}\n'
                    block = re.search(rf'id="{eid}"[^>]*>(.*?)</div>', html, re.S)
                    # 「数字＋単位」がある要素＝題名の数字。それより後の要素だけを、時間をずらして出す
                    if block and re.search(r'\d[\d,.]*\s*(?:%|％|倍|円|ドル|億|万|人|件|回|時間|か月|日|割)',
                                           re.sub(r'<[^>]+>', '', block.group(1))):
                        seen_num = True
    band = (f'<div class="ex-band">{a.series}<span class="ex-no">{a.no}</span></div>'
            f'<div class="ex-prog"><i></i></div>')
    html = re.sub(r'(<section class="slide[^"]*" id="[^"]+">)', lambda m: m.group(1) + band, html)
    html = re.sub(r'<span class="hi">(\d{4}年)</span>', r'<span class="hi ex-year">\1</span>', html)
    if a.kind == 'long':
        # 1枚目の大きな数字（インラインで accent 色が指定されている span）を「数字」として扱う
        html = re.sub(r'<span style="font-weight:900;line-height:1\.0;color:var\(--accent\);[^"]*">',
                      '<span class="ex-num">', html)
    if a.kind == 'long':
        # 最後のスライドに要素が無いとき（締めの語りだけの1枚）は、番組名のカードを出す
        m = list(re.finditer(r'<section class="slide[^"]*" id="[^"]+">(.*?)</section>', html, re.S))
        if m and 'class="se' not in m[-1].group(1) and 'se ' not in m[-1].group(1):
            end = f'<div class="ex-end">{a.series}<small>{a.no}</small></div>'
            html = html[:m[-1].end(1)] + end + html[m[-1].end(1):]
    if a.visuals:
        import json, shutil, sys
        sys.path.insert(0, HERE)
        import visuals
        plan = json.load(open(a.visuals, encoding='utf-8'))
        base = os.path.dirname(os.path.abspath(a.visuals))
        css += '\n' + open(os.path.join(HERE, 'expr_v1_visuals.css'), encoding='utf-8').read()
        for sid, pv in plan['slides'].items():
            if pv.get('type') == 'photo':     # 写真は台帳（assets.json）にあるものだけ
                led = {d['id']: d for d in json.load(open(os.path.join(base, 'assets', 'assets.json'), encoding='utf-8'))}
                assert pv['asset'] in led, f"台帳に無い素材: {pv['asset']}"
                import base64, subprocess
                small = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(base, led[pv['asset']]['file']),
                                        '-vf', 'scale=1280:-2', '-q:v', '4', '-f', 'mjpeg', '-'], capture_output=True, check=True).stdout
                pv['file'] = 'data:image/jpeg;base64,' + base64.b64encode(small).decode()
            if pv.get('reset') and sid in dict(zip(ids, meta)):
                s0, e0 = dict(zip(ids, meta))[sid]
                css += f'#{sid}{{--reset-at:{max(0.5, e0 - s0 - 1.0):.2f}s}}\n'
            block = visuals.render(sid, pv)
            html = re.sub(rf'(<section class="slide)([^"]*" id="{sid}">)', lambda m: m.group(1) + ' ex-hasvis' + m.group(2) + block, html, 1)
            css += visuals.sync_css(sid, pv)
    assert '</' not in css, 'CSS に閉じタグを書かない（録画用の HTML が壊れる）'
    assert '</head>' in html
    html = html.replace('</head>', f'<style id="expr-v1">\n{css}\n</style>\n</head>', 1)
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    open(a.dst, 'w', encoding='utf-8').write(html)
    print(f'{a.dst}: expr v1 ({a.kind}) スライド {len(ids)}枚')


if __name__ == '__main__':
    main()
