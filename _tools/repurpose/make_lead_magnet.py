#!/usr/bin/env python3
"""リードマグネット生成（YouTube以外のマネタイズ自動化）。

各EPの script.md から「学習ゴール・要点（スライド見出し）・明日やること（【注記】）」を
抽出し、メール/LINEリスト獲得用の配布物「全話まとめ＋実践チートシート」を1本の
Markdownに自動集約する。収益化戦略 docs/monetization-strategy.md §3-L3（リードマグネット）
の実装。

    # 全話（実スクリプトのある回）を集約
    python3 _tools/repurpose/make_lead_magnet.py --out _deliverables/lead-magnet/marketing-lab-cheatsheet.md

    # 一部だけ（例：AI活用編）
    python3 _tools/repurpose/make_lead_magnet.py --only 13,14,15,16 --out /tmp/ai.md

注意:
  - **公開済み動画と文言を一致させたい場合は、正となるブランチのscript.mdに対して実行すること**
    （このリポジトリはブランチによりscript内容が異なりうる。真実源は各話の実制作ブランチ）。
  - CTAリンク（登録URL・特典URL等）は環境変数で差し込む。未設定ならプレースホルダのまま出力。
    LEAD_CHANNEL_URL / LEAD_NEXT_URL / LEAD_CONTACT_URL
"""
import argparse
import glob
import os
import re
import sys

SECTIONS = [
    ("01_beginner", "初級編：マーケティングの型"),
    ("02_intermediate", "中級編：戦略を具体化する"),
    ("03_practical", "実践編：明日から使える"),
    ("04_ai-usage", "AI活用編：AIを実務の相棒に"),
    ("05_advanced", "上級編：組織・経営・ブランド"),
    ("06_case-studies", "事例編：成功と失敗に学ぶ"),
]

# 要点に採らない見出し＝物語の地の部分（ケース/フック/回収など。フレームワークでない）
SKIP_HEADING = re.compile(
    r"^(タイトル|フック|まとめ|オープニング|次回|次への|エンド|CTA|"
    r"コールドオープン|約束|ケース|リフック|回収|導入|問題提起)")

# 見出し先頭の列挙・段階ラベル（原則①/適用②/As-Is 等）を落として実質だけ残す
_ENUM = re.compile(r"^(原則|基本|ポイント|ステップ|手順|法則|方法|コツ|要素|適用)"
                   r"[①-⑳0-9]*\s*[：:]?\s*")
_PHASE = re.compile(r"^(As[\-\s]?Is|To[\-\s]?Be)\s*[：:]?\s*", re.I)
# 末尾のタイムスタンプ括弧だけを除去（（AMA）（ドリルと穴）等の意味ある括弧は残す）
_TS = re.compile(r"\s*（[\d:：〜~\.\-\s]+）\s*$")
# 見出し末尾の制作用注記（＋ミニ問いかけ／（エピソード固有図解）等）を落とす
_ANNOT = re.compile(r"(＋[^、。（]*(問い|問いかけ)[^、。]*|"
                    r"（[^）]*(図解|固有|問いかけ)[^）]*）)\s*$")


def clean_point(head: str) -> str:
    head = re.sub(r"\s*[—―–]{2,}\s*", "：", head)   # —— を : に寄せる
    head = _ENUM.sub("", head)
    head = _PHASE.sub("", head)
    head = _ANNOT.sub("", head)
    return head.strip("：: 　").strip()


def parse_episode(path: str) -> dict | None:
    md = open(path, encoding="utf-8").read()
    lines = md.splitlines()

    m = re.match(r"#\s*第(\d+)回[：:]\s*(.+)", lines[0]) if lines else None
    if not m:
        return None
    num, title = int(m.group(1)), m.group(2).strip()

    # 学習ゴール（テーブルセル）
    g = re.search(r"学習ゴール\s*\|\s*(.+?)\s*\|", md)
    goal = g.group(1).strip() if g else ""

    # スライド見出しから物語スキャフォールディングを除き、原則＝要点だけ残す
    # 見出しはタイムスタンプ付き/無しの両方があるため、末尾TSは後で個別に除去する
    points = []
    for hm in re.finditer(r"^#{2,3}\s*(?:🎬\s*)?スライド\s*\d+\s*[：:]\s*(.+?)\s*$",
                          md, re.M):
        head = _TS.sub("", hm.group(1).strip())
        if SKIP_HEADING.match(head):
            continue
        p = clean_point(head)
        if p and p not in points:
            points.append(p)

    if not points:  # 実スクリプトが無い（テンプレのみ）回は除外
        return None
    return {"num": num, "title": title, "goal": goal, "points": points}


