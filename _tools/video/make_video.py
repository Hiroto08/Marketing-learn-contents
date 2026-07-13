#!/usr/bin/env python3
"""
make_video.py — Generalized slide-to-video builder for Marketing-learn-contents.

Reads a slide.html that exports NARRATIONS / STEPS / SLIDES_META / TOTAL_SECS,
generates VOICEVOX narration audio (with natural breath pauses), records each slide
via Playwright, then assembles a final MP4.

Usage:
  python3 make_video.py <slide.html> [options]

Options:
  --out DIR           Output directory  (default: ./video_out)
  --speaker INT       VOICEVOX speaker ID (default: 11 = 玄野武宏 ノーマル)
  --speed FLOAT       TTS speed scale  (default: 1.1)
  --lead FLOAT        Animations finish this many seconds before the paragraph
                      narration starts (default: 1.0)
  --step-gap FLOAT    Extra gap between consecutive steps in a group (default: 0.35)
  --intro FLOAT       Hold before first animation per slide (default: 0.6)
  --outro FLOAT       Tail silence after narration ends per slide (default: 1.0)
  --final-outro FLOAT Tail hold after the very last narration ends (default: 3.0)
  --sent-gap FLOAT    Silence inserted between sentences (。！？) (default: 0.28)
  --para-gap FLOAT    Silence inserted between paragraphs (\\n) (default: 0.45)
  --slide INT         Process only this slide index (0-based); repeat to specify multiple
  --no-record         TTS only — skip Playwright recording
  --voicevox-url URL  VOICEVOX endpoint (default: http://127.0.0.1:50021)
  --width INT         Viewport width  (default: 1280)
  --height INT        Viewport height (default: 720)
  --crf INT           ffmpeg x264 CRF (default: 18)
"""

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from multiprocessing import Process
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Slide → video builder")
    p.add_argument("slide_html", help="Path to slide.html")
    p.add_argument("--out",          default="video_out")
    p.add_argument("--speaker",      type=int,   default=11,
                   help="VOICEVOX speaker ID (11=玄野武宏 ノーマル)")
    p.add_argument("--speed",        type=float, default=1.1)
    p.add_argument("--lead",         type=float, default=1.2,
                   help="Seconds each step fires before its narration moment (slightly early feels natural)")
    p.add_argument("--step-gap",     type=float, default=0.35, dest="step_gap",
                   help="Gap between consecutive steps (s)")
    p.add_argument("--intro",        type=float, default=0.6,
                   help="Hold before first step (s)")
    p.add_argument("--outro",        type=float, default=1.0,
                   help="Tail silence after narration (s)")
    p.add_argument("--final-outro",  type=float, default=3.0, dest="final_outro",
                   help="Tail hold after the last slide's narration (s)")
    p.add_argument("--sent-gap",     type=float, default=0.28, dest="sent_gap",
                   help="Breath pause between sentences (。！？) (s)")
    p.add_argument("--para-gap",     type=float, default=0.45, dest="para_gap",
                   help="Pause between paragraphs (\\n) (s)")
    p.add_argument("--slide",        type=int,   action="append", dest="only_slides",
                   help="Only process this slide index (may repeat)")
    p.add_argument("--no-record",    action="store_true")
    p.add_argument("--voicevox-url", default="http://127.0.0.1:50021", dest="voicevox_url")
    p.add_argument("--width",        type=int,   default=1280)
    p.add_argument("--height",       type=int,   default=720)
    p.add_argument("--crf",          type=int,   default=18)
    p.add_argument("--bgm",          default="",
                   help="BGM wav/mp3 to loop under the narration (e.g. _assets/audio/bgm_calm_loop.wav)")
    p.add_argument("--bgm-db",       type=float, default=-21.0, dest="bgm_db",
                   help="BGM gain in dB relative to source (default -21)")
    p.add_argument("--sfx-dir",      default="", dest="sfx_dir",
                   help="Dir containing sfx_whoosh/sfx_pop/sfx_ding.wav; enables SFX on slide transitions and pop/scale reveals")
    p.add_argument("--sfx-db",       type=float, default=-17.0, dest="sfx_db",
                   help="SFX gain in dB (default -17)")
    return p.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
# Text utilities
# ──────────────────────────────────────────────────────────────────────────────

ABBR_MAP = {
    "AMA":  "エーエムエー",  "SNS":  "エスエヌエス",  "AI":   "エーアイ",
    "PR":   "ピーアール",    "HBR":  "エイチビーアール", "HBS": "エイチビーエス",
    "JTBD": "ジェイティービーディー", "STP": "エスティーピー",
    "KPI":  "ケーピーアイ",  "CPA":  "シーピーエー",   "LTV":  "エルティーブイ",
    "CTR":  "シーティーアール", "CVR": "シーブイアール", "ROI":  "アールオーアイ",
    "ROAS": "アールオーエーエス", "SEO": "エスイーオー", "CRM":  "シーアールエム",
    "UGC":  "ユージーシー",
    "3C":   "サンシー",        "4P":   "ヨンピー",      "4C":   "ヨンシー",
    "AIDMA": "アイドマ",       "AISAS": "アイサス",
    "USP":  "ユーエスピー",   "CAC":  "シーエーシー",
    "AB":   "エービー",       "CTA":  "シーティーエー", "EC":   "イーシー",
    "GA4":  "ジーエーフォー", "URL":  "ユーアールエル", "VWO":  "ブイダブリューオー",
    "RAG":  "ラグ",
    "NPS":  "エヌピーエス",  "CSV":  "シーエスブイ",
    "5A":   "ファイブエー",  "SaaS": "サース",
    "D2C":  "ディーツーシー",
    "Airbnb": "エアビー",    # ×エアブンブ
    "QB":   "キュービー",    # ×キュビ等の分割読み防止（QBハウス、EP02）
}

