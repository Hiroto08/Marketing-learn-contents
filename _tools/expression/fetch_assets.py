#!/usr/bin/env python3
"""ライセンスが明確な写真だけを取得し、ライセンス台帳に自動で追記する。

  python3 _tools/expression/fetch_assets.py <回のフォルダ> --id <素材ID> --query "<英語の検索語>" [--title "File:..."] [--min-width 1600]
  python3 _tools/expression/fetch_assets.py <回のフォルダ> --id <素材ID> --drop     # 見て使わないと決めた写真を消す
    候補の一覧（○＝条件を満たす）が出る。最初の○を取るので、目で見て合わなければ --drop して --title で選び直す
    検索語に haslicense:unrestricted を足すと CC0／PD だけになる。
    同じ素材ID が既にあれば、取得せずに「使う回」だけを足す（同じ写真を別の回でも使える）

- 取得元：Wikimedia Commons の API（キー不要）。**使ってよいライセンスは CC0／Public domain／CC BY だけ**。
  CC BY-SA・NC・ND・ライセンス不明は取得しない。ロゴ・人物の肖像・作品の切り抜き（映画・テレビ・アニメ）は除外する。
- 解像度：元画像の幅が --min-width（既定 1600px）以上。取得後、幅 1600px の JPEG にして _assets/photos/<素材ID>.jpg に置く（全回共通の置き場）。
- 記録：_assets/photos/assets.json と docs/expression/license-ledger.md（取得日・出典URL・作者・ライセンス・使う回）。
- CC BY の素材は、概要欄に入れるクレジットの文を assets.json の credit に書く。
アニメ・映画・テレビの切り抜き GIF は、取得元に含めない（GIF・動画はこのツールでは取得しない）。
"""
import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = 'https://commons.wikimedia.org/w/api.php'
UA = 'video-asset-fetcher/1.0'
ALLOW = [r'^CC0', r'^Public domain', r'^PD\b', r'^CC BY \d', r'^CC BY$']
DENY_TITLE = re.compile(r'logo|icon|poster|screenshot|film|movie|anime|portrait|ロゴ', re.I)
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
LEDGER = os.path.join(ROOT, 'docs', 'expression', 'license-ledger.md')


def api(params):
    url = API + '?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for wait in (0, 20, 60, 120):          # 429（アクセスが多すぎる）は、待ってからやり直す
        time.sleep(wait)
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    sys.exit('FAIL：Wikimedia Commons が 429（アクセスが多すぎる）を返し続ける。10分ほど置いて、同じコマンドをもう一度実行する')


def license_ok(name: str) -> bool:
    return bool(name) and any(re.search(p, name.strip()) for p in ALLOW) and 'SA' not in name and 'NC' not in name and 'ND' not in name


