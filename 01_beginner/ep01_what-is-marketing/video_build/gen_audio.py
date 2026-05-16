#!/usr/bin/env python3
"""
Generate narration audio for ep01 slides.
Priority: VOICEVOX (localhost:50021) → Google TTS

VOICEVOX speakers (style_id):
  1 = ずんだもん（ノーマル）
  2 = 四国めたん（ノーマル）
  3 = ずんだもん（あまあま）
 13 = 青山龍星（ノーマル）— 落ち着いた男性声・教育コンテンツ向け

Usage:
  python3 gen_audio.py <slide.html> <out_dir> [speaker_id]
"""

import sys
import os
import re
import json
import time
import subprocess


VOICEVOX_URL = "http://localhost:50021"
DEFAULT_SPEAKER = 13   # 青山龍星 ノーマル（落ち着いた男性声）
SPEED_SCALE = 1.05     # わずかに速め（教育コンテンツ推奨）


def extract_narrations(slide_html_path: str) -> list[str]:
    """slide.html の NARRATIONS 配列からテキストを抽出する。"""
    with open(slide_html_path, encoding="utf-8") as f:
        content = f.read()

    match = re.search(r"const NARRATIONS\s*=\s*\[(.*?)\];", content, re.DOTALL)
    if not match:
        raise ValueError("NARRATIONS array not found in slide.html")

    narrations_str = match.group(1)
    texts = re.findall(r"`(.*?)`", narrations_str, re.DOTALL)

    result = []
    for text in texts:
        text = text.replace("\\n", "\n").strip()
        result.append(text)
    return result


def get_audio_duration(path: str) -> float:
    """ffprobe で音声ファイルの長さ（秒）を取得する。"""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


# ──────────────────────────────────────────────────────────────────────────────
# VOICEVOX
# ──────────────────────────────────────────────────────────────────────────────

def try_voicevox(texts: list[str], out_dir: str, speaker: int) -> bool:
    """VOICEVOX API（port 50021）で音声を生成する。"""
    try:
        import requests
    except ImportError:
        print("  requests not installed — skipping VOICEVOX")
        return False

    try:
        r = requests.get(f"{VOICEVOX_URL}/version", timeout=3)
        r.raise_for_status()
        print(f"  VOICEVOX version: {r.text.strip()}")
    except Exception as e:
        print(f"  VOICEVOX not running ({e})")
        return False

    durations = {}
    for i, text in enumerate(texts):
        slide_no = i + 1
        print(f"  [VOICEVOX] Slide {slide_no:02d}/{len(texts)} ...", end="", flush=True)
        try:
            r = requests.post(
                f"{VOICEVOX_URL}/audio_query",
                params={"text": text, "speaker": speaker},
                timeout=60,
            )
            r.raise_for_status()
            query = r.json()
            query["speedScale"] = SPEED_SCALE

            r = requests.post(
                f"{VOICEVOX_URL}/synthesis",
                params={"speaker": speaker},
                json=query,
                timeout=120,
            )
            r.raise_for_status()

            path = os.path.join(out_dir, f"audio_{i:02d}.wav")
            with open(path, "wb") as f:
                f.write(r.content)

            dur = get_audio_duration(path)
            durations[i] = dur
            print(f" {dur:.1f}s ✓")
        except Exception as e:
            print(f" ERROR: {e}")
            return False

    with open(os.path.join(out_dir, "durations.json"), "w") as f:
        json.dump({"engine": "voicevox", "speaker": speaker, "durations": durations}, f, indent=2)

    return True


# ──────────────────────────────────────────────────────────────────────────────
# Google TTS (fallback)
# ──────────────────────────────────────────────────────────────────────────────