def render(eps: list) -> str:
    ch = os.environ.get("LEAD_CHANNEL_URL", "（チャンネルURLをここに）")
    nxt = os.environ.get("LEAD_NEXT_URL", "（次のステップURLをここに）")
    contact = os.environ.get("LEAD_CONTACT_URL", "（お問い合わせURLをここに）")

    L = ["# マーケティング超入門｜全話まとめ＆実践チートシート",
         "",
         "「AI時代のマーケティング・ラボ」で解説した各テーマの要点を、"
         "1枚で見返せるチートシートにまとめました。動画を見返す前の地図として、"
         "また実務でフレームワークを使うときの手順書としてお使いください。",
         "",
         "**使い方**：①気になるテーマの「要点」を上から確認 → "
         "②「明日やること」を1つだけ実行 → ③詰まったら該当回の動画で深掘り。",
         "",
         "---", ""]

    placed = set()
    # セクション分けは呼び出し側で e["section"] に付与済み
    for prefix, label in SECTIONS:
        sec_eps = sorted([e for e in eps if e.get("section") == prefix],
                         key=lambda e: e["num"])
        if not sec_eps:
            continue
        L += [f"## {label}", ""]
        for e in sec_eps:
            placed.add(e["num"])
            L.append(f"### 第{e['num']}回　{e['title']}")
            if e["goal"]:
                L.append(f"- 🎯 **ゴール**：{e['goal']}")
            L.append("- ✅ **要点（フレームワーク）**：")
            for p in e["points"]:
                L.append(f"    - {p}")
            L.append("")

    # セクション未割当（念のため）
    rest = sorted([e for e in eps if e["num"] not in placed], key=lambda e: e["num"])
    if rest:
        L += ["## その他", ""]
        for e in rest:
            L.append(f"### 第{e['num']}回　{e['title']}")
            L.append("")

    L += ["---", "",
          "## この先へ",
          "",
          f"- 📺 **全話を動画で見る**：{ch}",
          f"- ✉️ **次の一歩（テンプレ・特典）**：{nxt}",
          f"- 💬 **相談・お仕事のご依頼**：{contact}",
          "",
          "> このチートシートは「AI時代のマーケティング・ラボ」の内容をまとめた無料配布物です。"
          "役に立ったら、ぜひチャンネル登録で最新回を受け取ってください。"]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="_deliverables/lead-magnet/marketing-lab-cheatsheet.md")
    ap.add_argument("--only", help="EP番号のカンマ区切り（例 13,14,15,16）")
    ap.add_argument("--root", default=".", help="リポジトリルート")
    a = ap.parse_args()

    only = {int(x) for x in a.only.split(",")} if a.only else None
    eps = []
    for prefix, _ in SECTIONS:
        for path in sorted(glob.glob(os.path.join(a.root, prefix, "ep*", "script.md"))):
            ep = parse_episode(path)
            if not ep:
                continue
            if only and ep["num"] not in only:
                continue
            ep["section"] = prefix
            eps.append(ep)

    if not eps:
        sys.exit("対象エピソードが見つからない（実スクリプトのある回が無い）。")
    eps.sort(key=lambda e: e["num"])

    out = render(eps)
    os.makedirs(os.path.dirname(a.out), exist_ok=True) if os.path.dirname(a.out) else None
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"{len(eps)}話を集約 → {a.out}（{len(out)}字）")
    print("収録:", ", ".join(f"EP{e['num']:02d}" for e in eps))


if __name__ == "__main__":
    main()
