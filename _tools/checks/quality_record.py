#!/usr/bin/env python3
"""
quality_record.py — 品質検査を全部走らせて、動画ごとの実施記録（quality_record.md）を書く（Issue #2 依頼3-4・依頼4）。

    python3 _tools/checks/quality_record.py <回のフォルダ>            # 本編＋その回の Shorts。記録は <回のフォルダ>/quality_record.md
    python3 _tools/checks/quality_record.py <回のフォルダ> --strict   # 旧基準の回も新基準で判定（試行・見直し用。記録は書くが合否は厳しい）

run_episode.sh / run_shorts.sh がビルドの後に呼ぶ。記録はコミットする。中身：
  1. 固有名詞（表記・読み・確認ソース・確認日）— この動画に出たもの全部
  2. 読み検査（ビルド前の原稿／ビルド後の音声）R1〜R9
  3. 数字の確認 F1〜F3
  4. AI臭さ検査（文章・テロップ）A1〜A7・T1〜T2
  5. 耳で確かめる項目 V1〜V4（機械では判定できない。聞いた人が記入する）
合否は機械検査（1〜4）で決まる。1つでも ✗ があれば終了コード 1。
"""
import datetime
import glob
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_facts as CF  # noqa: E402
import check_readings as CR  # noqa: E402
import check_style as CS  # noqa: E402

V_ITEMS = [
    ("V1", "人名・社名・商品名が、台帳の読みどおりに聞こえる"),
    ("V2", "数字（西暦・金額・割合・単位）が、画面の表記どおりに聞こえる"),
    ("V3", "文の途中に不自然な切れ目・息継ぎが無い。文と文の間が詰まりすぎていない"),
    ("V4", "抑揚が平らすぎる文・語尾が同じ調子で続く箇所が無い"),
]


def marks(fails, names, legacy=False):
    out = []
    for k, v in fails.items():
        if k not in names:
            continue
        if v:
            out += [f"- {'△（参考）' if legacy else '✗'} **{k} {names[k]}**：{x}" for x in v[:10]]
            if len(v) > 10:
                out.append(f"  - …ほか{len(v) - 10}件")
        else:
            out.append(f"- ✓ {k} {names[k]}")
    return out


def keep_listening(path):
    """前の記録に書かれた「耳で確かめる項目」の記入（聞いた人・日付）は消さない"""
    if not os.path.exists(path):
        return None
    m = re.search(r"^## 5\. 耳で確かめる項目.*?(?=^## |\Z)", open(path, encoding="utf-8").read(), re.S | re.M)
    return m[0].rstrip() if m and "未実施" not in m[0] else None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    ok_all = True
    for d in args:
        d = d.rstrip("/")
        targets = [d] if os.path.exists(f"{d}/slide.html") else []
        targets += sorted(os.path.dirname(p) for p in glob.glob(f"{d}/shorts_build/short*/stage.html"))
        if not targets:
            sys.exit(f"{d}: slide.html も shorts_build/short*/stage.html も無い")
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        out = [f"# 品質検査の実施記録：{os.path.basename(d)}", "",
               f"- 実施日：{datetime.date.today().isoformat()}（ツールの版 {rev}）",
               "- 検査の定義：`.claude/skills/episode-production/quality-gates.md`", ""]
        nouns, ok = {}, True
        body = []
        for t in targets:
            main_only = t == d
            label = "本編" if main_only else os.path.basename(t)
            pre = CR.check(t, main_only=main_only)
            built_file = CR.built_path(CR.sources(t, main_only)[0])
            post = CR.check(t, built=True, main_only=main_only) if os.path.exists(built_file) else None
            st, fa = CS.check(t), CF.check(t)
            for n in pre["nouns"]:
                nouns[n["表記"]] = n
            body += [f"## {label}", "", f"### 2. 読み検査（{pre['sentences']}文）", "", "**ビルド前（原稿）**"]
            body += marks(pre["fails"], {k: v for k, v in NAMES_R.items() if k != "R9"})
            body += ["", "**ビルド後（実際に音声になった読み）**"]
            body += marks(post["fails"], NAMES_R) if post else ["- 未ビルド（ビルド後にもう一度実行する）"]
            body += ["", f"### 3. 数字の確認（数字 {fa['numbers']}個・西暦 {fa['years']}個）", ""] + marks(fa["fails"], CF.NAMES, fa["legacy"])
            body += ["", "### 4. AI臭さ検査（文章・テロップ）", ""] + marks(st["fails"], CS.NAMES, st["legacy"])
            body += ["", "実測：" + "／".join(f"{k} {v}" for k, v in st["stats"].items()), ""]
            ok = ok and pre["pass"] and (post is None or post["pass"]) and st["pass"] and fa["pass"]
            # 表現コード v1 で作った回（expr_record.json がある）は、その検査結果と、使った素材のライセンスも記録する
            er = f"{t}/expr_record.json"
            if os.path.exists(er):
                import json
                e = json.load(open(er, encoding="utf-8"))
                body += ["### 6. 表現コード v1（docs/expression/expression-code.md §0）", ""]
                body += [f"- {'✓' if r['ok'] else '✗'} {r['code']} {r['text']}" for r in e["result"]]
                vp = f"{t}/visual_plan.json"
                used = [v.get("asset") for v in json.load(open(vp, encoding="utf-8")).get("slides", {}).values() if v.get("type") == "photo"] if os.path.exists(vp) else []
                if used:
                    lib = {x["id"]: x for x in json.load(open("_assets/photos/assets.json", encoding="utf-8"))}
                    body += ["", "使った写真（ライセンス台帳 docs/expression/license-ledger.md）：", ""]
                    body += [f"- {i}：{lib[i]['title']}（{lib[i]['license']}・{lib[i]['artist'] or '作者不明'}）{lib[i]['page']}" for i in dict.fromkeys(used) if i in lib]
                body += [""]
                ok = ok and e["pass"]
        out += ["## 1. 固有名詞（この動画に出たもの）", "", "| 表記 | 読み | 種別 | 確認ソース | 確認日 |", "|---|---|---|---|---|"]
        out += [f"| {n['表記']} | {n['読み']} | {n['種別']} | {n['確認ソース']} | {n['確認日'] or '—'} |" for n in nouns.values()] or ["| （固有名詞なし） | | | | |"]
        out += [""] + body
        rec = f"{d}/quality_record.md"
        kept = keep_listening(rec)
        out += [kept] if kept else ["## 5. 耳で確かめる項目（聞いた人が記入）", "",
                                    "機械では判定できない。レビュー便（Drive）で聞いた人が、✓／✗ と気づいた箇所（時刻）を書く。", ""] + \
            [f"- [ ] {k} {t}：未実施" for k, t in V_ITEMS]
        out += ["", f"**機械検査の結果：{'PASS' if ok else 'FAIL'}**", ""]
        open(rec, "w", encoding="utf-8").write("\n".join(out))
        print(f"{rec}: {'PASS' if ok else 'FAIL'}")
        ok_all = ok_all and ok
    sys.exit(0 if ok_all else 1)


NAMES_R = {"R1": "固有名詞の網羅", "R2": "確認ソース", "R3": "辞書登録", "R4": "読みの一致", "R5": "区切れ",
           "R6": "数字の読み", "R7": "英字の読み", "R8": "既知の誤読", "R9": "音声と原稿の一致", "R10": "読みの食い違い"}

if __name__ == "__main__":
    main()
