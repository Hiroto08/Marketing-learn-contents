"""series.py — シリーズ固有の設定（リポジトリ直下の series.json）を各ツールへ渡す共通モジュール。

横展開（別テーマのチャンネル）では series.json だけを書き換える。ツール側にチャンネルID・特典URL・
タグ接頭辞・公開曜日・シリーズ名などを直書きしない（docs/replication-playbook.md）。

    import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    import series as S
    S.NAME, S.CHANNEL_URL, S.tag("ep", 9) …
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "series.json"), encoding="utf-8"))

NAME = CFG["series_name"]
PREFIX = CFG["tag_prefix"]
TOTAL = int(CFG["total_episodes"])

_WD = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
_JA = "月火水木金土日"
PUBLISH_DAYS = {_WD[d] for d in CFG["schedule"]["days"]}          # 0=月 … 6=日
YT_HOUR = int(CFG["schedule"]["youtube_hour_jst"])
NOTE_HOUR = int(CFG["schedule"]["note_hour_jst"])
DAYS_JA = "・".join(_JA[d] for d in sorted(PUBLISH_DAYS))          # 例 "水・土"
CADENCE = f"毎週{DAYS_JA}の{YT_HOUR}時"                             # 例 "毎週水・土の18時"

YT = CFG["youtube"]
CHANNEL_ID = YT["channel_id"]
CHANNEL_URL = f"https://www.youtube.com/channel/{CHANNEL_ID}"
PLAYLIST_URL = f"https://www.youtube.com/playlist?list={YT['master_playlist_id']}" if YT.get("master_playlist_id") else None

NOTE_USER = CFG["note"]["urlname"]
OPTIN_URL = CFG["kit"]["optin_url"]
LEAD_MAGNET = CFG["kit"]["lead_magnet"]

VOICE = CFG["voice"]
VOICE_CREDIT = f"※ナレーションはAI音声合成（{VOICE['engine']}:{VOICE['speaker_name']}）を使用しています。"
BG = CFG["brand"]["bg_color"]


def tag(ep: int, short_n: int = 0) -> str:
    """動画の識別タグ（例 mlab-ep09 / mlab-ep09-s1）"""
    return f"{PREFIX}-ep{ep:02d}" + (f"-s{short_n}" if short_n else "")


SERIES_TAG = f"{PREFIX}-series"
TAG_RE = re.compile(rf"^{re.escape(PREFIX)}-ep(\d{{2}})(?:-s(\d+))?$")   # タグ → (ep, short_n)
MARK_RE = re.compile(rf"{re.escape(PREFIX)}-ep(\d{{2}})")               # Kit の description 目印


# ── 第2シリーズ（売れる仕組みの裏側）：Shorts単独 uNN ／ 本編ケースファイル cNN ─────────
S2 = CFG.get("series2") or {}
S2_NAME = S2.get("name", "")
S2_DIR = S2.get("dir", "s2_ura")
S2_TAG = f"{PREFIX}-{S2.get('key', 's2')}"
S2_HOUR = int(S2.get("youtube_hour_jst", YT_HOUR))
_S2_ITEM_RE = re.compile(rf"^({re.escape(S2.get('short_prefix', 'u'))}|{re.escape(S2.get('case_prefix', 'c'))})(\d{{2}})_")
S2_TAG_RE = re.compile(rf"^{re.escape(PREFIX)}-([uc])(\d{{2}})$")   # タグ → (kind u/c, no)


def s2_item(dirname: str):
    """ディレクトリ名 u01_xxx / c01_xxx → ("u"|"c", 1)。第2シリーズでなければ None"""
    m = _S2_ITEM_RE.match(os.path.basename(dirname.rstrip("/")))
    return (m.group(1), int(m.group(2))) if m else None


def tags_for_dir(dirname: str, short_n: int = 0) -> list:
    """動画の識別タグ一式。epNN_* は従来どおり、uNN_*/cNN_* は第2シリーズのタグ"""
    it = s2_item(dirname)
    if it:
        return [S2_TAG, f"{PREFIX}-{it[0]}{it[1]:02d}"]
    ep = int(re.search(r"ep(\d+)", os.path.basename(dirname.rstrip("/"))).group(1))
    return [SERIES_TAG, tag(ep, short_n)]