# Compound terms read as ONE accent phrase (prevents double/triple-hump
# intonation like "エスティー↗ピー↗ブンセキ↗"). Keyed by the POST-clean_for_tts
# surface (i.e. after ABBR_MAP katakana substitution). Each value is
# (katakana_pronunciation, accent_type) where accent_type = mora index of the
# pitch drop (0 = 平板/heiban). Seeded into the VOICEVOX user dictionary at
# startup. Accent values are ear-tuned; adjust if a term sounds off.
COMPOUND_DICT = {
    "サンシー分析":        ("サンシーブンセキ", 5),       # 3C分析
    "エスティーピー分析":  ("エスティーピーブンセキ", 6),  # STP分析
    "ヨンピー分析":        ("ヨンピーブンセキ", 4),        # 4P分析
    "ヨンシー分析":        ("ヨンシーブンセキ", 4),        # 4C分析
    "一方向":              ("イチホウコウ", 0),            # いちほうこう（×いっぽうこう）
    "高級品":              ("コウキュウヒン", 0),          # こうきゅうひん（×こうきゅうしな）
    "三方良し":            ("サンポウヨシ", 4),            # さんぽうよし（×さんぽういし）
    "ヨンシー":            ("ヨンシー", 2),                # 4C：ヨンシー（×ヨンスィイ）。4Pの「ヨンピー」と韻を揃える
    "サンシー":            ("サンシー", 2),                # 3C単独（×サンスィイ。「3C分析」は上の複合語が先に効く）
    "キュービーハウス":    ("キュービーハウス", 5),        # QBハウス（×キュ'ウ/ビ'イ/ハ'ウスの3分割読み）
    "日本中":              ("ニッポンジュウ", 0),          # にっぽんじゅう（×にっぽんちゅう）
    "顔剃り":              ("カオソリ", 0),                # かおそり（×カオ/ソリの分割読み）
    "小西國義":            ("コニシクニヨシ", 5),          # QBハウス創業者（×クニ/ヨシの分割読み）
    "遠山正道":            ("トオヤママサミチ", 4),         # Soup Stock Tokyo創業者（正道を×せいどう→まさみち）
    "坂本孝":              ("サカモトタカシ", 5),           # ブックオフ／俺の株式会社創業者（孝を×こう→たかし）
}

MARU_MAP = {
    "①": "いちつめ、", "②": "ふたつめ、", "③": "みっつめ、",
    "④": "よっつめ、", "⑤": "いつつめ、", "⑥": "むっつめ、",
}


def clean_for_tts(text: str) -> str:
    t = text
    t = t.replace("——", "、").replace("―", "、").replace("─", "、")
    t = t.replace("→", "から")
    for abbr, kana in ABBR_MAP.items():
        t = re.sub(r'(?<![A-Za-z])' + abbr + r'(?![A-Za-z])', kana, t)
    t = re.sub(r'(\d)\s*[〜～]\s*(\d)', r'\1から\2', t)
    for k, v in MARU_MAP.items():
        t = t.replace(k, v)
    # ・ between katakana = foreign name separator → silent (ピーター・ドラッカー)
    # ・ elsewhere = list separator → 、 (名前・年齢・職業 → 名前、年齢、職業)
    t = re.sub(r'(?<=[ァ-ヶー])・(?=[ァ-ヶー])', '', t)
    t = t.replace("・", "、")
    # 「A」「B」のように引用符が隣接する列挙は、除去すると無ポーズで連結読みになる。
    # 隣接境界に読点を入れてから引用符を除去する（句読点で既に区切れる場合は影響なし）。
    t = t.replace("」「", "、").replace("』『", "、")
    t = t.replace("「", "").replace("」", "").replace("『", "").replace("』", "")
    t = re.sub(r'\b(19|20)(\d{2})(年(?:代)?)', r'\2\3', t)
    t = re.sub(r'[（）\(\)]', '', t)
    t = re.sub(r'\s{2,}', ' ', t)
    return t.strip()


def split_sentences(text: str) -> list:
    """Split at 。！？ keeping punctuation with each sentence."""
    parts = re.split(r'(?<=[。！？])\s*', text)
    return [p.strip() for p in parts if p.strip()]


def split_paragraphs(text: str) -> list:
    """Split on \\n (as stored in JS template literals)."""
    return [p.strip() for p in text.split('\n') if p.strip()]


# ──────────────────────────────────────────────────────────────────────────────
# Slide data extraction
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class SlideMeta:
    id: str
    start: float
    end: float


@dataclass
class Step:
    si: int
    t: float
    anim: str = ""


@dataclass
class SlideData:
    meta: list
    steps: list
    narrations: list
    total_secs: float
    step_texts: list = None   # per-step visible text (for narration sync)


def _element_text(src: str, elem_id: str) -> str:
    """Rough visible text of the element with the given id (for keyword
    matching only — nested tags are stripped, capture window is bounded)."""
    m = re.search(r'id="' + re.escape(elem_id) + r'"', src)
    if not m:
        return ""
    gt = src.find(">", m.end())          # skip the rest of the opening tag
    if gt < 0:
        return ""
    seg = src[gt + 1:gt + 601]
    nxt = re.search(r'\sid="|<section\b', seg)
    if nxt:
        seg = seg[:nxt.start()]
    seg = re.sub(r"<[^>]+>", " ", seg)
    seg = re.sub(r"&[a-z]+;", " ", seg)
    return re.sub(r"\s+", " ", seg).strip()