def try_gtts(texts: list[str], out_dir: str) -> bool:
    """Google TTS（gtts）で音声を生成する。（VOICEVOX 不在時のフォールバック）"""
    try:
        from gtts import gTTS
    except ImportError:
        print("  gtts not installed — run: pip install gtts")
        return False

    print("  Trying Google TTS (gtts)...")
    durations = {}

    for i, text in enumerate(texts):
        slide_no = i + 1
        print(f"  [gtts] Slide {slide_no:02d}/{len(texts)} ...", end="", flush=True)

        clean = (text
                 .replace("——", "。")
                 .replace("「", "").replace("」", "")
                 .replace("『", "").replace("』", ""))
        mp3_path = os.path.join(out_dir, f"audio_{i:02d}.mp3")
        try:
            tts = gTTS(text=clean, lang="ja", slow=False)
            tts.save(mp3_path)
        except Exception as e:
            print(f" ERROR: {e}")
            return False

        dur = get_audio_duration(mp3_path)
        durations[i] = dur
        print(f" {dur:.1f}s ✓")
        time.sleep(0.5)

    with open(os.path.join(out_dir, "durations.json"), "w") as f:
        json.dump({"engine": "gtts", "durations": durations}, f, indent=2)
    return True


# ──────────────────────────────────────────────────────────────────────────────
# open-jtalk (offline fallback)
# ──────────────────────────────────────────────────────────────────────────────

JTALK_VOICE = "/usr/share/hts-voice/nitech-jp-atr503-m001/nitech_jp_atr503_m001.htsvoice"
JTALK_DIC = "/var/lib/mecab/dic/open-jtalk/naist-jdic"


def try_openjtalk(texts: list[str], out_dir: str) -> bool:
    """open_jtalk コマンドで日本語音声を生成する（オフライン・Nitech HTS 音声）。"""
    if not os.path.exists(JTALK_VOICE):
        print("  open_jtalk voice not found — run: apt install hts-voice-nitech-jp-atr503-m001")
        return False

    print("  Using open_jtalk (Nitech HTS voice, offline) ...")
    durations = {}

    for i, text in enumerate(texts):
        slide_no = i + 1
        print(f"  [open_jtalk] Slide {slide_no:02d}/{len(texts)} ...", end="", flush=True)

        # 改行を句点+スペースに変換し全文を1つの入力として送る
        clean = (text
                 .replace("\n", "。 ")
                 .replace("——", "。")
                 .replace("①", "一つ目、").replace("②", "二つ目、")
                 .replace("③", "三つ目、").replace("④", "四つ目、"))

        wav_path = os.path.join(out_dir, f"audio_{i:02d}.wav")

        result = subprocess.run(
            ["open_jtalk",
             "-m", JTALK_VOICE,
             "-x", JTALK_DIC,
             "-ow", wav_path,
             "-s", "48000",
             "-p", "200",    # フレーム周期
             "-r", "0.85",   # 発話速度（1.0=標準、小さいほど遅い）
             "-a", "0.55",
             "-b", "0.0"],
            input=clean,
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            print(f" ERROR: {result.stderr[:120]}")
            return False

        dur = get_audio_duration(wav_path)
        durations[i] = dur
        print(f" {dur:.1f}s ✓")

    with open(os.path.join(out_dir, "durations.json"), "w") as f:
        json.dump({"engine": "open_jtalk", "durations": durations}, f, indent=2)
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print("Usage: gen_audio.py <slide.html> <out_dir> [voicevox_speaker_id]")
        sys.exit(1)

    slide_path = sys.argv[1]
    out_dir = sys.argv[2]
    speaker = int(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_SPEAKER

    os.makedirs(out_dir, exist_ok=True)

    print("Extracting narrations from slide.html...")
    texts = extract_narrations(slide_path)
    print(f"Found {len(texts)} narration segments\n")

    print("=== Audio Generation ===")
    if try_voicevox(texts, out_dir, speaker):
        print("\nVOICEVOX audio generation complete.")
    elif try_gtts(texts, out_dir):
        print("\nGoogle TTS audio generation complete.")
        print("Note: Re-run with VOICEVOX running for higher quality audio.")
    elif try_openjtalk(texts, out_dir):
        print("\nopen_jtalk audio generation complete.")
        print("Note: Re-run with VOICEVOX running for higher quality audio.")
    else:
        print("ERROR: No TTS engine available.")
        sys.exit(1)


if __name__ == "__main__":
    main()
