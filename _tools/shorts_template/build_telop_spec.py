#!/usr/bin/env python3
"""
build_telop_spec.py — 第2シリーズ（s2_ura/uNN_*）の Short の spec.py を、shorts.md のナレーションから作る。

社長フィードバック #1（Issue #2、2026-11-06）を型にしたもの：
  - 画面の文字＝読み上げている文（テロップ）。1文＝1ステップで、その文を読み始める瞬間に出す
    （make_video が「画面の文」と「ナレーションの文」を照合して出す時刻を決める。run_shorts.sh は --lead 0.15）。
  - 表示位置は固定：各スライドの文は最初から場所が決まっていて（透明で待機）、出ても位置が動かない。下部の要約テロップは使わない。
  - 文字サイズの下限：本文 76〜88px、シリーズ名の帯 48px、次回予告 64px（verify_shorts が 48px 未満を不合格にする）。
  - 冒頭の入り：S1 は最初の1文だけ（エンジンは S1 の要素を最初のフレームから全部出すため、2文目以降があると先に見えてしまう）。

    python3 _tools/shorts_template/build_telop_spec.py s2_ura/u01_jcpenney-sale            # spec.py を書き出す
    python3 _tools/shorts_template/build_telop_spec.py s2_ura/u01_jcpenney-sale --restructure
        # S1 に2文以上あるとき、2文目以降を S2 の頭へ移して shorts.md を書き直す（ナレーションの文は変えない）

shorts.md の追加欄（任意）：
  **次回予告：** 明日：「残りわずか」で<br>売れるのはなぜ？     （最終スライドに出す。無ければ出さない）
  **表示置換：** ジェーシーペニー=JCペニー、ナンバーワン=No.1   （読み上げ用の表記を画面では元の表記に戻す）
その後は gen_stage.py → verify_shorts.py → run_shorts.sh（いつもの流れ）。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import series as S  # noqa: E402

ACC, GLOW = "#E11D48", "rgba(225,29,72,.25)"
DEFAULT_DISPLAY = {"ジェーシーペニー": "JCペニー", "ナンバーワン": "No.1", "ピーアンドジー": "P&G"}
ANIMS = ["rv-up", "rv-left", "rv-scale", "rv-pop"]
NUM_RE = re.compile(r"(約?[0-9０-９][0-9０-９,.．]*(?:%|％|倍|万|億|円|ドル|年|回|本|人|件|枚|時間|割|か月|種類|店舗|社)*(?:[0-9０-９,.．]*(?:%|万|億|ドル|時間|人))?|[0-9０-９]+(?:\.[0-9]+)?)")


def parse_md(md):
    head, _, body = md.partition("## Short 1")
    sections = list(re.finditer(r"### S(\d+)（(.*?)・[\d.]+〜[\d.]+秒）\s*\n\s*\*\*スライド内容：\*\*\s*(.*?)\n\s*\*\*ナレーション：\*\*\s*\n「(.*?)」",
                                body, re.S))
    slides = [{"label": m[2], "desc": m[3].strip(), "narr": m[4]} for m in sections]
    nxt = re.search(r"\*\*次回予告：\*\*\s*(.+)", md)
    disp = dict(DEFAULT_DISPLAY)
    dm = re.search(r"\*\*表示置換：\*\*\s*(.+)", md)
    if dm:
        for pair in re.split(r"[、,]", dm[1]):
            if "=" in pair:
                a, b = pair.split("=", 1)
                disp[a.strip()] = b.strip()
    title = re.search(r"\*\*タイトル案：\*\*\s*(.+)", md)[1].strip()
    return head, body, slides, (nxt[1].strip() if nxt else ""), disp, title


def sentences(t):
    return [s for s in re.split(r"(?<=[。！？])", t) if s.strip()]


LINE_MAX = 10   # 88px で 880px 幅に収まる文字数（これを超える行は分ける）
_PARTICLES = set("をにはがのでともへ")
_TWO = ("から", "まで", "より", "って", "ので", "のに", "ても", "には", "では", "とは", "へと")


def _is_word_start(ch):
    """次の文字が新しい語の頭らしいか（漢字・カタカナ・英数字・記号）。ひらがなの続き（「くい」「めた」）は語の途中とみなす"""
    return bool(re.match(r"[一-龥ァ-ヶA-Za-z0-9０-９「（]", ch)) and ch != "ー"


def _split_long(line):
    """10字を超える行を、助詞の後で次が新しい語になる位置で2つに分ける（語の途中・数字・カタカナ語を割らない）"""
    if len(line.rstrip("、")) <= LINE_MAX:
        return [line]
    mid = len(line) / 2
    cands = []
    ok_pos = []
    for i in range(2, len(line) - 1):
        prev, nxt = line[i - 1], line[i]
        katakana_run = re.match(r"[ァ-ヶー]", prev) and re.match(r"[ァ-ヶー]", nxt)
        # 英数字の並び（No.1・4.6）と、数字と単位（4.6|ドル・30|万）の間では割らない
        digit_run = bool(re.match(r"[A-Za-z0-9.%％]", prev)) and bool(re.match(r"[A-Za-z0-9.%％ァ-ヶ万億年回本人件枚割倍円時]", nxt))
        if katakana_run or digit_run:
            continue
        ok_pos.append(i)
        score = 0
        if line[i - 2:i] in _TWO or prev in _PARTICLES:
            score += 2
        if _is_word_start(nxt):
            score += 2
        if score:
            cands.append((-score, abs(i - mid), i))
    best = min(cands)[2] if cands else (min(ok_pos, key=lambda i: abs(i - mid)) if ok_pos else int(mid))
    return _split_long(line[:best]) + _split_long(line[best:])


def _width(line):
    return sum(0.6 if re.match(r"[ -~]", c) else 1.0 for c in line)


def display(sent, disp):
    s = sent
    for a, b in disp.items():
        s = s.replace(a, b)
    s = s.rstrip("。")
    # 読点で改行し（読点は行末に残す）、長い行はさらに分ける
    lines = []
    for chunk in s.replace("、", "、\n").split("\n"):
        lines += _split_long(chunk) if chunk else []
    # 1〜2字だけの行（「と」「です」など）は前の行につなげる
    # （前の行が読点で終わるなら次の行の頭へ。最後の行なら前の行の後ろへ）
    merged, carry = [], ""
    for k, ln in enumerate(lines):
        ln = carry + ln
        carry = ""
        if len(ln.rstrip("、")) <= 2:
            if k < len(lines) - 1 and (not merged or merged[-1].endswith("、")):
                carry = ln
                continue
            if merged:
                merged[-1] += ln
                continue
        merged.append(ln)
    if carry:
        merged.append(carry)
    s = "\n".join(merged)
    s = NUM_RE.sub(lambda m: f'<span class="hi">{m[0]}</span>', s)
    return s.replace("\n", "<br>")


def dur(n):
    return max(3.2, round(len(n) / 6.4 + 0.9, 1))


def build(d, restructure=False):
    p = f"{d}/shorts.md"
    md = open(p, encoding="utf-8").read()
    head, body, slides, nxt, disp, title = parse_md(md)
    if not slides:
        sys.exit(f"{p}: スライド（### S1 …）が読めない")
    s1 = sentences(slides[0]["narr"])
    if len(s1) > 1:
        if not restructure:
            sys.exit(f"{d}: S1 に {len(s1)} 文ある（S1 は1文だけ）。--restructure で2文目以降を S2 の頭へ移す")
        rest = "".join(s1[1:])
        slides[0]["narr"] = s1[0]
        slides[1]["narr"] = rest + slides[1]["narr"]
        slides[1]["desc"] = "（S1 から移した文）＋" + slides[1]["desc"]
    # shorts.md の各スライド節を、今のナレーションと時刻で書き直す
    t = 0.0
    secs = []
    for i, sl in enumerate(slides, 1):
        st, t = t, round(t + dur(sl["narr"]), 1)
        sl["end"] = t
        secs.append(f"### S{i}（{sl['label']}・{st:.1f}〜{t:.1f}秒）\n\n**スライド内容：** {sl['desc']}\n\n**ナレーション：**\n「{sl['narr']}」\n\n")
    first_sec = body.index("### S1")
    new_body = body[:first_sec] + "".join(secs)
    new_body = re.sub(r"\*\*想定尺：\*\* 約\d+秒（(\d+)スライド・合計\d+字）",
                      lambda m: f"**想定尺：** 約{round(t)}秒（{len(slides)}スライド・合計{sum(len(s['narr']) for s in slides)}字）", new_body)
    open(p, "w", encoding="utf-8").write(head + "## Short 1" + new_body.rstrip() + "\n")

    it = S.s2_item(d)
    no = it[1] if it else 0
    out_slides = []
    for i, sl in enumerate(slides):
        els = []
        if i == 0:
            els.append({"id": "s1-tag", "cls": "k-tag", "html": f"売れる仕組みの裏側 #{no:02d}", "anim": "rv-fade", "t": 0.0,
                        "style": "font-size:48px"})
        for j, sent in enumerate(sentences(sl["narr"])):
            # 行の幅（全角=1・半角英数=0.6）で文字サイズを決める。読点も1字ぶんの幅をとる
            # （2026-11-07：読点込み11字を 88px で組んで 880px を超え、ブラウザが勝手に折り返した）
            longest = max(_width(re.sub(r"<[^>]+>", "", x)) for x in display(sent, disp).split("<br>"))
            fs = next((f for f in (88, 80, 72, 64) if longest * f <= 870), 64)
            els.append({"id": f"s{i+1}-t{j+1}", "cls": "k-line", "html": display(sent, disp),
                        "anim": ANIMS[(i + j) % len(ANIMS)], "t": 0.0 if j == 0 else 1.0 * j, "style": f"font-size:{fs}px;margin:.25em 0"})
        if i == len(slides) - 1 and nxt:
            els.append({"id": f"s{i+1}-next", "cls": "cta-line", "html": nxt, "anim": "rv-pop", "t": 2.0, "style": "font-size:64px"})
        out_slides.append({"end": sl["end"], "els": els})
    spec = {"title": title, "accent": ACC, "glow": GLOW, "telop": 1, "slides": out_slides,
            "narrations": [sl["narr"] for sl in slides]}
    open(f"{d}/shorts_build/short1/spec.py", "w", encoding="utf-8").write(json.dumps(spec, ensure_ascii=False, indent=1) + "\n")
    print(f"{d}: spec.py（テロップ同期型）{len(slides)}枚・{t:.1f}秒")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    for d in args:
        build(d.rstrip("/"), "--restructure" in sys.argv)