def extract_slide_data(html_path: str) -> SlideData:
    with open(html_path, encoding="utf-8") as f:
        src = f.read()

    m = re.search(r'const NARRATIONS\s*=\s*\[(.*?)\];', src, re.DOTALL)
    if not m:
        raise ValueError("NARRATIONS not found in slide.html")
    narrations = [t.replace('\\n', '\n').strip()
                  for t in re.findall(r'`(.*?)`', m.group(1), re.DOTALL)]

    m = re.search(r'const STEPS\s*=\s*\[(.*?)\];', src, re.DOTALL)
    if not m:
        raise ValueError("STEPS not found")
    steps = []
    step_texts = []
    for e in re.finditer(r'\{[^}]+\}', m.group(1)):
        si_m = re.search(r'si\s*:\s*(\d+)', e.group(0))
        t_m  = re.search(r'\bt\s*:\s*([\d.]+)', e.group(0))
        an_m = re.search(r"anim\s*:\s*'([a-z-]+)'", e.group(0))
        ids_m = re.search(r"ids\s*:\s*\[([^\]]*)\]", e.group(0))
        if si_m and t_m:
            steps.append(Step(si=int(si_m.group(1)), t=float(t_m.group(1)),
                              anim=an_m.group(1) if an_m else ""))
            ids = re.findall(r"'([^']+)'", ids_m.group(1)) if ids_m else []
            step_texts.append(" ".join(_element_text(src, i) for i in ids))

    m = re.search(r'const SLIDES_META\s*=\s*\[(.*?)\];', src, re.DOTALL)
    if not m:
        raise ValueError("SLIDES_META not found")
    meta = []
    for e in re.finditer(r'\{[^}]+\}', m.group(1)):
        id_m    = re.search(r"id\s*:\s*'([^']+)'", e.group(0))
        start_m = re.search(r'start\s*:\s*([\d.]+)', e.group(0))
        end_m   = re.search(r'end\s*:\s*([\d.]+)', e.group(0))
        if id_m and start_m and end_m:
            meta.append(SlideMeta(id=id_m.group(1),
                                  start=float(start_m.group(1)),
                                  end=float(end_m.group(1))))

    m = re.search(r'const TOTAL_SECS\s*=\s*([\d.]+)', src)
    total = float(m.group(1)) if m else (meta[-1].end if meta else 0)

    return SlideData(meta=meta, steps=steps, narrations=narrations,
                     total_secs=total, step_texts=step_texts)


# ──────────────────────────────────────────────────────────────────────────────
# VOICEVOX TTS with natural breath pauses
# ──────────────────────────────────────────────────────────────────────────────

def _compound_salt(text: str) -> str:
    """Cache-busting salt for sentences containing a compound term.

    Empty when no compound is present, so non-compound audio keeps its existing
    cache key (backward compatible). Changes whenever a matched term's reading
    or accent changes in COMPOUND_DICT, forcing only the affected items to
    re-synthesize. `text` should be the post-clean_for_tts surface.
    """
    hits = [f"{s}={p}:{a}" for s, (p, a) in COMPOUND_DICT.items() if s in text]
    return ";".join(sorted(hits))


def _tts_cache_key(text: str, speaker: int, speed: float, salt: str = "") -> str:
    extra = f"|{salt}" if salt else ""
    return hashlib.md5(f"{text}|{speaker}|{speed:.3f}{extra}".encode()).hexdigest()


def seed_user_dict(url: str) -> None:
    """Register COMPOUND_DICT terms into the VOICEVOX user dictionary so each
    is tokenized as a single morpheme = a single accent phrase. Idempotent:
    removes any prior entries for the same surfaces, then re-registers."""
    managed = set(COMPOUND_DICT)
    try:
        with urllib.request.urlopen(f'{url}/user_dict', timeout=10) as r:
            current = json.load(r)
        for uid, word in current.items():
            if word.get('surface') in managed:
                urllib.request.urlopen(urllib.request.Request(
                    f'{url}/user_dict_word/{uid}', method='DELETE'), timeout=10)
    except Exception as e:
        print(f"  (user_dict pre-clean skipped: {e})")
    n = 0
    for surface, (pron, accent) in COMPOUND_DICT.items():
        qs = urllib.parse.urlencode({
            'surface': surface, 'pronunciation': pron,
            'accent_type': accent, 'word_type': 'PROPER_NOUN', 'priority': 10})
        try:
            urllib.request.urlopen(urllib.request.Request(
                f'{url}/user_dict_word?{qs}', method='POST'), timeout=10)
            n += 1
        except Exception as e:
            print(f"  (user_dict register failed for {surface}: {e})")
    if n:
        print(f"  user_dict: {n} compound term(s) registered")


def _tts_sentence(text: str, out_path: str, speaker: int, speed: float, url: str):
    clean = clean_for_tts(text)
    if not clean:
        return
    q = urllib.parse.urlencode({'text': clean, 'speaker': speaker})
    req = urllib.request.Request(f'{url}/audio_query?{q}', method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        query = json.load(r)
    query['speedScale'] = speed
    query['outputSamplingRate'] = 24000
    req = urllib.request.Request(
        f'{url}/synthesis?speaker={speaker}',
        data=json.dumps(query).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=120) as r:
        with open(out_path, 'wb') as f:
            f.write(r.read())


def _make_silence(path: str, duration: float, sr: int = 24000):
    subprocess.run(
        ['ffmpeg', '-y', '-f', 'lavfi',
         '-i', f'anullsrc=channel_layout=mono:sample_rate={sr}',
         '-t', str(duration), path],
        capture_output=True, check=True)


def _has_video_stream(path: str) -> bool:
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return False
    out = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-select_streams', 'v', '-show_entries',
         'stream=codec_type', '-of', 'csv=p=0', path],
        capture_output=True, text=True).stdout
    return 'video' in out


def get_duration(path: str) -> float:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', path],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def _concat_wavs(parts: list, out_path: str):
    n = len(parts)
    if n == 0:
        return
    if n == 1:
        shutil.copy(parts[0], out_path)
        return
    inputs = []
    for p in parts:
        inputs += ['-i', p]
    filt = ''.join(f'[{i}:a]' for i in range(n)) + f'concat=n={n}:v=0:a=1[out]'
    subprocess.run(
        ['ffmpeg', '-y'] + inputs + ['-filter_complex', filt, '-map', '[out]', out_path],
        capture_output=True, check=True)


