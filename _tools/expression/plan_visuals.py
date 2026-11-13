#!/usr/bin/env python3
"""映像意図の下書きを作る（決まった規則で。仕上げは人か AI が行い、check_visual_plan.py を通す）。

  python3 _tools/expression/plan_visuals.py <stage.html|slide.html> <出力 visual_plan.json>

規則（上から順に当てる。当たらなければ type="TODO" のままにして、検査で止める）：
  Shorts
    「N%」＋減・下・落 → chart_drop（増・上・伸 なら direction=up）
    「N回・件・人・店・個・社」で N が 1000 以下 → dot_grid
    同じ単位の数字が2つ → compare_bars
    固有名詞（docs/proper-nouns.md の企業・店・商品・地名）→ photo（asset は TODO。fetch_assets.py で取得して書く）
    西暦だけ → timeline
    「なぜ・？」→ question／「」の引用 → quote／セール・値引き・定価・割引 → tag_strike
    最後の1枚 → 1枚目と同じ型＋reset=true
  長尺
    数字のカード（.jcell）が2つ以上で同じ単位 → bar_cells
    「N回・件…」→ dot_grid（背景）／固有名詞 → photo（背景）／それ以外 → none
answer（答えの文）は、Shorts は最後のスライドの最初の要素、長尺は「まとめ」のスライドの最初の本文を入れる。必ず目で確かめる。
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_visual_plan as C  # noqa: E402

UNIT_CNT = r'(回|件|人|店|個|社)'


def nouns():
    out = []
    p = os.path.join(C.ROOT, 'docs', 'proper-nouns.md')
    for line in open(p, encoding='utf-8'):
        c = [x.strip() for x in line.split('|')]
        if len(c) > 4 and c[1] and c[3] and not c[3].startswith('人名') and c[1] != '表記' and not set(c[1]) <= set('-: '):
            out.append(c[1])
    return sorted(set(out), key=len, reverse=True)


def first_text(src, eid):
    m = re.search(rf'id="{eid}"[^>]*>(.*?)</div>', src, re.S)
    return re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else ''


def draft(html_path):
    ids, narr, steps, screen, kind = C.load(html_path)
    src = open(html_path, encoding='utf-8').read()
    NN = nouns()
    slides = {}
    for i, sid in enumerate(ids):
        t = narr[sid].translate(C.Z2H)
        st = steps.get(sid, [])
        sync = next((e for e in st if re.search(r'\d', first_text(src, e))), st[0] if st else None)
        p = None
        pct = re.search(r'(\d[\d.]*)\s*(?:%|パーセント)', t)
        cnt = re.search(r'(\d[\d,]*)\s*' + UNIT_CNT, t)
        noun = next((n for n in NN if n in narr[sid]), None)
        if kind == 'short':
            if pct and re.search(r'減|下が|落ち|増|上が|伸び', t):
                p = {'type': 'chart_drop', 'value': float(pct.group(1)), 'before_label': 'TODO', 'after_label': 'TODO',
                     'intent': f'図解＋数字の強調：{pct.group(0)} の変化を棒で見せる'}
                if re.search(r'増え|増や|伸び|上がっ|上げ', t) and not re.search(r'減|下が|落ち', t):
                    p['direction'] = 'up'
            elif cnt and int(cnt.group(1).replace(',', '')) <= 1000:
                p = {'type': 'dot_grid', 'n': int(cnt.group(1).replace(',', '')), 'intent': f'図解＋数字の強調：{cnt.group(0)} を点の数で見せる'}
            elif noun:
                p = {'type': 'photo', 'asset': 'TODO', 'intent': f'実写イメージ：{noun}（固有名詞に同期）'}
            elif re.search(r'(19|20)\d{2}年', t):
                p = {'type': 'timeline', 'year': re.search(r'((19|20)\d{2})年', t).group(1), 'intent': '図解：いつの話かを年表で示す'}
            elif re.search(r'セール|値引|定価|割引|値下げ', t):
                p = {'type': 'tag_strike', 'intent': '図解：値札と取り消し線で、値段の見せかたを示す'}
            elif re.search(r'なぜ|？|\?', t):
                p = {'type': 'question', 'intent': '図解：問いのスライド。疑問符を描く'}
            elif '「' in narr[sid]:
                p = {'type': 'quote', 'intent': '図解：発言の引用。かぎかっこを描く'}
        else:
            cells = re.findall(r'class="jv[^"]*"[^>]*>([^<]*)<', re.search(rf'id="{sid}">(.*?)</section>', src, re.S).group(1))
            units = [re.sub(r'[\d.,−\-+ ]', '', c) for c in cells]
            if len(cells) >= 2 and len(set(units)) == 1:
                p = {'type': 'bar_cells', 'values': [float(re.search(r'[\d.]+', c.replace(',', '')).group(0)) for c in cells],
                     'intent': f'数字のカードの下に棒を足して、{"と".join(cells)} の差を見せる'}
            elif cnt and int(cnt.group(1).replace(',', '')) <= 1000:
                p = {'type': 'dot_grid', 'n': int(cnt.group(1).replace(',', '')), 'strike': False, 'intent': f'背景に {cnt.group(0)} ぶんの点を並べる'}
            elif noun:
                p = {'type': 'photo', 'asset': 'TODO', 'intent': f'背景に実写：{noun}'}
            else:
                p = {'type': 'none', 'intent': 'TODO：絵を足さない理由を書く（絵のあるスライドは半分以上）'}
        if p is None:
            p = {'type': 'TODO', 'intent': 'TODO：型を選ぶ（yt-expression スキルの表）'}
        if sync and p['type'] not in ('none', 'TODO', 'bar_cells') and i > 0:
            p['sync'] = sync
        slides[sid] = p
    if kind == 'short' and len(ids) >= 2:
        last = dict(slides[ids[0]]); last.pop('sync', None); last['reset'] = True
        last['intent'] = '答え。冒頭と同じ絵に戻して、くり返しの継ぎ目をつなぐ'
        slides[ids[-1]] = last
        ans = first_text(src, (steps.get(ids[-1]) or [''])[0])
    else:
        sid = next((s for s in ids if 'まとめ' in screen[s]), ids[-2] if len(ids) > 1 else ids[0])
        st = steps.get(sid, [])
        ans = first_text(src, st[1] if len(st) > 1 else (st[0] if st else ''))
    return {'_note': '映像意図。plan_visuals.py の下書き → TODO を埋める → check_visual_plan.py を通す。数字・文字は台本にあるものだけ。',
            'version': 'v1', 'kind': kind, 'answer': re.sub(r'\s+', '', ans), 'slides': slides}


def main():
    d = draft(sys.argv[1])
    if os.path.exists(sys.argv[2]) and '--force' not in sys.argv:
        sys.exit(f'{sys.argv[2]} は既にある（上書きは --force）')
    json.dump(d, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    todo = json.dumps(d, ensure_ascii=False).count('TODO')
    print(f'{sys.argv[2]}：下書き（{d["kind"]}・{len(d["slides"])}枚・TODO {todo}か所）')


if __name__ == '__main__':
    main()
