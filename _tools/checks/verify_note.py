#!/usr/bin/env python3
"""note記事の機械検品（note-qa が独立再実行する唯一の合否判定）。

note編集現場の「校了チェック」を機械化したもの。主観的な読みやすさは人手ロール
（note-writer/note-proofreader）が担い、本スクリプトは「公開してはいけない機械的欠陥」
を落とす最終ゲート。verify_episode.py と同じく RESULT: PASS/FAIL を1行で返す。

    python3 _tools/checks/verify_note.py _deliverables/note/ep01_what-is-marketing.md
    python3 _tools/checks/verify_note.py _deliverables/note        # ディレクトリ一括

判定基準（FAIL＝公開不可 / WARN＝要確認だが停止はしない）:
  1. 制作物の混入禁止：スライド/【…】/タイムスタンプ/「ナレーション」/YouTube定型挨拶
  2. 構造：H1が1つ、本文見出し(##)3つ以上、CTAブロック、ハッシュタグ行
  3. タイトル長：全角30字前後が理想（>45字 FAIL / 33-45字 WARN）
  4. 本文量：1,200〜6,000字（読み物として過少/過多を防ぐ）
  5. 空セクション禁止（##直後に本文が無い）
  6. CTA：チャンネルURLがある（動画URLは任意＝未公開回は省略可）
  7. ハッシュタグ：3〜8個
  ── 2026-11-10 追加（社長指示・Issue #2。quality-gates.md の N1〜N7）──
  N1 自分の呼び方：本文に「自社」「弊社」「当社」が無い（書き手は「自分」。読者の会社は「あなたの会社」「自分の会社」）
  N2 タイトルの数字：タイトルに算用数字が1つ以上ある（数字・実績が伝わる）
  N3 対象の絞り込み：記事の末尾に <!-- 対象読者: 誰向けか｜キーワード1 キーワード2 --> があり、
     キーワードのどれかがタイトルか冒頭300字にある
  N4 冒頭の価値：最初の見出し（##）より前の文章に「数字＋単位」が1つ以上あり、読者の得を言う文
     （〜がわかる・〜できる・〜の理由・〜の手順 など）がある。<!-- 有料ライン --> があるときは、それより前で判定する
  N5 定型句：AI が書いたと見抜かれる定型句（いかがでしたか 等。check_style.py の BANNED）が無い
  N6 語尾の連続：同じ語尾が4文以上続かない
  N7 数字の出どころ：本文の「数字＋単位」が、対応する回の script.md のナレーションにある（記事で新しい数字を足さない）。
     足すときは、記事の末尾に <!-- 追加の数字: 値｜URL1｜URL2 --> を書く（2ソース）
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CTA_MARKER = "この記事は動画でも見られます"

FORBIDDEN = [
    (r"スライド\s*\d+", "スライド番号が本文に残っている"),
    (r"【[^】]+】", "制作用タグ【…】が残っている"),
    (r"（?\d+:\d{2}\s*[〜~]", "タイムスタンプが残っている"),
    (r"ナレーション", "「ナレーション」という制作語が残っている"),
    (r"さっそく始めましょう", "YouTube定型挨拶が残っている"),
    (r"第\d+回のテーマは", "YouTube定型オープニングが残っている"),
    (r"アニメーション[:：]", "制作指示（アニメーション）が残っている"),
]


def split_body_footer(md: str):
    idx = md.find(CTA_MARKER)
    if idx == -1:
        return md, ""
    # CTAマーカーを含む見出し(##)の手前まで＝本文
    head = md.rfind("##", 0, idx)
    return md[:head] if head != -1 else md[:idx], md[head if head != -1 else idx:]


def check_file(path: str):
    md = open(path, encoding="utf-8").read()
    fails, warns = [], []

    # H1
    h1 = re.findall(r"^#\s+(.+)$", md, re.M)
    if len(h1) != 1:
        fails.append(f"H1（記事タイトル）が {len(h1)} 個（1つであるべき）")
    title = h1[0].strip() if h1 else ""
    tlen = len(title)
    if tlen > 45:
        fails.append(f"タイトルが長すぎる（{tlen}字 / note推奨は32字前後）")
    elif tlen > 33:
        warns.append(f"タイトルやや長め（{tlen}字）")

    body, footer = split_body_footer(md)

    # 禁止パターンは「見出しを除いた地の文」だけに適用。
    # 見出し・タイトルの【カテゴリ】表記は note の正当なスタイルなので対象外。
    prose = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    for pat, msg in FORBIDDEN:
        if re.search(pat, prose):
            fails.append(msg)

    # 見出し構造
    heads = re.findall(r"^##\s+(.+)$", body, re.M)
    if len(heads) < 3:
        fails.append(f"本文見出し(##)が {len(heads)} 個（3つ以上必要）")

    # 空セクション（##直後に実体のある本文が無い）
    for m in re.finditer(r"^##\s+.+$", body, re.M):
        after = body[m.end():]
        nxt = re.search(r"^##\s+", after, re.M)
        seg = after[:nxt.start()] if nxt else after
        if not seg.strip():
            fails.append(f"空セクション: 「{m.group(0).strip()[:20]}」直後に本文が無い")

    # CTA
    if CTA_MARKER not in md:
        fails.append("CTAブロック（動画・チャンネル導線）が無い")
    if "youtube.com/channel/" not in footer and "youtube.com/@" not in footer:
        warns.append("CTAにチャンネルURLが見当たらない")

    # ハッシュタグ
    tags = re.findall(r"(?:^|\s)#[^\s#]+", footer)
    if not (3 <= len(tags) <= 8):
        (fails if len(tags) == 0 else warns).append(
            f"ハッシュタグが {len(tags)} 個（3〜8個が目安）")

    # 本文量
    body_chars = len(re.sub(r"\s", "", body))
    if body_chars < 1200:
        fails.append(f"本文が少なすぎる（{body_chars}字 / 1,200字以上）")
    elif body_chars > 6000:
        warns.append(f"本文が多め（{body_chars}字 / 分割検討）")

    fails += quality_checks(path, md, title, body)
    return fails, warns


def quality_checks(path, md, title, body):
    """N1〜N7（2026-11-10 追加）"""
    import check_style as CS
    out = []
    prose = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    prose = re.sub(r"<!--.*?-->", "", prose, flags=re.S)
    # N1
    for w in ("自社", "弊社", "当社"):
        n = prose.count(w)
        if n:
            out.append(f"N1 「{w}」が{n}か所（書き手は「自分」、読者の会社は「あなたの会社／自分の会社」と書く）")
    # N2
    if not re.search(r"\d", title):
        out.append("N2 タイトルに数字が無い（数字・実績が伝わる形にする）")
    # N3
    lead_all = body.split("\n## ")[0]
    paid = md.find("<!-- 有料ライン -->")
    free = md[:paid] if paid != -1 else lead_all
    head300 = re.sub(r"\s", "", re.sub(r"^#\s+.+$", "", lead_all, flags=re.M))[:300]
    m = re.search(r"<!--\s*対象読者[:：]\s*(.+?)\s*-->", md)
    if not m or "｜" not in m[1]:
        out.append("N3 <!-- 対象読者: 誰向けか｜キーワード --> が無い")
    else:
        kws = [k for k in re.split(r"[\s　、,]+", m[1].split("｜", 1)[1]) if k]
        if not any(k in title or k in head300 for k in kws):
            out.append(f"N3 対象読者のキーワード（{'・'.join(kws)}）が、タイトルにも冒頭300字にも無い")
    # N4
    free_txt = re.sub(r"^#\s+.+$", "", free, flags=re.M)
    if not CS.numbers(free_txt):
        out.append("N4 冒頭（無料で読める部分）に「数字＋単位」が無い")
    if not re.search(r"わかります|分かります|わかる|分かる|できます|できる|理由|手順|方法|やり方|やりかた|コツ|ひもと", free_txt):
        out.append("N4 冒頭（無料で読める部分）に、読者の得を言う文（〜がわかる・〜できる・理由・手順）が無い")
    # N5
    for b in CS.BANNED:
        if b in prose:
            out.append(f"N5 定型句「{b}」を使っている")
    # N6
    sents = [x for x in re.split(r"(?<=[。！？])\s*", re.sub(r"\n+", "", prose)) if len(x) > 3]

    def cls(x):
        x = re.sub(r"[。！？!?」』\s]+$", "", x)
        for pat, c in CS.ENDINGS:
            if re.search(pat, x):
                return c
        return "体言止め"
    cs = [cls(x) for x in sents]
    run = 1
    for i in range(1, len(cs)):
        run = run + 1 if cs[i] == cs[i - 1] else 1
        if run == 4:
            out.append(f"N6 語尾「{cs[i]}」が4文続く（…{sents[i][-18:]}）")
    # N7
    em = re.search(r"ep(\d+)_", os.path.basename(path))
    scripts = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", f"0*/ep{em[1]}_*/slide.html")) if em else []
    if scripts:
        narr = CS.numbers("".join(CS.sents_of(scripts[0])))
        extra = CS.numbers(" ".join(re.findall(r"<!--\s*追加の数字[:：]\s*(.+?)\s*-->", md)))
        miss = sorted(v for k, v in CS.numbers(prose).items() if k not in narr and k not in extra)
        if miss:
            out.append(f"N7 動画（ナレーション）に無い数字：{miss[:6]}（消すか、<!-- 追加の数字: … --> に2ソースを書く）")
    return out


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    target = sys.argv[1]
    files = (sorted(glob.glob(os.path.join(target, "ep*.md")))
             if os.path.isdir(target) else [target])
    if not files:
        sys.exit(f"対象なし: {target}")

    total_fail = 0
    for f in files:
        fails, warns = check_file(f)
        status = "PASS" if not fails else "FAIL"
        total_fail += bool(fails)
        print(f"\n── {os.path.basename(f)}: {status}")
        for x in fails:
            print(f"   ✗ {x}")
        for x in warns:
            print(f"   ⚠ {x}")

    print(f"\nRESULT: {'PASS' if total_fail == 0 else 'FAIL'} "
          f"（{len(files)}件中 FAIL {total_fail}件）")
    sys.exit(1 if total_fail else 0)


if __name__ == "__main__":
    main()
