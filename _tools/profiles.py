"""profiles.py — 動画フォーマットのプロファイル（検査・後処理の数値基準）を1か所で定義する。

本編:  slide.html に <meta name="episode-profile" content="casefile"> があればシーズン2
       「ケースファイル」形式。無ければ従来の18枚・8分形式（standard）。
Shorts: stage.html に <meta name="shorts-profile" content="s2"> があればシーズン2形式。

数値の根拠は docs/post-series-strategy.md v0.2 §3.2・§4（ケースファイル＝10〜12枚・5:00〜7:30、
裏側ショート＝30〜50秒を目安。上限は Shorts の早送り離脱を避けて45秒に置く）。
"""
import re

EPISODE = {
    # slides: 許容枚数 / est_min・est_max: verify の推定尺(秒) / final_min: 完成動画の最低尺(秒)
    "standard": {"slides": (18, 18), "est_min": 495, "est_max": None, "final_min": 480,
                 "label": "18枚・推定8:15以上"},
    "casefile": {"slides": (10, 12), "est_min": 305, "est_max": 465, "final_min": 285,
                 "label": "10〜12枚・推定5:05〜7:45"},
}

SHORTS = {
    "standard": {"dur": (15, 30), "slides": (4, 6), "chars": 150, "slide_chars": 45},
    "s2":       {"dur": (20, 45), "slides": (4, 7), "chars": 230, "slide_chars": 60},
}


def episode_profile(html: str) -> tuple[str, dict]:
    m = re.search(r'<meta\s+name="episode-profile"\s+content="([a-z0-9-]+)"', html)
    name = m.group(1) if m and m.group(1) in EPISODE else "standard"
    return name, EPISODE[name]


def shorts_profile(html: str) -> tuple[str, dict]:
    m = re.search(r'<meta\s+name="shorts-profile"\s+content="([a-z0-9-]+)"', html)
    name = m.group(1) if m and m.group(1) in SHORTS else "standard"
    return name, SHORTS[name]
