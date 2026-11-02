#!/usr/bin/env python3
"""エピソードのサムネイルPNG(1280x720)を自動生成する。

    python3 _tools/publish/make_thumbnail.py <episode_dir> [--main TEXT] [--sub TEXT] [--out PNG]

テキストの出どころ（優先順）:
  1. CLI --main / --sub
  2. <episode_dir>/thumbnail.md の「## サムネ生成データ」ブロック（main: / sub: 行）
  3. thumbnail.md の「## メインテキスト…」「## サブテキスト…」セクションの採用行
     （**採用：** X ／ **候補A（採用）：** X ／ 最初の **太字** ／ 最初の箇条書き の順で解決）

デザインはシリーズ共通（背景#0B1220・バッジ・Noto Sans JP Black）で、
アクセント色は slide.html の :root { --accent:... } から自動取得する。
数字＋単位（% 倍 割 円 万 億 人 段階 店舗 分）はアクセント色で強調される。

出力先は既定で <episode_dir>/thumbnail.png（コミット対象。コンテナ再作成後も残す）。
アップロード時の自動設定は upload_youtube.py 側が行う。
"""
import argparse
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import series as S  # noqa: E402  シリーズ固有の値（series.json）

W, H = 1280, 720


def _accent(ep_dir: str) -> str:
    html = open(f"{ep_dir}/slide.html", encoding="utf-8").read()
    m = re.findall(r":root\s*\{\s*--accent:\s*(#[0-9A-Fa-f]{6})", html)
    return m[-1] if m else "#FFD54F"


def _episode_no(ep_dir: str) -> str:
    m = re.search(r"ep(\d+)", os.path.basename(ep_dir.rstrip("/")))
    return str(int(m.group(1))) if m else "?"


def _section(md: str, prefix: str) -> str:
    m = re.search(rf"^## {prefix}[^\n]*\n(.*?)(?=\n## |\Z)", md, re.S | re.M)
    return m.group(1) if m else ""


def _pick(body: str) -> str | None:
    for pat in [r"\*\*採用：\*\*\s*(.+)", r"\*\*候補A（採用）：\*\*\s*(.+)",
                r"\*\*(.+?)\*\*", r"^- (.+)$"]:
        m = re.search(pat, body, re.M)
        if m:
            t = m.group(1).strip()
            # 「**候補A：** X」形式のラベルは値ではないので中身を再解決
            if t.startswith("候補") and "：" in t:
                continue
            return re.sub(r"\*\*", "", t).strip()
    return None


def texts_from_md(ep_dir: str) -> tuple[str | None, str | None]:
    p = f"{ep_dir}/thumbnail.md"
    if not os.path.exists(p):
        return None, None
    md = open(p, encoding="utf-8").read()
    gen = _section(md, "サムネ生成データ")
    if gen:
        gm = re.search(r"^main:\s*(.+)$", gen, re.M)
        gs = re.search(r"^sub:\s*(.+)$", gen, re.M)
        return (gm.group(1).strip() if gm else None,
                gs.group(1).strip() if gs else None)
    main = _pick(_section(md, "メインテキスト"))
    sub_body = _section(md, "サブテキスト")
    sub = None
    if sub_body:
        m = re.search(r"\*\*候補A：\*\*\s*(.+)", sub_body)
        sub = m.group(1).strip() if m else _pick(sub_body)
    return main, sub


def _hi(text: str, cls: str = "acc") -> str:
    """数字と単位をアクセント色スパンで包む"""
    return re.sub(r"([0-9０-９][0-9０-９.,．]*)(%|％|倍|割|円|万|億|人|段階|店舗|分)?",
                  lambda m: f'<span class="{cls}">{m.group(1)}{m.group(2) or ""}</span>', text)


USABLE = 1150  # 左右パディングを除いた実効幅


