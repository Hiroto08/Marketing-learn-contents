#!/usr/bin/env python3
"""
Generate narration audio for ep01 slides.
Priority: VOICEVOX (localhost:50021) → Google TTS → open_jtalk

VOICEVOX speakers (style_id):
  1 = ずんだもん（ノーマル）
  2 = 四国めたん（ノーマル）
 13 = 青山龍星（ノーマル）← デフォルト・落ち着いた男性声

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
# TTS テキスト前処理（読み仮名・イントネーション修正）
# ──────────────────────────────────────────────────────────────────────────────

def clean_for_tts(text: str) -> str:
    """
    open_jtalk / VOICEVOX 向けに読み間違いが起きやすい表記を修正する。

    修正方針:
      - 英字略語 → カタカナに展開（MeCab が letter-by-letter で読むのを防ぐ）
      - 数字の範囲表現「〜」→「から」
      - ダッシュ「——」→ 自然な読点「、」
      - 行区切り（\\n）→ 句点「。」に変換して連続した1文として送る
      - 括弧記号・丸数字 → 読みやすい表現に展開
    """
    t = text

    # ── 改行 → 句点変換（1行ずつ音声合成ではなく全体を1入力として送るため）──
    t = t.replace("\n", "。 ")

    # ── ダッシュ類 ──
    t = t.replace("——", "、").replace("―", "、").replace("─", "、")

    # ── 英字略語（アルファベット → カタカナ）──
    ABBR = {
        "AMA":  "エーエムエー",
        "SNS":  "エスエヌエス",
        "AI":   "エーアイ",
        "PR":   "ピーアール",
        "HBR":  "エイチビーアール",
        "HBS":  "エイチビーエス",
        "JTBD": "ジェイティービーディー",
        "STP":  "エスティーピー",
        "KPI":  "ケーピーアイ",
    }
    for abbr, kana in ABBR.items():
        # 前後が単語境界（スペース、句読点、括弧など）の場合のみ置換
        t = re.sub(r'(?<![A-Za-z])' + abbr + r'(?![A-Za-z])', kana, t)

    # ── 数字の範囲「〜」→「から」──
    t = re.sub(r'(\d)\s*〜\s*(\d)', r'\1から\2', t)
    t = re.sub(r'(\d)\s*～\s*(\d)', r'\1から\2', t)

    # ── 丸数字 → 読み出し ──
    MARU = {"①": "いちつめ、", "②": "ふたつめ、", "③": "みっつめ、", "④": "よっつめ、",
            "⑤": "いつつめ、", "⑥": "むっつめ、"}
    for k, v in MARU.items():
        t = t.replace(k, v)

    # ── 引用括弧 → 読み上げ時は除去（前後に自然なポーズが入るよう句点付与）──
    t = t.replace("「", "").replace("」", "")
    t = t.replace("『", "").replace("』", "")

    # ── 年号・数字の自然な読み方補助 ──
    # 「1960年代」等は MeCab が処理するが念のため明示的な読みを入れない
    # （誤変換を避けるため過剰な変換は行わない）

    # ── MeCab プロソディ異常回避 ──
    # 「〜のかと考える/思う」など間接疑問句の後に読点を補うことで
    # open_jtalk が異常に長い合成をするのを防ぐ
    t = re.sub(r'(のか|だろうか|ないか)と(考え|思|感じ)', r'\1、と\2', t)

    # ── その他記号クリーニング ──
    t = re.sub(r'[（）\(\)]', '', t)   # 括弧除去
    t = re.sub(r'\s{2,}', ' ', t)      # 連続スペース圧縮
    t = t.strip()

    return t


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
            clean = clean_for_tts(text)
            r = requests.post(
                f"{VOICEVOX_URL}/audio_query",
                params={"text": clean, "speaker": speaker},
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

        clean = clean_for_tts(text)
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
SENT_GAP_SEC  = 0.28   # 。区切りの文間ギャップ（秒）
PARA_GAP_SEC  = 0.45   # \n 区切りの段落間ギャップ（秒）


def _jtalk_synthesize(text: str, out_path: str) -> bool:
    """open_jtalk で1文を合成し、先頭・末尾の無音をトリムして out_path に書き出す。"""
    raw_path = out_path + ".raw.wav"
    result = subprocess.run(
        ["open_jtalk",
         "-m", JTALK_VOICE,
         "-x", JTALK_DIC,
         "-ow", raw_path,
         "-s", "48000",
         "-p", "200",    # フレーム周期
         "-r", "1.0",    # 発話速度（標準）
         "-a", "0.55",
         "-b", "0.0"],
        input=text,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return False

    # 先頭・末尾の無音をトリム（areverse trick で両端を除去）
    trim_filter = (
        "silenceremove=start_periods=1:start_duration=0.02:start_threshold=-40dB,"
        "areverse,"
        "silenceremove=start_periods=1:start_duration=0.02:start_threshold=-40dB,"
        "areverse"
    )
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", raw_path, "-af", trim_filter, out_path],
        capture_output=True,
    )
    if os.path.exists(raw_path):
        os.remove(raw_path)
    return r.returncode == 0 and os.path.exists(out_path)


def _make_silence(path: str, duration: float) -> None:
    """指定秒の無音 WAV を生成する。"""
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", "anullsrc=channel_layout=mono:sample_rate=48000",
         "-t", str(duration), path],
        capture_output=True,
    )


def _concat_wavs(parts_and_gaps: list, out_path: str) -> None:
    """(wavpath | gap_sec) のリストを順に結合して out_path に書き出す。
    parts_and_gaps は [str, float, str, float, str, ...] の交互リスト。
    """
    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="_concat_")
    inputs_seq = []
    gap_cache: dict[float, str] = {}

    for item in parts_and_gaps:
        if isinstance(item, float):
            key = round(item, 3)
            if key not in gap_cache:
                gp = os.path.join(tmp_dir, f"gap_{key}.wav")
                _make_silence(gp, item)
                gap_cache[key] = gp
            inputs_seq.append(gap_cache[key])
        else:
            inputs_seq.append(item)

    input_args = []
    for f in inputs_seq:
        input_args += ["-i", f]

    n = len(inputs_seq)
    filter_str = "".join(f"[{i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[out]"

    subprocess.run(
        ["ffmpeg", "-y"] + input_args + [
            "-filter_complex", filter_str,
            "-map", "[out]",
            out_path,
        ],
        capture_output=True,
    )
    import shutil as _sh; _sh.rmtree(tmp_dir, ignore_errors=True)


def _split_to_segments(text: str) -> list[tuple[str, float]]:
    """テキストを (合成テキスト, 直後のギャップ秒) のリストに分割する。

    分割ルール:
      - \\n  → 段落区切り（PARA_GAP_SEC）
      - 。！？ → 文末（SENT_GAP_SEC）
      - それ以外は前の文に結合
    最後の要素のギャップは 0.0（末尾は不要）。
    """
    # まず段落（\n）で分割
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    segments: list[tuple[str, float]] = []

    for pi, para in enumerate(paragraphs):
        # 段落内を 。！？ で分割
        parts = re.split(r'(?<=[。！？])', para)
        parts = [p.strip() for p in parts if p.strip()]

        for si, part in enumerate(parts):
            is_last_in_para = (si == len(parts) - 1)
            is_last_para    = (pi == len(paragraphs) - 1)

            if is_last_in_para and not is_last_para:
                gap = PARA_GAP_SEC
            elif is_last_in_para and is_last_para:
                gap = 0.0
            else:
                gap = SENT_GAP_SEC

            clean = clean_for_tts(part)
            if clean:
                segments.append((clean, gap))

    return segments


def try_openjtalk(texts: list[str], out_dir: str) -> bool:
    """open_jtalk で 。\\n ごとに分割合成し制御されたギャップで結合する。"""
    if not os.path.exists(JTALK_VOICE):
        print("  open_jtalk voice not found — run: apt install hts-voice-nitech-jp-atr503-m001")
        return False

    print(f"  Using open_jtalk (per-sentence, sent={SENT_GAP_SEC}s para={PARA_GAP_SEC}s gap) ...")
    import tempfile
    tmp_dir = tempfile.mkdtemp(prefix="jtalk_")
    durations = {}

    for i, text in enumerate(texts):
        slide_no = i + 1
        print(f"  [open_jtalk] Slide {slide_no:02d}/{len(texts)} ...", end="", flush=True)

        segments = _split_to_segments(text)
        if not segments:
            print(" SKIP (empty)")
            continue

        wav_path = os.path.join(out_dir, f"audio_{i:02d}.wav")

        if len(segments) == 1:
            ok = _jtalk_synthesize(segments[0][0], wav_path)
            if not ok:
                print(" ERROR: open_jtalk failed")
                return False
        else:
            # 各セグメントを合成してギャップ付きで結合
            parts_and_gaps: list = []
            for j, (sent, gap) in enumerate(segments):
                pf = os.path.join(tmp_dir, f"s{i:02d}_{j:02d}.wav")
                if not _jtalk_synthesize(sent, pf):
                    print(f" ERROR: open_jtalk failed on segment {j}")
                    return False
                parts_and_gaps.append(pf)
                if gap > 0:
                    parts_and_gaps.append(gap)
            _concat_wavs(parts_and_gaps, wav_path)

        dur = get_audio_duration(wav_path)
        durations[i] = dur
        print(f" {len(segments)}seg / {dur:.1f}s ✓")

    import shutil
    shutil.rmtree(tmp_dir, ignore_errors=True)

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
