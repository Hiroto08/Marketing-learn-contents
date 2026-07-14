#!/usr/bin/env python3
"""本編ビルド後の後処理を1コマンドで行う（判断不要・機械ゲート）。

    python3 _tools/video/postbuild_episode.py <episode_dir>

やること（全自動）:
  1. A/V検証   : final.mp4 の video/audio トラック長を比較。
                 合格 = 合計差 ≤0.2秒 かつ 全スライド単体の差 ≤0.1秒
                 （フレーム量子化(1/25s)の蓄積は正常。単体で大きくズレた
                  スライドがある場合のみ `--slide N` での再録画が必要）
  2. ラウドネス : ebur128 Integrated が -16〜-13 LUFS 帯にあること
  3. タイムスタンプ実測修正:
                 .work/slides/slide_NN.mp4 の実測尺から各スライド開始時刻を出し、
                 script.md の全スライド見出し（タイムスタンプ無し形式にも追記対応）と
                 description.md の「## タイムスタンプ」「## チャプター生成用」を書き換える。
                 チャプター節が旧1行形式ならタイムスタンプ節のラベルから18行形式に再生成
  4. mp4ステージング: video_build/out/<name>_final.mp4 → video_build/<name>_final.mp4
                 （upload_youtube.py が見るのはこの場所）

終了コード 0 = 全ゲート通過。非0 = メッセージの指示に従うこと。
"""
import glob
import os
import re
import shutil
import subprocess
import sys

FAILS = []


def probe_dur(path: str, sel: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", sel,
         "-show_entries", "stream=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def container_dur(path: str) -> float:
    """コンテナ全体の尺（タイムスタンプ計算はこちら。SKILL.mdの公式レシピと同じ基準）"""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    ep = sys.argv[1].rstrip("/")
    name = os.path.basename(ep)
    out = f"{ep}/video_build/out"
    final = f"{out}/{name}_final.mp4"
    if not os.path.exists(final):
        sys.exit(f"NG: {final} が無い。先に make_video.py でビルドする")

    # ── 1. A/V検証 ──
    vd, ad = probe_dur(final, "v:0"), probe_dur(final, "a:0")
    total_diff = abs(vd - ad)
    slides = sorted(glob.glob(f"{out}/.work/slides/slide_*.mp4"))
    per = []
    for s in slides:
        d = probe_dur(s, "v:0") - probe_dur(s, "a:0")
        per.append((os.path.basename(s), d))
    bad = [(n, d) for n, d in per if abs(d) > 0.1]
    if total_diff <= 0.2 and not bad:
        note = "" if total_diff <= 0.1 else "（量子化蓄積・スライド単体は全て≤0.1s → 正常）"
        print(f"✓ A/V: video={vd:.3f}s audio={ad:.3f}s diff={total_diff:.3f}s {note}")
    else:
        FAILS.append("A/V")
        print(f"✗ A/V: diff={total_diff:.3f}s  単体超過: {[(n, round(d,3)) for n,d in bad]}")
        for n, d in bad:
            i = int(re.search(r"(\d+)", n).group(1))
            print(f"    → 再録画: rm {out}/.work/slides/{n} して make_video.py に --slide {i} を付けて再実行")

    # ── 1b. 最低尺（完成動画は8:00以上が必須） ──
    if vd < 480.0:
        FAILS.append("最低尺")
        print(f"✗ 最低尺: {int(vd//60)}:{int(vd%60):02d} < 8:00 → script.md/slide.htmlのナレーションを増補して再ビルド（verify_episodeの推定尺ゲート8:15を先に通すこと）")
    else:
        print(f"✓ 最低尺: {int(vd//60)}:{int(vd%60):02d} ≥ 8:00")

    # ── 2. ラウドネス ──
    r = subprocess.run(["ffmpeg", "-nostats", "-i", final,
                        "-filter_complex", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)  # 途中経過も出るので必ず最後(Summary)を読む
    lufs = float(m[-1]) if m else -99.0
    if -16 <= lufs <= -13:
        print(f"✓ LUFS: {lufs}")
    else:
        FAILS.append("LUFS")
        print(f"✗ LUFS: {lufs}（-16〜-13の外。BGMミックス指定漏れ? audio-production.md参照）")

    # ── 3. タイムスタンプ実測修正 ──
    durs = [container_dur(s) for s in slides]
    n = len(durs)

    def ts(t):
        return f"{int(t // 60)}:{int(t % 60):02d}"

    starts, cum = [], 0.0
    for d in durs:
        starts.append(ts(cum))
        cum += d
    bounds = starts + [ts(cum)]
    print(f"  実測: {n}枚 総尺 {ts(cum)} ({cum:.2f}s)")

    sp = f"{ep}/script.md"
    s = open(sp, encoding="utf-8").read()

    def fix(m2):
        k = int(m2.group(1))
        return f"スライド {k}：{m2.group(2)}（{bounds[k-1]}〜{bounds[k]}）"
    s2, cnt = re.subn(r"スライド (\d+)：(.*?)（\d+:\d{2}〜\d+:\d{2}）", fix, s)
    if cnt == 0:
        # 見出しにタイムスタンプが無い旧形式 → 追記（見出し行のみを置換。直後の空行は保持）
        s2, cnt = re.subn(
            r"^### (🎬 )?スライド (\d+)：(.+?)\s*$",
            lambda m2: f"### {m2.group(1) or ''}スライド {int(m2.group(2))}："
                       f"{m2.group(3)}（{bounds[int(m2.group(2))-1]}〜{bounds[int(m2.group(2))]}）",
            s, flags=re.M)
    if cnt != n:
        FAILS.append("script.md")
        print(f"✗ script.md 見出し {cnt}/{n} 件しか更新できない（形式を確認）")
    else:
        open(sp, "w", encoding="utf-8").write(s2)
        print(f"✓ script.md 見出し {cnt}件を実測値に更新")

    dp = f"{ep}/description.md"
    d = open(dp, encoding="utf-8").read()
    ts_labels = None
    for m3 in re.finditer(r"(## (?:タイムスタンプ|チャプター生成用)[^\n]*\s*\n\n```\n)(.*?)(```)", d, re.S):
        lines = m3.group(2).strip("\n").split("\n")
        if len(lines) != n:
            if ts_labels is not None:
                new = [f"{starts[i]} {re.split('（', lab)[0].strip()}" for i, lab in enumerate(ts_labels)]
                d = d.replace(m3.group(0), m3.group(1) + "\n".join(new) + "\n" + m3.group(3))
                print("✓ チャプター生成用: 旧形式をタイムスタンプ節から18行形式に再生成")
                continue
            FAILS.append("description.md")
            print(f"✗ description.md のブロック行数 {len(lines)} ≠ スライド数 {n}")
            continue
        new = [re.sub(r"^\d+:\d{2}", starts[i], l) for i, l in enumerate(lines)]
        if ts_labels is None:
            ts_labels = [re.sub(r"^\d+:\d{2}\s*", "", l) for l in new]
        d = d.replace(m3.group(0), m3.group(1) + "\n".join(new) + "\n" + m3.group(3))
        print("✓ description.md タイムスタンプブロック更新")
    open(dp, "w", encoding="utf-8").write(d)

    # ── 4. ステージング ──
    dst = f"{ep}/video_build/{name}_final.mp4"
    shutil.copyfile(final, dst)
    print(f"✓ staged: {dst}")

    if FAILS:
        sys.exit(f"POSTBUILD FAIL: {FAILS}")
    print("POSTBUILD PASS")


if __name__ == "__main__":
    main()
