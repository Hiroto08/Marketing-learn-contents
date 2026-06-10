#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_video.py — スライドHTML → 合成音声付き動画ジェネレーター

このリポジトリの slide.html（共通エンジン: NARRATIONS / STEPS / SLIDES_META /
advanceStep / resetSlideElements）を読み込み、VOICEVOX でナレーションを合成し、
1スライドずつ Playwright で実時間録画して ffmpeg で結合する。

設計のポイント:
  - スライド単位で「録画 → 音声結合」するため、ズレが蓄積しない
  - 各アニメーションステップは対応するナレーション段落の lead 秒前に発火
    （話題に入る直前に図が動く）
  - TTS はテキストの md5 でキャッシュされ、再実行時は変更段落のみ再合成

前提:
  - VOICEVOX ENGINE が起動していること（--voicevox-url、既定 127.0.0.1:50021）
  - ffmpeg / ffprobe が PATH にあること
  - playwright (python) と Chromium バイナリ（--chromium で指定可）

使い方:
  python3 make_video.py --slide path/to/slide.html --out episode.mp4
  python3 make_video.py --slide ... --out ... --slides 2 5   # 一部だけ再録画
  python3 make_video.py --slide ... --out ... --speaker 8 --speed 1.0
"""

import argparse
import asyncio
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict


# ---------------------------------------------------------------- utilities

def die(msg):
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


def ffprobe_duration(path):
    out = subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', path])
    return float(out.strip())


def run_ffmpeg(args):
    subprocess.run(['ffmpeg', '-y', '-v', 'error'] + args, check=True)


def find_chromium(explicit):
    if explicit:
        if not os.path.exists(explicit):
            die(f'chromium not found: {explicit}')
        return explicit
    candidates = sorted(glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome'))
    if candidates:
        return candidates[-1]
    return None  # let playwright use its default


# ---------------------------------------------------------------- pipeline

class VideoBuilder:
    HIDE_CSS = (
        '#ctrl,#prog-wrap,#narr-panel{display:none !important;}'
        'body{margin:0;padding:0;overflow:hidden;}'
        '#stage-wrap{max-width:none;width:WIDTHpx;}'
    )

    PREP_JS = """(si) => {
      document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));
      document.getElementById(SLIDES_META[si].id).classList.add('active');
      state.slide = si;
      resetSlideElements(si);
      state.cursor = SLIDE_FIRST_STEP[si];
      if (typeof updateDots === 'function') updateDots();
    }"""

    def __init__(self, opt):
        self.opt = opt
        self.url = 'file://' + os.path.abspath(opt.slide)
        self.work = opt.workdir
        for sub in ('tts', 'audio', 'rec', 'mp4'):
            os.makedirs(os.path.join(self.work, sub), exist_ok=True)
        self.chromium = find_chromium(opt.chromium)
        self.data = None        # {narrations, steps}
        self.durations = {}     # si -> [para durations]
        self.schedule = {}      # si -> {events:[t...], total:s}

    # -------- 1. extract deck data --------
    async def extract(self):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            kw = {'executable_path': self.chromium} if self.chromium else {}
            b = await p.chromium.launch(**kw)
            page = await b.new_page(
                viewport={'width': self.opt.width, 'height': self.opt.height})
            await page.goto(self.url)
            await page.wait_for_timeout(800)
            ok = await page.evaluate(
                "typeof NARRATIONS!=='undefined' && typeof STEPS!=='undefined'"
                " && typeof SLIDES_META!=='undefined'")
            if not ok:
                die('slide.html に NARRATIONS / STEPS / SLIDES_META が見つかりません。'
                    'このツールはリポジトリ共通のスライドエンジンを前提としています。')
            self.data = await page.evaluate(
                "() => ({narrations: NARRATIONS,"
                " steps: STEPS.map(s => ({si:s.si})),"
                " count: SLIDES_META.length})")
            await b.close()
        n_slides = self.data['count']
        n_narr = len(self.data['narrations'])
        if n_slides != n_narr:
            die(f'SLIDES_META({n_slides}) と NARRATIONS({n_narr}) の数が一致しません')
        print(f'deck: {n_slides} slides, '
              f'{len(self.data["steps"])} animation steps')

    # -------- 2. TTS --------
    @staticmethod
    def clean_text(text):
        t = text.replace('——', '、').replace('──', '、').replace('→', '、')
        t = re.sub(r'[『』「」]', '', t)
        return re.sub(r'\s+', ' ', t).strip()

    def tts_one(self, text, path):
        base = self.opt.voicevox_url
        q = urllib.parse.urlencode({'text': text, 'speaker': self.opt.speaker})
        req = urllib.request.Request(f'{base}/audio_query?{q}', method='POST')
        with urllib.request.urlopen(req) as r:
            query = json.load(r)
        query['speedScale'] = self.opt.speed
        query['outputSamplingRate'] = 24000
        req = urllib.request.Request(
            f'{base}/synthesis?speaker={self.opt.speaker}',
            data=json.dumps(query).encode(),
            headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req) as r:
            with open(path, 'wb') as f:
                f.write(r.read())

    def gen_tts(self):
        try:
            with urllib.request.urlopen(
                    f'{self.opt.voicevox_url}/version', timeout=5) as r:
                ver = r.read().decode().strip('"')
            print(f'voicevox engine: {ver}')
        except Exception:
            die(f'VOICEVOX ENGINE に接続できません: {self.opt.voicevox_url}\n'
                '  起動例: /opt/voicevox_engine/engine/linux-cpu-x64/run '
                '--host 127.0.0.1 --port 50021 &')
        total = 0.0
        for si, narr in enumerate(self.data['narrations']):
            paras = [p for p in narr.split('\n') if p.strip()]
            self.durations[si] = []
            for pi, para in enumerate(paras):
                text = self.clean_text(para)
                key = hashlib.md5(
                    f'{text}|{self.opt.speaker}|{self.opt.speed}'.encode()
                ).hexdigest()[:16]
                path = os.path.join(self.work, 'tts', f'{key}.wav')
                if not os.path.exists(path):
                    self.tts_one(text, path)
                d = ffprobe_duration(path)
                self.durations[si].append((d, path))
                total += d
        print(f'narration total: {total/60:.1f} min '
              f'({sum(len(v) for v in self.durations.values())} paragraphs)')

    # -------- 3. schedule + per-slide audio track --------
    def build_schedule(self):
        steps_per_slide = defaultdict(int)
        for s in self.data['steps']:
            steps_per_slide[s['si']] += 1
        o = self.opt
        n = self.data['count']
        for si in range(n):
            durs = self.durations[si]
            P, S = len(durs), steps_per_slide[si]
            para_steps = defaultdict(list)
            for j in range(S):
                para_steps[min(P - 1, j * P // S)].append(j)
            t, events, marks = o.intro, [], []
            for k in range(P):
                m = len(para_steps.get(k, []))
                for i in range(m):
                    events.append(round(t + o.step_spacing * i, 3))
                start = (t + o.step_spacing * (m - 1) + o.lead) if m else t + 0.2
                marks.append((round(start, 3), durs[k][1], durs[k][0]))
                t = start + durs[k][0] + o.gap
            total = round(t + (o.tail_last if si == n - 1 else o.tail), 3)
            self.schedule[si] = {'events': events, 'total': total}
            self._assemble_audio(si, marks, total)
        grand = sum(v['total'] for v in self.schedule.values())
        print(f'video total: {grand/60:.1f} min')

    def _assemble_audio(self, si, marks, total):
        adir = os.path.join(self.work, 'audio')
        parts, cur = [], 0.0
        for idx, (start, wav, dur) in enumerate(marks):
            gap = start - cur
            if gap > 0.005:
                sil = os.path.join(adir, f'sil_{si:02d}_{idx}.wav')
                run_ffmpeg(['-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
                            '-t', f'{gap:.3f}', '-c:a', 'pcm_s16le', sil])
                parts.append(sil)
            parts.append(wav)
            cur = start + dur
        tail = total - cur
        if tail > 0.005:
            sil = os.path.join(adir, f'sil_{si:02d}_tail.wav')
            run_ffmpeg(['-f', 'lavfi', '-i', 'anullsrc=r=24000:cl=mono',
                        '-t', f'{tail:.3f}', '-c:a', 'pcm_s16le', sil])
            parts.append(sil)
        lst = os.path.join(adir, f'list_{si:02d}.txt')
        with open(lst, 'w') as f:
            for p in parts:
                f.write(f"file '{p}'\n")
        run_ffmpeg(['-f', 'concat', '-safe', '0', '-i', lst,
                    '-c:a', 'pcm_s16le',
                    os.path.join(adir, f'slide_{si:02d}.wav')])

    # -------- 4. record (real-time, one slide per video) --------
    async def record(self, targets):
        from playwright.async_api import async_playwright
        o = self.opt
        hide_css = self.HIDE_CSS.replace('WIDTH', str(o.width))
        async with async_playwright() as p:
            for si in targets:
                sched = self.schedule[si]
                kw = {'executable_path': self.chromium} if self.chromium else {}
                browser = await p.chromium.launch(**kw)
                ctx = await browser.new_context(
                    viewport={'width': o.width, 'height': o.height},
                    record_video_dir=os.path.join(self.work, 'rec'),
                    record_video_size={'width': o.width, 'height': o.height})
                page = await ctx.new_page()
                await page.goto(self.url)
                await page.add_style_tag(content=hide_css)
                await page.evaluate(self.PREP_JS, si)
                await page.wait_for_timeout(700)
                t0 = time.monotonic()
                for ev in sched['events']:
                    delay = ev - (time.monotonic() - t0)
                    if delay > 0:
                        await asyncio.sleep(delay)
                    await page.evaluate('advanceStep()')
                remain = sched['total'] - (time.monotonic() - t0)
                if remain > 0:
                    await asyncio.sleep(remain)
                video = page.video
                await page.close()
                path = await video.path()
                await ctx.close()
                await browser.close()
                final = os.path.join(self.work, 'rec', f'slide_{si:02d}.webm')
                os.replace(path, final)
                print(f'recorded slide {si+1}/{self.data["count"]} '
                      f'({sched["total"]:.1f}s)', flush=True)

    # -------- 5. mux + concat --------
    def mux_concat(self):
        files = []
        for si in sorted(self.schedule):
            webm = os.path.join(self.work, 'rec', f'slide_{si:02d}.webm')
            wav = os.path.join(self.work, 'audio', f'slide_{si:02d}.wav')
            mp4 = os.path.join(self.work, 'mp4', f'slide_{si:02d}.mp4')
            total = self.schedule[si]['total']
            trim = max(0.0, ffprobe_duration(webm) - total)
            run_ffmpeg(['-ss', f'{trim:.3f}', '-i', webm, '-i', wav,
                        '-map', '0:v', '-map', '1:a', '-t', f'{total:.3f}',
                        '-c:v', 'libx264', '-preset', 'medium',
                        '-crf', str(self.opt.crf), '-r', str(self.opt.fps),
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac', '-b:a', '160k', '-ar', '24000', mp4])
            files.append(mp4)
        lst = os.path.join(self.work, 'concat.txt')
        with open(lst, 'w') as f:
            for p in files:
                f.write(f"file '{p}'\n")
        run_ffmpeg(['-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy',
                    self.opt.out])
        print(f'FINAL: {self.opt.out} ({ffprobe_duration(self.opt.out):.1f}s)')


async def amain(opt):
    vb = VideoBuilder(opt)
    await vb.extract()
    vb.gen_tts()
    vb.build_schedule()
    targets = opt.slides if opt.slides else sorted(vb.schedule)
    missing = [si for si in sorted(vb.schedule)
               if si not in targets and not os.path.exists(
                   os.path.join(vb.work, 'rec', f'slide_{si:02d}.webm'))]
    if missing:
        die(f'--slides 指定外のスライド {[m+1 for m in missing]} の録画が '
            f'workdir にありません。全スライドを録画するか workdir を確認してください。')
    await vb.record(targets)
    vb.mux_concat()


def main():
    ap = argparse.ArgumentParser(
        description='slide.html から合成音声付き動画を生成する')
    ap.add_argument('--slide', required=True, help='slide.html のパス')
    ap.add_argument('--out', required=True, help='出力 mp4 のパス')
    ap.add_argument('--workdir', default=None,
                    help='中間ファイル置き場（既定: 出力先と同名の .work ディレクトリ）')
    ap.add_argument('--slides', type=int, nargs='*', default=None,
                    help='再録画するスライド番号（1始まり）。省略時は全スライド')
    ap.add_argument('--speaker', type=int, default=2,
                    help='VOICEVOX 話者ID（既定: 2 = 四国めたんノーマル）')
    ap.add_argument('--speed', type=float, default=1.1, help='読み上げ速度')
    ap.add_argument('--voicevox-url', default='http://127.0.0.1:50021')
    ap.add_argument('--chromium', default=None, help='Chromium 実行ファイルのパス')
    ap.add_argument('--width', type=int, default=1280)
    ap.add_argument('--height', type=int, default=720)
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--crf', type=int, default=18, help='x264 品質（小さいほど高品質）')
    ap.add_argument('--lead', type=float, default=0.7,
                    help='アニメーション発火からナレーション開始までの秒数')
    ap.add_argument('--gap', type=float, default=0.35, help='段落間の無音秒数')
    ap.add_argument('--intro', type=float, default=0.6, help='スライド冒頭の間')
    ap.add_argument('--tail', type=float, default=0.5, help='スライド末尾の間')
    ap.add_argument('--tail-last', type=float, default=1.2, help='最終スライド末尾の間')
    ap.add_argument('--step-spacing', type=float, default=0.55,
                    help='同一段落内の連続ステップの間隔')
    opt = ap.parse_args()

    if not os.path.exists(opt.slide):
        die(f'slide not found: {opt.slide}')
    if opt.workdir is None:
        opt.workdir = os.path.splitext(os.path.abspath(opt.out))[0] + '.work'
    if opt.slides:
        opt.slides = [s - 1 for s in opt.slides]
    os.makedirs(os.path.dirname(os.path.abspath(opt.out)) or '.', exist_ok=True)

    asyncio.run(amain(opt))


if __name__ == '__main__':
    main()