def gen_narration_audio(narration_text, out_wav, cache_dir,
                        speaker, speed, voicevox_url, sent_gap, para_gap):
    """
    Synthesize one slide's narration with natural breath pauses.

    Splits at \\n → paragraphs, then at 。！？ → sentences.
    Each sentence is synthesized individually (sentence-level cache).
    Sentences are joined with sent_gap silence; paragraphs with para_gap.

    Returns per-paragraph audio durations (gaps within a paragraph included,
    para_gap between paragraphs excluded) and writes them to <out_wav>.json
    so the animation schedule can align to real paragraph starts.
    """
    os.makedirs(cache_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="narr_")
    try:
        paragraphs = split_paragraphs(narration_text)
        parts = []
        para_durs = []

        for pi, para in enumerate(paragraphs):
            sentences = split_sentences(para) or [para]
            p_dur = 0.0
            for si, sent in enumerate(sentences):
                clean = clean_for_tts(sent)
                if not clean:
                    continue

                key = _tts_cache_key(clean, speaker, speed,
                                     _compound_salt(clean))
                cached = os.path.join(cache_dir, f'{key}.wav')
                if not os.path.exists(cached):
                    _tts_sentence(sent, cached, speaker, speed, voicevox_url)
                parts.append(cached)
                p_dur += get_duration(cached)

                is_last_sent = (si == len(sentences) - 1)
                is_last_para = (pi == len(paragraphs) - 1)
                if is_last_sent and is_last_para:
                    pass  # caller adds outro
                elif is_last_sent:
                    g = os.path.join(tmp, f'para{pi}.wav')
                    _make_silence(g, para_gap)
                    parts.append(g)
                else:
                    g = os.path.join(tmp, f'sent{pi}_{si}.wav')
                    _make_silence(g, sent_gap)
                    parts.append(g)
                    p_dur += sent_gap
            para_durs.append(p_dur)

        if parts:
            _concat_wavs(parts, out_wav)
        else:
            _make_silence(out_wav, 1.0)

        with open(out_wav + '.json', 'w') as f:
            json.dump({'para_durs': para_durs,
                       'hash': _narr_hash(narration_text, speaker, speed,
                                          sent_gap, para_gap)}, f)
        return para_durs
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def compute_sent_starts(narration_text, cache_dir, speaker, speed,
                        sent_gap, para_gap):
    """Start time and raw text of every sentence in one narration, mirroring
    gen_narration_audio's exact gap layout. Requires the sentence WAVs to be
    cached already (call after gen_tts). Returns [(start_sec, sentence), ...]."""
    out, t = [], 0.0
    paragraphs = split_paragraphs(narration_text)
    for pi, para in enumerate(paragraphs):
        sentences = split_sentences(para) or [para]
        real = [s for s in sentences if clean_for_tts(s)]
        for si, sent in enumerate(real):
            clean = clean_for_tts(sent)
            key = _tts_cache_key(clean, speaker, speed, _compound_salt(clean))
            cached = os.path.join(cache_dir, f'{key}.wav')
            dur = get_duration(cached) if os.path.exists(cached) else len(clean) / 6.8
            out.append((t, sent))
            t += dur
            if si < len(real) - 1:
                t += sent_gap
            elif pi < len(paragraphs) - 1:
                t += para_gap
    return out


_TOKEN_RE = re.compile(r'[0-9]+(?:\.[0-9]+)?|[一-龥]{2,}|[ァ-ヶー]{2,}|[A-Za-z]{2,}')
_SYNC_STOP = {"class", "slide", "section", "style", "span", "div",
              "する", "こと", "ため", "よう"}


def _sync_tokens(text: str):
    """Keywords used to match a step's on-screen text to a narration sentence."""
    t = text.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    t = t.replace(",", "").replace("，", "")
    return [tok for tok in _TOKEN_RE.findall(t) if tok.lower() not in _SYNC_STOP]


def _match_score(tokens, sentence: str) -> int:
    """Weighted overlap: numbers count at least 2 (a matching figure is a
    strong signal even when short, e.g. '6年' or '2.2倍')."""
    s = sentence.translate(str.maketrans("０１２３４５６７８９", "0123456789"))
    s = s.replace(",", "").replace("，", "")
    total = 0
    for tok in set(tokens):
        if tok in s:
            total += max(len(tok), 2) if tok[0].isdigit() else len(tok)
    return total


def _narr_hash(text, speaker, speed, sent_gap, para_gap) -> str:
    clean = clean_for_tts(text)
    salt = _compound_salt(clean)
    # "nk2" suffix invalidates cache for narrations with ・ (v2: katakana→silent, others→、)
    nakaten_salt = "nk2" if "・" in text else ""
    return hashlib.md5(
        f'{text}|{speaker}|{speed:.3f}|{sent_gap:.3f}|{para_gap:.3f}|{salt}|{nakaten_salt}'.encode()
    ).hexdigest()


# ──────────────────────────────────────────────────────────────────────────────
# Schedule builder
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class AnimEvent:
    rel_t: float    # seconds from slide start
    step_idx: int   # index into STEPS


@dataclass
class SlideSchedule:
    si: int
    narration_start: float
    anim_events: list
    audio_dur: float
    total_dur: float


_SYNC_STATS = [0, 0]   # [text-anchored steps, total non-first steps]