def _split_two_lines(text: str) -> list[str]:
    """自然な切れ目（、・空白・助詞境界）で2行に分ける。無ければ中央で割る"""
    n = len(text)
    cands = [m.end() for m in re.finditer(r"[、。・\s]", text)]
    cands += [m.end() for m in re.finditer(r"[はがをにでとのも]", text) if 2 <= m.end() < n - 1]
    if not cands:
        return [text[:(n + 1) // 2], text[(n + 1) // 2:]]
    mid = min(cands, key=lambda i: abs(i - n / 2))
    return [text[:mid].rstrip("、 "), text[mid:]]


def render_html(no: str, accent: str, main: str, sub: str | None) -> str:
    main_len = len(re.sub(r"\s", "", main))
    if main_len <= 9:
        lines = [main]
    else:
        lines = _split_two_lines(main)
    longest = max(len(re.sub(r"\s", "", l)) for l in lines)
    size = min(190, int(USABLE / max(longest, 1)))
    main_html = "<br>".join(_hi(l) for l in lines)
    sub_html = f'<div class="sub">{_hi(sub)}</div>' if sub else ""
    return f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Noto Sans JP','Noto Sans CJK JP',sans-serif;color:#EEEEF8}}
#t{{position:relative;width:{W}px;height:{H}px;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:34px;padding:0 60px;
  background:radial-gradient(ellipse at 78% 20%, {accent}2E 0%, transparent 52%),
             linear-gradient(135deg,#0B1220 0%,#101830 62%,#0B1220 100%)}}
.badge{{position:absolute;top:36px;left:44px;font-weight:900;font-size:40px;
  color:{accent};border:4px solid {accent};border-radius:999px;padding:.18em .8em}}
.series{{position:absolute;top:48px;right:48px;font-weight:500;font-size:30px;color:#B8BEDD}}
.main{{font-weight:900;font-size:{size}px;line-height:1.14;text-align:center;
  white-space:nowrap;text-shadow:0 6px 30px rgba(0,0,0,.6)}}
.main .acc{{color:{accent};text-shadow:0 0 44px {accent}59}}
.sub{{font-weight:900;font-size:52px;line-height:1.3;text-align:center;color:#D9DCEF;
  border-top:3px solid {accent}66;padding-top:26px}}
.sub .acc{{color:{accent}}}
.bar{{position:absolute;left:0;bottom:0;width:100%;height:14px;
  background:linear-gradient(90deg,{accent},{accent}00 82%)}}
</style></head><body><div id="t">
  <div class="badge">第{no}回</div>
  <div class="series">{S.NAME}</div>
  <div class="main">{main_html}</div>
  {sub_html}
  <div class="bar"></div>
</div></body></html>"""


def _casefile(ep_dir: str):
    """シーズン2（casefile プロファイル）なら (case_no, subject) を返す。それ以外は None"""
    html = open(f"{ep_dir}/slide.html", encoding="utf-8").read()
    if 'name="episode-profile" content="casefile"' not in html:
        return None
    import ast
    spec = ast.literal_eval(open(f"{ep_dir}/casefile_spec.py", encoding="utf-8").read())
    return spec["case_no"], spec["subject"]


def render_casefile_html(case_no: str, subject: str, accent: str, main: str, sub: str | None) -> str:
    """シーズン2「売れる仕組みの裏側」のサムネ（墨色×明朝×紙の証拠カード）"""
    # main の [語] はキーイエローで強調（例「客より[店]で稼ぐ」）
    plain = re.sub(r"[\[\]]", "", main)
    lines = [main] if len(re.sub(r"\s", "", plain)) <= 8 else _split_two_lines(main)
    longest = max(len(re.sub(r"[\s\[\]]", "", l)) for l in lines)
    size = min(170, int(1080 / max(longest, 1)))
    main_html = "<br>".join(re.sub(r"\[(.+?)\]", r'<span class="acc">\1</span>', _hi(l)) for l in lines)
    card = (f'<div class="card"><div class="sub">{_hi(sub, "acc2")}</div><div class="stamp">有報で確認</div></div>'
            if sub else "")
    return f"""<!DOCTYPE html><html lang="ja"><head><meta charset="UTF-8"><style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;font-family:'Noto Sans JP','Noto Sans CJK JP',sans-serif}}
#t{{position:relative;width:{W}px;height:{H}px;padding:44px 56px;color:#F1EFEA;
  background:radial-gradient(ellipse 70% 80% at 30% 40%, rgba(255,255,255,.06) 0%, transparent 70%),
             radial-gradient(ellipse 120% 100% at 50% 50%, transparent 55%, rgba(0,0,0,.6) 100%),#111216}}
#t::before{{content:'';position:absolute;inset:0;opacity:.5;
  background-image:linear-gradient(rgba(255,255,255,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.06) 1px,transparent 1px);
  background-size:64px 64px}}
.badge{{position:relative;display:inline-flex;align-items:center;gap:14px;font-family:'Inter','Noto Sans CJK JP',sans-serif;
  font-weight:900;font-size:30px;letter-spacing:.28em;color:{accent};border:3px solid {accent};padding:8px 20px;border-radius:4px}}
.dot{{width:16px;height:16px;border-radius:50%;background:#E5484D;box-shadow:0 0 14px #E5484D}}
.subj{{position:relative;font-family:'Noto Serif CJK JP',serif;font-weight:700;font-size:58px;margin-top:16px;color:#F1EFEA}}
.main{{position:relative;font-family:'Noto Serif CJK JP',serif;font-weight:700;font-size:{size}px;line-height:1.12;
  margin-top:26px;white-space:nowrap;text-shadow:0 8px 34px rgba(0,0,0,.7)}}
.main .acc{{color:#FFD54F}}
.card{{position:absolute;right:52px;bottom:54px;background:#F3EEE4;color:#1D1E23;border-radius:6px;padding:22px 30px 24px;
  rotate:-2deg;box-shadow:0 22px 44px rgba(0,0,0,.6)}}
.sub{{font-weight:900;font-size:50px;line-height:1.2}}
.sub .acc2{{color:#B4531E}}
.stamp{{position:absolute;right:-22px;top:-34px;font-family:'Noto Serif CJK JP',serif;font-weight:700;font-size:30px;color:#E5484D;
  border:5px solid #E5484D;border-radius:8px;padding:2px 12px;rotate:-10deg;background:rgba(243,238,228,.85)}}
.series{{position:absolute;left:58px;bottom:50px;font-weight:700;font-size:26px;letter-spacing:.2em;color:#B9B4AA}}
.bar{{position:absolute;left:0;top:0;width:100%;height:12px;background:linear-gradient(90deg,{accent},{accent}00 80%)}}
</style></head><body><div id="t">
  <div class="bar"></div>
  <div class="badge"><span class="dot"></span>CASE FILE {case_no}</div>
  <div class="subj">{subject}</div>
  <div class="main">{main_html}</div>
  {card}
  <div class="series">売れる仕組みの裏側</div>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode_dir")
    ap.add_argument("--main")
    ap.add_argument("--sub")
    ap.add_argument("--out")
    a = ap.parse_args()
    ep = a.episode_dir.rstrip("/")
    md_main, md_sub = texts_from_md(ep)
    main_text = a.main or md_main
    sub_text = a.sub if a.sub is not None else md_sub
    if not main_text:
        sys.exit(f"メインテキストが見つからない: {ep}/thumbnail.md を確認するか --main を指定")
    out = a.out or f"{ep}/thumbnail.png"

    cf = _casefile(ep)
    html = (render_casefile_html(cf[0], cf[1], _accent(ep), main_text, sub_text) if cf
            else render_html(_episode_no(ep), _accent(ep), main_text, sub_text))
    tmp = f"{out}.src.html"
    open(tmp, "w", encoding="utf-8").write(html)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": W, "height": H})
        page.goto(f"file://{os.path.abspath(tmp)}")
        page.wait_for_timeout(300)
        page.screenshot(path=out)
        b.close()
    os.remove(tmp)
    print(f"thumbnail: {out}  main=「{main_text}」 sub=「{sub_text or '(なし)'}」")


if __name__ == "__main__":
    main()
