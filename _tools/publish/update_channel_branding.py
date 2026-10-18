#!/usr/bin/env python3
"""channels.update brandingSettings: 既存値を取得→description/keywords/country だけ差し替えて送り返す（他は保持）"""
import json, sys, urllib.request
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
from yt_index import API, api, token  # noqa: E402
sys.path.insert(0, __import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), ".."))
import series as S  # noqa: E402  シリーズ固有の値（series.json）

DESC = S.YT["channel_description"]   # series.json の youtube.channel_description
KW = S.YT["channel_keywords"]

tok = token()
dry = "--dry-run" in sys.argv
ch = api(tok, "channels", {"part": "brandingSettings", "mine": "true"})["items"][0]
bs = ch["brandingSettings"]
print("BEFORE:", json.dumps(bs, ensure_ascii=False)[:600])
bs.setdefault("channel", {})
bs["channel"].update({"description": DESC, "keywords": KW, "country": S.YT["country"], "defaultLanguage": S.YT["default_language"]})
assert len(DESC) <= 1000 and len(KW) <= 500, (len(DESC), len(KW))
if dry:
    sys.exit(f"[dry] desc={len(DESC)} kw={len(KW)}")
req = urllib.request.Request(f"{API}/channels?part=brandingSettings", method="PUT",
                             data=json.dumps({"id": ch["id"], "brandingSettings": bs}).encode(),
                             headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
r = json.load(urllib.request.urlopen(req, timeout=30))
print("AFTER:", json.dumps(r["brandingSettings"]["channel"], ensure_ascii=False)[:300])