def build_schedule(sd, audio_durs, para_durs_list, lead, step_gap,
                   intro, outro, final_outro, para_gap,
                   sent_starts_list=None):
    _SYNC_STATS[0] = _SYNC_STATS[1] = 0
    meta_count = len(sd.meta)
    narr_count = len(sd.narrations)

    slide_steps = [[] for _ in range(meta_count)]
    for gi, step in enumerate(sd.steps):
        if step.si < meta_count:
            slide_steps[step.si].append(gi)

    schedules = []
    for si in range(meta_count):
        ni = min(si, narr_count - 1)
        audio_dur = audio_durs[ni] if ni < len(audio_durs) else 0.0
        narr_text = sd.narrations[ni] if ni < narr_count else ""
        durs = para_durs_list[ni] if ni < len(para_durs_list) else []
        gsteps = slide_steps[si]
        S = len(gsteps)
        P = max(1, len(durs) or len(split_paragraphs(narr_text)))

        # Real start time of each paragraph within the narration audio
        para_start = [sum(durs[:k]) + k * para_gap if k < len(durs)
                      else audio_dur * k / P
                      for k in range(P)]

        narration_start = intro
        anim_events = []

        if si == 0:
            # Title slide: shown fully from the first frame (no step animations)
            pass
        elif S > 0:
            # Narration-synced reveal (content-matched):
            #   1. step 0 → slide start (heading visible immediately)
            #   2. each later step anchors to the START of the narration
            #      sentence whose text best matches the step's on-screen text
            #      (monotonic search — STEPS order = speaking order)
            #   3. unmatched steps interpolate between neighboring anchors
            # Every step fires `lead` seconds before its sentence and never
            # later than 1s before the narration ends.
            sents = (sent_starts_list[ni] if sent_starts_list
                     and ni < len(sent_starts_list) else [])
            anchors = [None] * S           # narration-relative anchor seconds
            anchors[0] = -narration_start  # fires at rel_t 0 after offset below
            ptr = 0
            for m in range(1, S):
                text = (sd.step_texts[gsteps[m]]
                        if sd.step_texts and gsteps[m] < len(sd.step_texts) else "")
                toks = _sync_tokens(text)
                best, best_score = None, 1   # require score >= 2
                for sj in range(ptr, len(sents)):
                    sc = _match_score(toks, sents[sj][1]) if toks else 0
                    if sc > best_score:
                        best, best_score = sj, sc
                if best is not None:
                    anchors[m] = sents[best][0]
                    ptr = best               # later steps may share this sentence
            # interpolate the unmatched between known anchors / audio end
            known = [(m, a) for m, a in enumerate(anchors) if a is not None]
            known.append((S, max(audio_dur - 1.0, 0.0)))
            for (m0, a0), (m1, a1) in zip(known, known[1:]):
                for m in range(m0 + 1, m1):
                    anchors[m] = a0 + (a1 - a0) * (m - m0) / (m1 - m0)
            matched = sum(1 for m in range(1, S)
                          if anchors[m] is not None and any(
                              anchors[m] == s for s, _ in sents))
            _SYNC_STATS[0] += matched
            _SYNC_STATS[1] += max(S - 1, 0)
            for m, gi in enumerate(gsteps):
                t = narration_start + anchors[m] - (lead if m else 0.0)
                t = min(t, narration_start + max(audio_dur - 1.0, 0.0))
                t = max(t, 0.0 if m == 0 else step_gap * m)
                if anim_events and t < anim_events[-1].rel_t + 0.3:
                    t = anim_events[-1].rel_t + 0.3
                anim_events.append(AnimEvent(rel_t=t, step_idx=gi))

        tail = final_outro if si == meta_count - 1 else outro
        schedules.append(SlideSchedule(
            si=si,
            narration_start=narration_start,
            anim_events=sorted(anim_events, key=lambda e: e.rel_t),
            audio_dur=audio_dur,
            total_dur=narration_start + audio_dur + tail,
        ))
    return schedules


# ──────────────────────────────────────────────────────────────────────────────
# Recording
# ──────────────────────────────────────────────────────────────────────────────

_RECORD_CSS = """<style id="record-mode">
html,body{{margin:0!important;padding:0!important;overflow:hidden!important;
  background:#0b0b1a!important;width:{W}px!important;height:{H}px!important;}}
#stage-wrap{{max-width:{W}px!important;width:{W}px!important;margin:0!important;padding:0!important;}}
#stage{{padding-top:0!important;height:{H}px!important;width:{W}px!important;}}
.slide{{position:absolute!important;inset:0!important;width:{W}px!important;height:{H}px!important;}}
#ctrl,#narr-panel,#btn-narr,#flash{{display:none!important;}}
</style>"""


def _make_record_html(src, dst, W, H):
    with open(src, encoding='utf-8') as f:
        html = f.read()
    html = html.replace('</head>', _RECORD_CSS.format(W=W, H=H) + '\n</head>', 1)
    with open(dst, 'w', encoding='utf-8') as f:
        f.write(html)


