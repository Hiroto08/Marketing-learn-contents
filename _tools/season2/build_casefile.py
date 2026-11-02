#!/usr/bin/env python3
"""シーズン2「ケースファイル」本編の slide.html を宣言的 spec から生成する。

    python3 _tools/season2/build_casefile.py <episode_dir>

入力:
  <episode_dir>/casefile_spec.py … スライドの中身（HTML断片）と STEPS（話す順の要素id）
  <episode_dir>/script.md        … NARRATIONS の唯一の正（ここから文字単位でコピーする＝不一致が起きない）
  _tools/season2/casefile_theme.css … シーズン2の見た目（全回共通）
  ベースHTML（エンジン：フォント・base CSS・JS）… 既定は 05_advanced/ep20_growth-hack/slide.html

出力: <episode_dir>/slide.html（verify_episode.py は <meta name="episode-profile" content="casefile"> を
      見て 10〜12枚・5〜7分の基準で検査する。_tools/profiles.py が数値の正）

エンジン（base CSS の keyframes / rv-* / .se / JS 再生ロジック）は書き換えない。差し替えるのは
<title>・<style id="ep-css">・ステージ本体・JSデータ配列（STEPS/SLIDES_META/NARRATIONS/TOTAL_SECS）だけ。

spec の形式（Pythonリテラル辞書）:
{
  "case_no": "01", "subject": "コメダ珈琲", "watermark": "KOMEDA",
  "accent": "#E0884A", "glow": "rgba(224,136,74,.25)", "accent_name": "copper",
  "title": "コメダ珈琲は、なぜ長居されても儲かる？",
  "chapters": ["謎", "証拠", "種明かし", "あなたの店"],
  "slides": [
    {"chapter": None,            # None=表紙（ヘッダー無し）。0始まりで chapters の位置
     "body": "cover",            # cf-body に足すクラス（cover / center / 空）
     "html": "<div class=\\"se ...\\" id=\\"s1-a\\">…</div>",
     "steps": [["s1-a", "rv-fade"], ...]},   # 話す順。anim は rv-fade/up/left/right/scale/pop/grow/stamp/draw
  ]
}
"""
import ast
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THEME = os.path.join(ROOT, "_tools/season2/casefile_theme.css")
BASE = os.path.join(ROOT, "05_advanced/ep20_growth-hack/slide.html")
ANIMS = {"rv-fade", "rv-up", "rv-left", "rv-right", "rv-scale", "rv-pop", "rv-grow", "rv-stamp", "rv-draw"}


def narrations(ep):
    md = open(f"{ep}/script.md", encoding="utf-8").read()
    return [m.group(1).strip() for m in re.finditer(
        r'\*\*ナレーション：\*\*\s*\n「(.*?)」\s*\n\s*---', md, re.S)]


def est_secs(n):
    """verify_episode.py の推定式と同じ（＋スライド前後の余白1秒）"""
    return (len(n.replace("\n", "")) / 6.8 + (n.count("\n") + 1) * 0.45
            + len([s for s in re.split(r"[。？?！]", n) if s.strip()]) * 0.28 + 1.0)


def header(spec, si, n):
    ch = spec["slides"][si].get("chapter")
    if ch is None:
        return ""
    chips = []
    for k, name in enumerate(spec["chapters"]):
        cls = "on" if k == ch else ("done" if k < ch else "")
        chips.append(f'<span class="{cls}">{name}</span>')
    return (f'  <div class="cf-top"><div class="cf-file"><span class="cf-rec"></span>'
            f'<b>CASE FILE {spec["case_no"]}</b><span class="cf-subj">{spec["subject"]}</span>'
            f'<span>{si + 1:02d} / {n:02d}</span></div>'
            f'<div class="cf-chap">{"".join(chips)}</div></div>\n')


