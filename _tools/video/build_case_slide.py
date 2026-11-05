"""第2シリーズのケースファイル（cNN）の slide.html を、既存本編の slide.html（エンジン）から組み立てる。
エンジン部分（base CSS・keyframes・rv-*・.se・#__heartbeat・JS本体）は一切触らず、
  ① ep-css ブロック（アクセント色・S1背景）
  ② STAGE 内の <section> 群
  ③ STEPS / SLIDES_META / NARRATIONS / TOTAL_SECS
だけを差し替える。
使い方: python3 _tools/video/build_case_slide.py <cNN_dir>/case.json 06_case-studies/ep22_v-shaped-recovery/slide.html <cNN_dir>/slide.html
case.json: {"accent","glow","s1bg","slides":[{"html": "<section内のpad部分>", "steps":[[id,anim],...], "narr": "..."}]}
"""
import json, re, sys

case = json.load(open(sys.argv[1], encoding="utf-8"))
base = open(sys.argv[2], encoding="utf-8").read()
N = len(case["slides"])


def est(n):
    return (len(n.replace("\n", "")) / 6.8 + (n.count("\n") + 1) * 0.45
            + len([s for s in re.split(r"[。？?！]", n) if s.strip()]) * 0.28)


# ① ep-css
css = f"""<style id="ep-css">

/* ── vertical centering override ── */
.pad   {{ justify-content: center; }}
.pad-t {{ justify-content: center; }}

/* 第2シリーズ ケースファイル accent */
:root {{ --accent:{case['accent']}; --glow-acc:{case['glow']}; }}

#s1{{background:radial-gradient(ellipse 90% 75% at 65% 45%, {case['s1bg']} 0%, var(--slide-bg) 68%);align-items:center;justify-content:center;text-align:center;}}

</style>"""
base = re.sub(r'<style id="ep-css">.*?</style>', lambda m: css, base, count=1, flags=re.S)

# ② sections
secs = []
for i, sl in enumerate(case["slides"], 1):
    cls = "slide active" if i == 1 else "slide"
    if i == N:
        secs.append(f'  <section class="{cls}" id="s{i}">\n    <div class="step-dots" id="sd{i}"></div>\n  </section>')
        continue
    rings = ""
    if i == 1:
        rings = ('    <div class="s1-ring s1-ring1" aria-hidden="true"></div>\n'
                 '    <div class="s1-ring s1-ring2" aria-hidden="true"></div>\n'
                 '    <div class="s1-ring s1-ring3" aria-hidden="true"></div>\n')
    secs.append(f'  <section class="{cls}" id="s{i}">\n{rings}'
                f'    <div class="slide-num">{i:02d} / {N:02d}</div><div class="step-dots" id="sd{i}"></div>\n'
                f'{sl["html"]}\n  </section>')
stage = "\n".join(secs)
base = re.sub(r'(<div id="flash"></div>\n).*?(\n\n?</div><!-- /stage -->)', lambda m: m.group(1) + stage + "\n" + m.group(2), base, count=1, flags=re.S)

# ③ data
steps, metas, narrs = [], [], []
t = 0.0
for i, sl in enumerate(case["slides"]):
    d = round(est(sl["narr"]) + 1.2, 1)
    start, end = round(t, 1), round(t + d, 1)
    ids = sl.get("steps", [])
    for k, (eid, anim) in enumerate(ids):
        # 最初の要素は即時、残りはナレーション尺に均等配置（STEPS 密度 5〜7秒・無変化15秒以内）
        tt = start + (0.0 if k == 0 else d * k / len(ids))
        steps.append(f"  {{si:{i}, t:{tt:.1f}, ids:['{eid}'], anim:'{anim}'}},")
    metas.append(f"  {{id:'s{i+1}', start:{start:.1f}, end:{end:.1f}, dotContainerId:'sd{i+1}'}},")
    narrs.append("  `" + sl["narr"] + "`,")
    t = end
total = int(round(t))
base = re.sub(r"const STEPS = \[\n.*?\n\];", lambda m: "const STEPS = [\n" + "\n".join(steps) + "\n];", base, count=1, flags=re.S)
base = re.sub(r"const SLIDES_META = \[\n.*?\n\];", lambda m: "const SLIDES_META = [\n" + "\n".join(metas) + "\n];", base, count=1, flags=re.S)
base = re.sub(r"const NARRATIONS = \[\n.*?\n\];", lambda m: "const NARRATIONS = [\n" + "\n".join(narrs) + "\n];", base, count=1, flags=re.S)
base = re.sub(r"const TOTAL_SECS = \d+;", f"const TOTAL_SECS = {total};", base, count=1)
base = base.replace("Slide 1 / 18", f"Slide 1 / {N}")
open(sys.argv[3], "w", encoding="utf-8").write(base)
print(f"wrote {sys.argv[3]} slides={N} steps={len(steps)} est={total}s")