def _record_slide(record_html, audio_path, schedule, out_video, W, H):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Run: pip install playwright && playwright install chromium")

    si = schedule.si
    tmp_dir = out_video + '.recdir'
    os.makedirs(tmp_dir, exist_ok=True)

    anim_js = json.dumps([{'rel_t': e.rel_t, 'step_idx': e.step_idx}
                          for e in schedule.anim_events])
    total_ms = int(schedule.total_dur * 1000)

    # 出力を最低1080pに引き上げるためのスーパーサンプリング倍率。
    # スライドは max-width:1280px でCSS設計されているため、viewportは1280x720のまま
    # device_scale_factor で画素密度を上げ、録画サイズを実ピクセル(1920x1080)に合わせる。
    # 本編1280x720→dsf1.5→1920x1080、Shorts1080x1920→dsf1.0（既に1080px幅）。
    dsf = round(max(1.0, 1080 / min(W, H)) * 2) / 2
    rw, rh = int(round(W * dsf)), int(round(H * dsf))
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=['--no-sandbox', '--disable-gpu'])
        ctx = browser.new_context(
            viewport={'width': W, 'height': H},
            device_scale_factor=dsf,
            record_video_dir=tmp_dir,
            record_video_size={'width': rw, 'height': rh},
        )
        rec_start = time.time()   # video capture begins with page creation
        page = ctx.new_page()
        page.goto(f'file://{os.path.abspath(record_html)}')
        page.wait_for_load_state('networkidle')

        page.evaluate(f"""() => {{
            const si = {si};
            document.querySelectorAll('.slide').forEach(el => el.style.display = 'none');
            const sm = SLIDES_META[si];
            if (sm) {{ const el = document.getElementById(sm.id); if (el) el.style.display = 'flex'; }}
            document.querySelectorAll('[class*="rv-"]').forEach(el => {{ el.style.opacity = '0'; }});
            if (si === 0) {{
                // Title slide: reveal every element instantly in its final state
                STEPS.filter(s => s.si === 0).forEach(s => (s.ids || []).forEach(id => {{
                    const el = document.getElementById(id);
                    if (el) {{ el.style.opacity = '1'; el.style.transform = 'none'; }}
                }}));
            }}
        }}""")

        time.sleep(0.3)
        # Page load + setup got captured too — trim this much off the head
        head_offset = time.time() - rec_start

        page.evaluate(f"""() => {{
            const events = {anim_js};
            const t0 = performance.now();
            let cur = 0;
            (function tick() {{
                const now = performance.now() - t0;
                while (cur < events.length && events[cur].rel_t * 1000 <= now) {{
                    const ev = events[cur++];
                    const step = STEPS[ev.step_idx];
                    if (step && step.ids) step.ids.forEach(id => {{
                        const el = document.getElementById(id);
                        if (el) {{
                            el.style.opacity = '1';
                            ['rv-fade','rv-up','rv-scale','rv-pop','rv-left','rv-right']
                              .forEach(c => el.classList.remove(c));
                            el.classList.add(step.anim || 'rv-fade');
                        }}
                    }});
                }}
                if (now < {total_ms} - 50) requestAnimationFrame(tick);
            }})();
        }}""")

        time.sleep(schedule.total_dur + 0.5)
        page.close()
        ctx.close()
        browser.close()

    webms = sorted(
        [f for f in os.listdir(tmp_dir) if f.endswith('.webm')],
        key=lambda f: os.path.getmtime(os.path.join(tmp_dir, f)),
        reverse=True,
    )
    if not webms:
        raise RuntimeError(f"No webm for slide {si}")

    raw_webm = os.path.join(tmp_dir, webms[0])
    # Chromium's screencast is damage-based: once a slide is visually static
    # (after its last animation) it stops emitting frames, so the WebM can end
    # well before the narration audio does. tpad clones the last frame to fill
    # any gap; -t then caps the output at total_dur so the video track always
    # matches the audio track (else editors like Clipchamp trim the tail).
    subprocess.run(
        ['ffmpeg', '-y',
         '-ss', f'{head_offset:.3f}', '-i', raw_webm, '-i', audio_path,
         '-map', '0:v:0', '-map', '1:a:0',
         '-vf', 'tpad=stop_mode=clone:stop_duration=600',
         '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
         '-c:a', 'aac', '-b:a', '192k',
         '-t', str(schedule.total_dur),
         out_video],
        check=True, capture_output=True)
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────────────
# VideoBuilder
# ──────────────────────────────────────────────────────────────────────────────