def main(ep):
    ep = ep.rstrip("/")
    spec = ast.literal_eval(open(f"{ep}/casefile_spec.py", encoding="utf-8").read())
    narr = narrations(ep)
    slides = spec["slides"]
    n = len(slides)
    if len(narr) != n:
        sys.exit(f"NG: script.md のナレーション{len(narr)}件 ≠ spec のスライド{n}枚")

    html = open(spec.get("base", BASE), encoding="utf-8").read()
    base_css = html.split('<style id="ep-css">')[0]
    theme = open(THEME, encoding="utf-8").read()

    # 1) title / profile meta
    html = re.sub(r"<title>.*?</title>", f"<title>{spec['title']}</title>", html, count=1, flags=re.S)
    html = re.sub(r'\s*<meta name="episode-profile"[^>]*>', "", html)
    html = html.replace('<meta charset="UTF-8">',
                        '<meta charset="UTF-8">\n<meta name="episode-profile" content="casefile">', 1)

    # 2) ep-css = 回のアクセント＋シーズン2テーマ
    epcss = (f'<style id="ep-css">\n/* EP{os.path.basename(ep)[2:4]} accent: {spec.get("accent_name", "")} */\n'
             f':root {{ --accent:{spec["accent"]}; --glow-acc:{spec["glow"]}; }}\n{theme}\n</style>')
    html, k = re.subn(r'<style id="ep-css">.*?</style>', lambda _: epcss, html, count=1, flags=re.S)
    assert k == 1, "ベースHTMLに <style id=\"ep-css\"> が無い"

    # 3) ステージ本体
    out, steps, meta = [], [], []
    t = 0.0
    for i, sl in enumerate(slides):
        sid = f"s{i + 1}"
        dur = est_secs(narr[i])
        meta.append((sid, t, t + dur))
        body_cls = sl.get("body", "")
        if sl.get("chapter") is None and "cover" not in body_cls:
            body_cls = (body_cls + " cover").strip()
        out.append(f'  <section class="slide{" active" if i == 0 else ""}" id="{sid}">\n'
                   f'  <div class="slide-num">{i + 1:02d} / {n}</div><div class="step-dots" id="sd{i + 1}"></div>\n'
                   f'  <div class="cf-wm" aria-hidden="true">{sl.get("watermark", spec.get("watermark", ""))}</div>\n'
                   + header(spec, i, n)
                   + f'  <div class="cf-body {body_cls}">\n{sl["html"].strip()}\n  </div>\n  </section>\n')
        st = sl["steps"]
        # STEPS に載っていない .se 要素（キッカー等）は、そのスライドの最初のSTEPと一緒に出す
        # （載せ忘れると録画で永久に不可視になる。2026-11-02 CF01で実害）
        stepped = {e for e, _ in st}
        orphans = [m.group(1) for m in re.finditer(
            r'<[a-z]+[^>]*class="[^"]*\bse\b[^"]*"[^>]*\bid="([^"]+)"', sl["html"]) if m.group(1) not in stepped]
        for j, (eid, anim) in enumerate(st):
            if anim not in ANIMS:
                sys.exit(f"NG: {sid} の anim '{anim}' は未定義（{sorted(ANIMS)}）")
            if f'id="{eid}"' not in sl["html"]:
                sys.exit(f"NG: {sid} の STEP id '{eid}' が html に無い")
            if re.search(rf"^#{re.escape(eid)}\b", base_css, re.M):
                sys.exit(f"NG: id '{eid}' はベースCSSにID指定があり見た目が崩れる。別名にする（例 s1-head）")
            ids = (orphans + [eid]) if j == 0 else [eid]
            steps.append((i, t + dur * j / max(len(st), 1), ids, anim))
        t += dur
    stage = '  <div id="flash"></div>\n' + "".join(out)
    html, k = re.subn(r'  <div id="flash"></div>.*?(</div><!-- /stage -->)',
                      lambda m: stage + m.group(1), html, count=1, flags=re.S)
    assert k == 1, "ステージ領域が見つからない"

    # 4) JSデータ配列
    steps_js = "\n".join(f"  {{si:{si}, t:{st:.1f}, ids:[{', '.join(repr(x) for x in ids)}], anim:'{an}'}},"
                          for si, st, ids, an in steps)
    meta_js = "\n".join(f"  {{id:'{sid}', start:{a:.1f}, end:{b:.1f}, dotContainerId:'sd{k + 1}'}},"
                        for k, (sid, a, b) in enumerate(meta))
    narr_js = "\n".join(f"  `{x}`," for x in narr)
    total = int(round(meta[-1][2]))
    for name, body in (("STEPS", steps_js), ("SLIDES_META", meta_js), ("NARRATIONS", narr_js)):
        html, k = re.subn(rf"const {name} = \[.*?\n\];", lambda _: f"const {name} = [\n{body}\n];",
                          html, count=1, flags=re.S)
        assert k == 1, f"const {name} が見つからない"
    html = re.sub(r"const TOTAL_SECS = \d+;", f"const TOTAL_SECS = {total};", html, count=1)
    html = re.sub(r"Slide 1 / \d+", f"Slide 1 / {n}", html)

    open(f"{ep}/slide.html", "w", encoding="utf-8").write(html)
    print(f"wrote {ep}/slide.html  slides={n} steps={len(steps)} est={total // 60}:{total % 60:02d}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
