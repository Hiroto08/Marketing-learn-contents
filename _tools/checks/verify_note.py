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
"""
import glob
import os
import re
import sys

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

    return fails, warns


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
