#!/usr/bin/env python3
"""Shorts縦型 stage.html を spec（宣言的データ）から生成する。

    python3 _tools/shorts_template/gen_stage.py <spec.py> <out_stage.html>
    # 慣例: spec は <episode_dir>/shorts_build/shortN/spec.py に置いてコミットする
    #        （stage.html を手で書かない＝エンジン部分を壊しようがない）

spec.py の形式（Pythonリテラル辞書。例は既存の spec.py を参照）:
{
  "title": "Shortsのタイトル",
  "accent": "#F97316",                     # 本編 slide.html の --accent と同値
  "glow": "rgba(249,115,22,.25)",          # accent の .25 透過
  "slides": [                              # 4〜6枚（shorts-production.md §2）
    {"end": 3.0,                           # 累積の終了秒（開始は前枚のend）
     "els": [                              # 表示要素＝話す順（STEPSになる）
        {"id": "s1-num", "cls": "k-num",   # cls: k-num/k-line/k-sub/k-tag/cta-line
         "html": "60%",                    # .hi span でキーイエロー強調可
         "anim": "rv-scale",               # rv-fade/up/left/right/scale/pop
         "t": 0.0},                        # スライド内の相対秒
     ],
     "caption": "下部テロップ（1行15〜18字）",   # 省略可。caption_t で表示秒指定可
    }, ...
  ],
  "narrations": ["...", ...],              # shorts.md と文字単位で一致させること
  # ── シーズン2（任意）──
  "theme": "casefile",                     # theme_casefile.css を差し込む（紙の証拠カード・明朝・ヘッダー）
  "profile": "s2",                         # 検査基準（_tools/profiles.py：20〜45秒・4〜7枚・230字）
  "header": {"label": "CASE FILE 01", "subject": "コメダ珈琲"},   # 全スライド上部の静的ヘッダー
  "watermark": "KOMEDA",                   # 背景の透かし文字
  # els の cls に k-card（html内で .lbl/.big/.txt/.stamp）、k-kicker、k-src が使える
}

生成後は必ず verify_shorts.py を通す:
    python3 _tools/checks/verify_shorts.py <episode_dir>/shorts_build/shortN
"""
import ast
import io
import os
import sys

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vertical_template.html")


def main(spec_path, out_path):
    spec = ast.literal_eval(open(spec_path, encoding="utf-8").read())
    tpl = open(TEMPLATE, encoding="utf-8").read()

    tpl = tpl.replace("SHORTS_TITLE", spec["title"])
    if spec.get("theme"):
        css = open(os.path.join(os.path.dirname(TEMPLATE), f"theme_{spec['theme']}.css"), encoding="utf-8").read()
        tpl = tpl.replace("</style>\n</head>", css + "\n</style>\n</head>", 1)
    if spec.get("profile"):
        tpl = tpl.replace('<meta charset="UTF-8">',
                          f'<meta charset="UTF-8">\n<meta name="shorts-profile" content="{spec["profile"]}">', 1)
    head_html = ""
    if spec.get("header"):
        h = spec["header"]
        head_html = (f'  <div class="cf-head">{h["label"]}'
                     f'<span class="subj">{h.get("subject", "")}</span></div>\n')
    if spec.get("watermark"):
        head_html = f'  <div class="cf-wm" aria-hidden="true">{spec["watermark"]}</div>\n' + head_html
    tpl = tpl.replace("--accent:#FFD54F;", f"--accent:{spec['accent']};")
    tpl = tpl.replace("--glow-acc:rgba(255,213,79,.25);", f"--glow-acc:{spec['glow']};")

    stage = io.StringIO()
    steps = []
    meta = []
    start = 0.0
    for i, sl in enumerate(spec["slides"], 1):
        stage.write(f'<section class="slide" id="s{i}">\n{head_html}  <div class="card">\n')
        for el in sl["els"]:
            stage.write(f'    <div class="se {el["cls"]}" id="{el["id"]}">{el["html"]}</div>\n')
            steps.append((i - 1, start + el["t"], el["id"], el["anim"]))
        stage.write('  </div>\n')
        if sl.get("caption"):
            cid = f's{i}-cap'
            stage.write(f'  <div class="caption-zone"><div class="se caption" id="{cid}">{sl["caption"]}</div></div>\n')
            steps.append((i - 1, start + sl.get("caption_t", 0.2), cid, "rv-fade"))
        stage.write('</section>\n')
        meta.append((i, start, sl["end"]))
        start = sl["end"]

    steps.sort(key=lambda x: (x[0], x[1]))
    meta_js = "\n".join(f"  {{id:'s{i}', start:{s:.1f}, end:{e:.1f}}}," for i, s, e in meta)
    steps_js = "\n".join(f"  {{si:{si}, t:{t:.1f}, ids:['{eid}'], anim:'{anim}'}}," for si, t, eid, anim in steps)
    narr_js = "\n".join(f"  `{n}`," for n in spec["narrations"])
    total = spec["slides"][-1]["end"]

    a, b = tpl.split("<!-- ══ SHORTS_STAGE_START ══ -->")
    _, c = b.split("<!-- ══ SHORTS_STAGE_END ══ -->")
    tpl = (a + "<!-- ══ SHORTS_STAGE_START ══ -->\n" + stage.getvalue()
           + "<!-- ══ SHORTS_STAGE_END ══ -->" + c)

    tpl = tpl.replace("const SLIDES_META = [\n  // {id:'s1', start:0.0, end:4.0},\n];",
                      f"const SLIDES_META = [\n{meta_js}\n];")
    tpl = tpl.replace("const STEPS = [\n  // {si:0, t:0.0, ids:['s1-cap'], anim:'rv-fade'},\n];",
                      f"const STEPS = [\n{steps_js}\n];")
    tpl = tpl.replace("const NARRATIONS = [\n  // `フックの一文。`,\n];",
                      f"const NARRATIONS = [\n{narr_js}\n];")
    tpl = tpl.replace("const TOTAL_SECS = 0;", f"const TOTAL_SECS = {total};")

    open(out_path, "w", encoding="utf-8").write(tpl)
    print(f"wrote {out_path}  slides={len(meta)} steps={len(steps)} total={total}s")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