def candidates(query, title, min_width):
    p = {'action': 'query', 'format': 'json', 'prop': 'imageinfo',
         'iiprop': 'url|size|mime|extmetadata', 'iiurlwidth': 1600}
    if title:
        p['titles'] = title
    else:
        p.update({'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': 20,
                  'gsrsearch': f'{query} filetype:bitmap'})
    out = []
    for pg in sorted(api(p).get('query', {}).get('pages', {}).values(), key=lambda x: x.get('index', 0)):
        ii = (pg.get('imageinfo') or [{}])[0]
        md = ii.get('extmetadata', {})
        lic = md.get('LicenseShortName', {}).get('value', '')
        row = {'title': pg['title'], 'width': ii.get('width', 0), 'height': ii.get('height', 0), 'mime': ii.get('mime', ''),
               'license': lic, 'artist': re.sub(r'<[^>]+>', '', html.unescape(md.get('Artist', {}).get('value', ''))).strip()[:80],
               'page': ii.get('descriptionurl', ''), 'thumb': ii.get('thumburl', ''), 'url': ii.get('url', '')}
        why = None
        if not license_ok(lic):
            why = f'ライセンス不可（{lic or "不明"}）'
        elif row['mime'] != 'image/jpeg':
            why = f'JPEG でない（{row["mime"]}）'
        elif row['width'] < min_width:
            why = f'幅 {row["width"]}px < {min_width}px'
        elif DENY_TITLE.search(row['title']):
            why = 'ロゴ・肖像・作品系の疑い'
        row['reject'] = why
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ep_dir'); ap.add_argument('--id', required=True)
    ap.add_argument('--query', default=''); ap.add_argument('--title', default='')
    ap.add_argument('--min-width', type=int, default=1600)
    ap.add_argument('--drop', action='store_true', help='目で見て使わないと決めた写真を、置き場・記録・台帳から消す')
    a = ap.parse_args()
    parts = os.path.normpath(os.path.abspath(a.ep_dir)).split(os.sep)
    ep = next((x for x in parts if re.match(r'^(u|c|ep)\d+_', x)), parts[-1])      # 回のフォルダ名（u01_… など）
    adir = os.path.join(ROOT, '_assets', 'photos')
    os.makedirs(adir, exist_ok=True)
    jp = os.path.join(adir, 'assets.json')
    data = json.load(open(jp, encoding='utf-8')) if os.path.exists(jp) else []
    have = next((d for d in data if d['id'] == a.id), None)
    if a.drop:
        if not have:
            sys.exit(f'{a.id} は無い')
        others = [u for u in have.get('used_in', []) if u != ep]
        if others:
            sys.exit(f'{a.id} は他の回（{"・".join(others)}）でも使っているので消さない')
        data = [d for d in data if d['id'] != a.id]
        json.dump(data, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        f = os.path.join(adir, have['file'])
        if os.path.exists(f):
            os.remove(f)
        led = open(LEDGER, encoding='utf-8').read().splitlines(keepends=True)
        open(LEDGER, 'w', encoding='utf-8').write(''.join(l for l in led if f'| {a.id} |' not in l))
        print(f'消した：{a.id}（{have["title"]}）。使わない理由を visual_plan.json の intent か判断ログに書く')
        return 0
    if have:
        if ep not in have.setdefault('used_in', []):
            have['used_in'].append(ep)
            json.dump(data, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(f"既にある素材を使う：_assets/photos/{have['file']}（{have['license']}）使う回＝{'・'.join(have['used_in'])}")
        return 0
    if not (a.query or a.title):
        sys.exit('--query か --title が要る')
    rows = candidates(a.query, a.title, a.min_width)
    for r in rows:
        print(('  × ' + r['reject']) if r['reject'] else '  ○', r['title'][:70], f"{r['width']}x{r['height']}", r['license'])
    ok = [r for r in rows if not r['reject']]
    if not ok:
        print('FAIL：条件を満たす素材が無い（素材なしで作る＝図解に切り替える）')
        return 1
    r = ok[0]
    raw = os.path.join(adir, f'.{a.id}.orig')
    req = urllib.request.Request(r['thumb'] or r['url'], headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=120) as resp, open(raw, 'wb') as f:
        f.write(resp.read())
    dst = os.path.join(adir, f'{a.id}.jpg')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-vf', "scale='min(1600,iw)':-2", '-q:v', '3', dst], check=True)
    os.remove(raw)
    today = datetime.date.today().isoformat()
    credit = '' if re.match(r'^(CC0|Public domain|PD)', r['license']) else f"写真：{r['artist']}（{r['license']}）{r['page']}"
    rec = {'id': a.id, 'file': f'{a.id}.jpg', 'source': 'Wikimedia Commons', 'title': r['title'], 'page': r['page'],
           'artist': r['artist'], 'license': r['license'], 'orig_size': f"{r['width']}x{r['height']}",
           'fetched': today, 'credit': credit, 'used_in': [ep]}
    data.append(rec)
    json.dump(data, open(jp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    line = (f"| {today} | {ep} | {a.id} | 写真 | [{r['title']}]({r['page']}) | {r['artist'] or '—'} | {r['license']} | "
            f"可 | {'不要' if not credit else '要（概要欄）'} |\n")
    with open(LEDGER, 'a', encoding='utf-8') as f:
        f.write(line)
    print(f"取得：{dst}（{r['license']}）→ 台帳に追記")
    return 0


if __name__ == '__main__':
    sys.exit(main())