class VideoBuilder:
    def __init__(self, args):
        self.a = args
        self.slide_html = os.path.abspath(args.slide_html)
        self.out_dir    = os.path.abspath(args.out)
        self.work       = os.path.join(self.out_dir, '.work')
        self.tts_cache  = os.path.join(self.work, 'tts')
        self.audio_dir  = os.path.join(self.work, 'audio')
        self.video_dir  = os.path.join(self.work, 'slides')
        for d in (self.tts_cache, self.audio_dir, self.video_dir):
            os.makedirs(d, exist_ok=True)
        self.sd        = None
        self.audio_durs = []
        self.schedules  = []

    def extract(self):
        print(f"Extracting: {self.slide_html}")
        self.sd = extract_slide_data(self.slide_html)
        print(f"  {len(self.sd.meta)} slides  "
              f"{len(self.sd.steps)} steps  "
              f"{len(self.sd.narrations)} narrations")

    def gen_tts(self):
        a = self.a
        print(f"\nTTS  speaker={a.speaker} (玄野武宏)  speed={a.speed}  "
              f"sent-gap={a.sent_gap}s  para-gap={a.para_gap}s")
        try:
            req = urllib.request.Request(f'{a.voicevox_url}/version')
            with urllib.request.urlopen(req, timeout=5) as r:
                print(f"  VOICEVOX {r.read().decode().strip()}")
        except Exception as e:
            sys.exit(f"VOICEVOX unreachable ({e})\n"
                     "  Start: ./run --host 127.0.0.1 --port 50021")

        seed_user_dict(a.voicevox_url)

        self.audio_durs = []
        self.para_durs = []
        for ni, narr in enumerate(self.sd.narrations):
            wav = os.path.join(self.audio_dir, f'narr_{ni:02d}.wav')
            sidecar = wav + '.json'
            tag = f"[{ni+1:02d}/{len(self.sd.narrations)}]"
            want = _narr_hash(narr, a.speaker, a.speed, a.sent_gap, a.para_gap)
            meta = None
            if os.path.exists(wav) and os.path.exists(sidecar):
                with open(sidecar) as f:
                    meta = json.load(f)
            if meta is not None and meta.get('hash') == want:
                dur = get_duration(wav)
                durs = meta['para_durs']
                print(f"  {tag} cached  {dur:.1f}s")
            else:
                print(f"  {tag} ...", end='', flush=True)
                t0 = time.time()
                durs = gen_narration_audio(
                    narration_text=narr, out_wav=wav,
                    cache_dir=self.tts_cache,
                    speaker=a.speaker, speed=a.speed,
                    voicevox_url=a.voicevox_url,
                    sent_gap=a.sent_gap, para_gap=a.para_gap)
                dur = get_duration(wav)
                print(f" {dur:.1f}s  ({time.time()-t0:.0f}s)")
            self.audio_durs.append(dur)
            self.para_durs.append(durs)

        print(f"\n  Total: {sum(self.audio_durs)/60:.1f} min")

    def build_schedule(self):
        a = self.a
        # sentence start times (cached WAVs exist after gen_tts) for
        # content-matched narration sync
        sent_starts = [compute_sent_starts(n, self.tts_cache, a.speaker,
                                           a.speed, a.sent_gap, a.para_gap)
                       for n in self.sd.narrations]
        self.schedules = build_schedule(
            self.sd, self.audio_durs, self.para_durs,
            lead=a.lead, step_gap=a.step_gap,
            intro=a.intro, outro=a.outro,
            final_outro=a.final_outro, para_gap=a.para_gap,
            sent_starts_list=sent_starts)
        if _SYNC_STATS[1]:
            print(f"\n  narration sync: {_SYNC_STATS[0]}/{_SYNC_STATS[1]} "
                  f"steps text-anchored (rest interpolated)")
        print("\nSchedule:")
        for sc in self.schedules:
            print(f"  S{sc.si+1:02d} ({self.sd.meta[sc.si].id}):  "
                  f"dur={sc.audio_dur:.1f}s  total={sc.total_dur:.1f}s  "
                  f"anims={len(sc.anim_events)}")

    def record(self):
        a = self.a
        record_html = os.path.join(self.work, 'slide_record.html')
        _make_record_html(self.slide_html, record_html, a.width, a.height)

        only = set(a.only_slides) if a.only_slides else None
        print("\nRecording ...")
        for sc in self.schedules:
            if only and sc.si not in only:
                continue
            ni = min(sc.si, len(self.audio_durs) - 1)
            narr_wav = os.path.join(self.audio_dir, f'narr_{ni:02d}.wav')

            intro_w = os.path.join(self.work, f'intro_{sc.si:02d}.wav')
            outro_w = os.path.join(self.work, f'outro_{sc.si:02d}.wav')
            full_w  = os.path.join(self.work, f'full_{sc.si:02d}.wav')
            tail = a.final_outro if sc.si == len(self.schedules) - 1 else a.outro
            _make_silence(intro_w, a.intro)
            _make_silence(outro_w, tail)
            _concat_wavs([intro_w, narr_wav, outro_w], full_w)

            out_mp4 = os.path.join(self.video_dir, f'slide_{sc.si:02d}.mp4')
            print(f"  slide {sc.si+1} ({self.sd.meta[sc.si].id})", end='', flush=True)
            if os.path.exists(out_mp4):
                if _has_video_stream(out_mp4):
                    print(f"  {sc.total_dur:.1f}s (cached)")
                    continue
                # stale audio-only artifact from an interrupted/failed run
                os.remove(out_mp4)
            # Run in isolated subprocess so Playwright/Chromium memory is fully
            # released between slides (prevents crash after ~5 consecutive sessions)
            # Chromium's screencast sporadically emits ZERO video frames under
            # system load, yielding an audio-only mp4 that later breaks the
            # concat/mix (-map 0:v matches nothing). Validate and retry.
            for attempt in range(1, 4):
                p = Process(target=_record_slide,
                            args=(record_html, full_w, sc, out_mp4, a.width, a.height))
                p.start(); p.join()
                if p.exitcode != 0:
                    raise RuntimeError(f"Recording failed for slide {sc.si} (exit {p.exitcode})")
                if _has_video_stream(out_mp4):
                    break
                if os.path.exists(out_mp4):
                    os.remove(out_mp4)
                print(f"  !video-less recording (attempt {attempt}), retrying", end='', flush=True)
            else:
                raise RuntimeError(f"slide {sc.si}: no video stream after 3 attempts")
            print(f"  {sc.total_dur:.1f}s ✓")

    def concat(self):
        # Always assemble every recorded slide — --slide limits re-recording only
        slides = [sc.si for sc in self.schedules]

        list_file = os.path.join(self.work, 'concat.txt')
        with open(list_file, 'w') as f:
            for si in slides:
                mp4 = os.path.join(self.video_dir, f'slide_{si:02d}.mp4')
                if os.path.exists(mp4):
                    f.write(f"file '{os.path.abspath(mp4)}'\n")

        # 出力名: 本編は <episode>_final.mp4、Shortsは <episode>_short<N>_final.mp4。
        # Shortsの親ディレクトリ名は short1 等で区別がつかないため、必ずエピソード名を接頭辞に付ける
        # （納品ファイルの識別性のため。upload_youtube.py / run_shorts.sh も同じ規則で参照する）
        p = Path(self.slide_html).parent
        if re.fullmatch(r'short\d+', p.name) and p.parent.name == 'shorts_build':
            ep = f'{p.parent.parent.name}_{p.name}'
        else:
            ep = p.name
        out_mp4 = os.path.join(self.out_dir, f'{ep}_final.mp4')
        mixing = bool(self.a.bgm or self.a.sfx_dir)
        concat_out = out_mp4 + '.premix.mp4' if mixing else out_mp4
        # 連結は映像を再エンコードする（-c copy は per-slide AACのプライミング間隙が
        # 積もってA/Vが0.8秒ほどズレるため不可）。品質はCRF18で実質ロスレス。
        # 画質の主改善は解像度1080p化（record()のdevice_scale_factor）が担う。
        subprocess.run(
            ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', list_file,
             '-c:v', 'libx264', '-crf', str(self.a.crf), '-preset', 'fast',
             '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', concat_out],
            check=True)
        if mixing:
            self.mix_audio(concat_out, out_mp4, slides)
            os.remove(concat_out)
        dur = get_duration(out_mp4)
        print(f"\nFinal: {out_mp4}  ({dur/60:.1f} min)")

    def mix_audio(self, src, dst, slide_order):
        """Post-mix BGM (looped, faded) and SFX (slide whooshes + reveal pops)
        under the narration. Video stream is copied untouched."""
        a = self.a
        total = get_duration(src)

        # absolute start offset of each slide from the actual muxed files
        offsets, cum = {}, 0.0
        for si in slide_order:
            offsets[si] = cum
            cum += get_duration(os.path.join(self.video_dir, f'slide_{si:02d}.mp4'))

        # SFX event plan: whoosh on every slide boundary (not video start),
        # pop on rv-pop / rv-scale reveals, one soft ding on the opening anchor.
        events = []   # (time_sec, kind)
        if a.sfx_dir:
            events.append((0.5, 'ding'))
            for sc in self.schedules:
                off = offsets.get(sc.si, 0.0)
                if sc.si != slide_order[0]:
                    events.append((off + 0.03, 'whoosh'))
                for ev in sc.anim_events:
                    anim = self.sd.steps[ev.step_idx].anim if ev.step_idx < len(self.sd.steps) else ""
                    if anim in ('rv-pop', 'rv-scale'):
                        events.append((off + ev.rel_t + 0.05, 'pop'))
            # rate-limit: global min gap 0.6s, cap 60 events
            events.sort()
            kept, last_t = [], -10.0
            for t, kind in events:
                if t - last_t >= 0.6 and t < total - 0.5:
                    kept.append((t, kind)); last_t = t
            events = kept[:60]

        sfx_files = {'whoosh': 'sfx_whoosh.wav', 'pop': 'sfx_pop.wav', 'ding': 'sfx_ding.wav'}
        kinds = [k for k in ('whoosh', 'pop', 'ding') if any(e[1] == k for e in events)]

        inputs = ['-i', src]
        if a.bgm:
            inputs += ['-stream_loop', '-1', '-i', a.bgm]
        for k in kinds:
            inputs += ['-i', os.path.join(a.sfx_dir, sfx_files[k])]

        flt, mix_ins = [], ['[0:a]']
        idx = 1
        if a.bgm:
            flt.append(f"[{idx}:a]atrim=0:{total:.3f},afade=t=in:d=1.5,"
                       f"afade=t=out:st={max(0.0, total-4):.3f}:d=4,"
                       f"volume={a.bgm_db}dB[bgm]")
            mix_ins.append('[bgm]'); idx += 1
        for k in kinds:
            evs = [e for e in events if e[1] == k]
            names = ''.join(f'[{k}{j}]' for j in range(len(evs)))
            flt.append(f"[{idx}:a]volume={a.sfx_db}dB,asplit={len(evs)}{names}")
            for j, (t, _) in enumerate(evs):
                ms = int(t * 1000)
                flt.append(f"[{k}{j}]adelay={ms}:all=1[{k}d{j}]")
                mix_ins.append(f'[{k}d{j}]')
            idx += 1
        flt.append(f"{''.join(mix_ins)}amix=inputs={len(mix_ins)}:duration=first:normalize=0[amixed]")

        # pass 1: render the mixed audio and measure loudness
        tmp_wav = dst + '.mix.wav'
        subprocess.run(
            ['ffmpeg', '-y', *inputs, '-filter_complex', ';'.join(flt),
             '-map', '[amixed]', '-ar', '48000', tmp_wav],
            check=True, capture_output=True)
        meas = subprocess.run(
            ['ffmpeg', '-hide_banner', '-i', tmp_wav,
             '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
            capture_output=True, text=True).stderr
        mj = json.loads(meas[meas.rindex('{'):meas.rindex('}') + 1])

        # pass 2: gain to -14 LUFS + lookahead limiter at -1.5 dBTP.
        # (VOICEVOX voice has ~24dB peak-to-loudness ratio, so loudnorm's
        # TP ceiling blocks a pure gain; explicit limiting is required.)
        gain = -14.0 - float(mj['input_i'])
        ln = (f"volume={gain:.2f}dB,"
              f"alimiter=level_in=1:level_out=1:limit=0.8414:attack=4:release=60:level=false,"
              f"aresample=48000")
        subprocess.run(
            ['ffmpeg', '-y', '-i', src, '-i', tmp_wav,
             '-map', '0:v', '-map', '1:a', '-af', ln,
             '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', dst],
            check=True, capture_output=True)
        os.remove(tmp_wav)

        # convergence passes: the limiter eats some integrated loudness on
        # high-PLR speech, so measure the result and trim the residual
        # (audio-only re-encode; at most 2 extra passes).
        def measure_i(path):
            out = subprocess.run(
                ['ffmpeg', '-hide_banner', '-i', path,
                 '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json',
                 '-f', 'null', '-'], capture_output=True, text=True).stderr
            return float(json.loads(out[out.rindex('{'):out.rindex('}') + 1])['input_i'])

        cur = measure_i(dst)
        for _ in range(2):
            resid = -14.0 - cur
            if abs(resid) <= 0.6:
                break
            tmp2 = dst + '.trim.mp4'
            subprocess.run(
                ['ffmpeg', '-y', '-i', dst,
                 '-af', (f"volume={resid:.2f}dB,"
                         f"alimiter=level_in=1:level_out=1:limit=0.8414:attack=4:release=60:level=false"),
                 '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', tmp2],
                check=True, capture_output=True)
            os.replace(tmp2, dst)
            cur = measure_i(dst)
        print(f"  audio mix: bgm={'on' if a.bgm else 'off'} sfx={len(events)} events, "
              f"loudness {mj['input_i']}→{cur:.1f} LUFS (target -14, gain+limiter)")

    def run(self):
        self.extract()
        self.gen_tts()
        self.build_schedule()
        if not self.a.no_record:
            self.record()
            self.concat()
        else:
            print("\n--no-record: TTS done, skipping recording.")


if __name__ == '__main__':
    VideoBuilder(parse_args()).run()
