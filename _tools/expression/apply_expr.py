#!/usr/bin/env python3
"""表現コード v1 を、stage.html／slide.html の「写し」に当てる（元のファイルは変えない）。

  python3 _tools/expression/apply_expr.py <元の html> <出力 html> --plan <visual_plan.json> [--kind short|long]
                                          [--series 名前] [--no "#01"] [--color "#E11D48"]

やること：
  1. head の末尾に expr_v1_<kind>.css（色・文字・配置・動き）と expr_v1_visuals.css（図・写真）を差し込む
  2. 各スライドに、番組名の帯と進行バーを足す（ナレーションの対象外）
  3. visual_plan.json の型どおりに、図・写真を差し込む（写真は台帳 assets.json にあるものだけ）
  4. 西暦の .hi に ex-year を付ける（西暦は「数字の見せ場」に数えない）
台本（NARRATIONS）・STEPS・エンジン（keyframes・rv-*・.se・#__heartbeat）には触れない。
番組名・色・回の番号は、省略すると series.json とフォルダ名から決まる。
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
import visuals  # noqa: E402

NUM_UNIT = r'\d[\d,.]*\s*(?:%|％|倍|円|ドル|億|万|人|件|回|時間|か月|日|割)'


def series_of(path):
    """html のパス → (番組名, 色, 回の表記)。series.json の expression.series から引く。"""
    cfg = json.load(open(os.path.join(ROOT, 'series.json'), encoding='utf-8')).get('expression', {}).get('series', {})
    parts = os.path.abspath(path).split(os.sep)
    key = 's2_ura' if any(re.match(r'^[uc]\d+_', x) for x in parts) else 'default'
    s = cfg.get(key) or {'name': '', 'color': '#E11D48'}
    no = ''
    for x in parts:
        m = re.match(r'^([uc])(\d+)_', x) or re.match(r'^(ep)(\d+)_', x)
        if m:
            no = {'u': f'#{m.group(2)}', 'c': f'CASE FILE #{m.group(2)}', 'ep': f'第{int(m.group(2))}回'}[m.group(1)]
    return s['name'], s['color'], no


def slide_meta(html):
    meta = [(float(s), float(e)) for s, e in
            re.findall(r"\{\s*id:\s*'[^']+',\s*(?:title:\s*'[^']*',\s*)?start:\s*([\d.]+),\s*end:\s*([\d.]+)", html)]
    ids = re.findall(r'<section class="slide[^"]*" id="([^"]+)"', html)
    return ids, meta


def embed_photo(base, asset_id):
    pdir = os.path.join(ROOT, '_assets', 'photos')
    led = {d['id']: d for d in json.load(open(os.path.join(pdir, 'assets.json'), encoding='utf-8'))}
    assert asset_id in led, f'台帳（_assets/photos/assets.json）に無い素材: {asset_id}'
    small = subprocess.run(['ffmpeg', '-v', 'error', '-i', os.path.join(pdir, led[asset_id]['file']),
                            '-vf', 'scale=1280:-2', '-q:v', '4', '-f', 'mjpeg', '-'], capture_output=True, check=True).stdout
    return 'data:image/jpeg;base64,' + base64.b64encode(small).decode()


FIT_JS = r"""
() => {
  const out = [];
  document.querySelectorAll('section.slide').forEach(sec => {
    document.querySelectorAll('section.slide').forEach(x => x.style.display = (x === sec ? 'flex' : 'none'));
    sec.querySelectorAll('.k-line').forEach(e => {
      const fs = parseFloat(getComputedStyle(e).fontSize), lh = fs * 0.6;
      const rg = document.createRange(); rg.selectNodeContents(e);
      const cs = [];
      [...rg.getClientRects()].filter(q => q.width > 1).forEach(q => {
        const c = (q.top + q.bottom) / 2; if (!cs.some(v => Math.abs(v - c) < lh)) cs.push(c);
      });
      const want = e.querySelectorAll('br').length + 1;
      if (e.id && cs.length > want) out.push([e.id, fs, cs.length, want]);
    });
  });
  return out;
}
"""


def fit_telop(path, floor=64, step=4):
    """数字を大きくした結果、テロップが <br> 以外で折り返したら、その行だけ文字を小さくする（64px まで）。
    テロップ同期のルール（画面の文＝ナレーション・<br> 以外で折り返さない）を守るため。"""
    from playwright.sync_api import sync_playwright
    fixed = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={'width': 1080, 'height': 1920})
        for _ in range(8):
            pg.goto('file://' + os.path.abspath(path)); pg.wait_for_timeout(400)
            bad = pg.evaluate(FIT_JS)
            if not bad:
                break
            html = open(path, encoding='utf-8').read()
            for eid, fs, got, want in bad:
                nfs = fs - step
                if nfs < floor:
                    b.close()
                    sys.exit(f'FAIL: テロップ {eid} が {floor}px でも折り返す（{got}行/{want}行）。台本の改行（<br>）を見直す')
                fixed[eid] = nfs
                rule = f'#{eid}{{font-size:{nfs:.0f}px !important}}'
                html = re.sub(rf'#{eid}\{{font-size:[\d.]+px !important\}}\n?', '', html)
                html = html.replace('</style>\n</head>', rule + '\n</style>\n</head>', 1)
            open(path, 'w', encoding='utf-8').write(html)
        b.close()
    for eid, v in fixed.items():
        print(f'  テロップ {eid}：数字を大きくして折り返したので {v:.0f}px に下げた')


def apply(src, dst, plan_path, kind=None, series=None, no=None, color=None):
    html = open(src, encoding='utf-8').read()
    plan = json.load(open(plan_path, encoding='utf-8')) if plan_path else {'slides': {}}
    kind = kind or plan.get('kind') or ('short' if 'SHORTS_STAGE_START' in html else 'long')
    s_name, s_color, s_no = series_of(src if not plan_path else plan_path)
    series, color, no = series or s_name, color or s_color, (no if no is not None else plan.get('band_no', s_no))
    base = os.path.dirname(os.path.abspath(plan_path)) if plan_path else None

    css = open(os.path.join(HERE, f'expr_v1_{kind}.css'), encoding='utf-8').read()
    css += '\n' + open(os.path.join(HERE, 'expr_v1_visuals.css'), encoding='utf-8').read()
    ids, meta = slide_meta(html)
    total = meta[-1][1] if meta else 1.0
    css += f'\n:root{{--ex-series:{color};}}\n'
    for i, sid in enumerate(ids):
        if i < len(meta):
            s, e = meta[i]
            css += f'#{sid}{{--p0:{s/total:.4f};--p1:{e/total:.4f};--sd:{e-s:.2f}s}}\n'

    # 1枚目：録画エンジンは最初から全部を完成形で出す。数字の着地と、2つめ以降の要素の出現を CSS の時間で作る
    first = ids[0] if ids else None
    if first:
        # 1枚目の映像の枠は、0秒から出しておく（Shorts のくり返しで、最後のコマ＝最初のコマにするため。枠のフェードインは継ぎ目のちらつきになる）
        css += f'#{first} .ex-vis{{animation:none;opacity:1}}\n'
        css += (f'#{first} .hi:not(.ex-year),#{first} .ex-num{{display:inline-block;transform-origin:center;'
                f'animation:exHit0 .30s .45s cubic-bezier(.2,.8,.2,1) both !important;}}\n')
        if kind == 'long':
            seen_num = False
            for t, idl in re.findall(r"\{si:0,\s*t:([\d.]+),\s*ids:\[([^\]]*)\]", html):
                for eid in re.findall(r"'([^']+)'", idl):
                    if seen_num and float(t) > 1.0:
                        css += f'#{eid}{{animation:exRise .30s {float(t) + 0.3:.2f}s cubic-bezier(.2,.8,.2,1) both !important;}}\n'
                    block = re.search(rf'id="{eid}"[^>]*>(.*?)</div>', html, re.S)
                    # 「数字＋単位」がある要素＝題名の数字。それより後の要素だけを、時間をずらして出す
                    if block and re.search(NUM_UNIT, re.sub(r'<[^>]+>', '', block.group(1))):
                        seen_num = True

    band = (f'<div class="ex-band">{series}<span class="ex-no">{no}</span></div>'
            f'<div class="ex-prog"><i></i></div>')
    html = re.sub(r'(<section class="slide[^"]*" id="[^"]+">)', lambda m: m.group(1) + band, html)
    html = re.sub(r'<span class="hi">(\d{4}年)</span>', r'<span class="hi ex-year">\1</span>', html)

    if kind == 'long':
        # 1枚目の大きな数字（インラインで accent 色が指定されている span）を「数字」として扱う
        html = re.sub(r'<span style="font-weight:900;line-height:1\.0;color:var\(--accent\);[^"]*">',
                      '<span class="ex-num">', html)
        # 最後のスライドに要素が無いとき（締めの語りだけの1枚）は、番組名のカードを出す
        m = list(re.finditer(r'<section class="slide[^"]*" id="[^"]+">(.*?)</section>', html, re.S))
        if m and 'class="se' not in m[-1].group(1) and ' se ' not in m[-1].group(1):
            end = f'<div class="ex-end">{series}<small>{no}</small></div>'
            html = html[:m[-1].end(1)] + end + html[m[-1].end(1):]

    span = dict(zip(ids, meta))
    for sid, pv in plan.get('slides', {}).items():
        pv = dict(pv)
        t = pv.get('type', 'none')
        if t == 'none':
            continue
        if t == 'photo':
            pv['file'] = embed_photo(base, pv['asset'])
        if pv.get('reset') and sid in span:
            css += f'#{sid}{{--reset-at:{max(0.5, span[sid][1] - span[sid][0] - 1.0):.2f}s}}\n'
        css += visuals.sync_css(sid, pv)
        if kind == 'long' and t == 'bar_cells':
            # 既にある数字のカードの下に、値の大きさの棒を足す（同じ単位の数字だけ）
            vals = [float(v) for v in pv['values']]
            mx = max(vals)
            sec = re.search(rf'(<section class="slide[^"]*" id="{sid}">)(.*?)(</section>)', html, re.S)
            it = iter(vals)
            body = re.sub(r'(<span class="jv[^"]*"[^>]*>[^<]*</span>)',
                          lambda mm: mm.group(1) + f'<i class="ex-cellbar" style="--w:{next(it)/mx:.3f}"></i>', sec.group(2), len(vals))
            html = html[:sec.start(2)] + body + html[sec.end(2):]
            continue
        block = visuals.render(sid, pv)
        if kind == 'long':      # 長尺：絵は文字の後ろ（背景の層）に置く。配置は変えない
            block = block.replace('class="ex-vis ', 'class="ex-bg ' + ('ex-bg-end ' if sid == ids[-1] else ''), 1)
            html = re.sub(rf'(<section class="slide[^"]*" id="{sid}">)', lambda m: m.group(1) + block, html, 1)
        else:
            html = re.sub(rf'(<section class="slide)([^"]*" id="{sid}">)',
                          lambda m: m.group(1) + ' ex-hasvis' + m.group(2) + block, html, 1)

    assert '</' not in css, 'CSS に閉じタグを書かない（録画用の HTML が壊れる）'
    assert '</head>' in html
    html = html.replace('</head>', f'<style id="expr-v1">\n{css}\n</style>\n</head>', 1)
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    open(dst, 'w', encoding='utf-8').write(html)
    if kind == 'short':
        fit_telop(dst)
    print(f'{dst}: expr v1 ({kind}) スライド {len(ids)}枚・映像 {sum(1 for v in plan.get("slides", {}).values() if v.get("type", "none") != "none")}枚')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--plan', '--visuals', dest='plan')
    ap.add_argument('--kind', choices=['short', 'long'])
    ap.add_argument('--series'); ap.add_argument('--no'); ap.add_argument('--color')
    a = ap.parse_args()
    apply(a.src, a.dst, a.plan, a.kind, a.series, a.no, a.color)


if __name__ == '__main__':
    main()
