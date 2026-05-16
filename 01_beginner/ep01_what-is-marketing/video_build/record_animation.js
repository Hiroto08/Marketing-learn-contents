/**
 * slide_record.html のアニメーション再生を Playwright で録画する。
 *
 * 機能:
 *   - コントロール・ナレーション非表示のスライドを使用
 *   - durations.json の実際の音声長さに合わせて SLIDES_META と STEPS のタイミングを同期
 *   - Font Awesome はローカルファイルを使用（CDN 不要）
 *
 * Usage:
 *   NODE_PATH=/opt/node22/lib/node_modules \
 *   PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *   node record_animation.js <slide_record.html> <out_dir> [durations.json]
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const slideHtmlPath = process.argv[2];
const outDir        = process.argv[3];
const durationsPath = process.argv[4] || path.join(outDir, 'durations.json');

if (!slideHtmlPath || !outDir) {
  console.error('Usage: node record_animation.js <slide_record.html> <out_dir> [durations.json]');
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });

// ── durations.json から各スライドの音声長を読み込む ──────────────────────────
let audioDurations = null;
if (fs.existsSync(durationsPath)) {
  const d = JSON.parse(fs.readFileSync(durationsPath, 'utf8'));
  audioDurations = d.durations; // { "0": 28.2, "1": 41.7, ... }
  console.log(`Loaded audio durations from: ${durationsPath}`);
} else {
  console.warn(`durations.json not found at ${durationsPath} — using original SLIDES_META timing`);
}

// 総録画時間を計算
const totalSecs = audioDurations
  ? Math.ceil(Object.values(audioDurations).reduce((a, b) => a + b, 0)) + 3
  : 605;

console.log(`Total recording time: ${totalSecs}s`);

function formatTime(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2,'0')}:${String(s % 60).padStart(2,'0')}`;
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: ['--disable-web-security', '--autoplay-policy=no-user-gesture-required'],
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: {
      dir: outDir,
      size: { width: 1280, height: 720 },
    },
  });

  const page = await context.newPage();
  const fileUrl = `file://${path.resolve(slideHtmlPath)}`;

  console.log('Loading slide_record.html ...');
  await page.goto(fileUrl, { waitUntil: 'load', timeout: 60000 });

  // フォント・アイコン読み込みの完全待機（ローカル FA でも念のため）
  await page.waitForTimeout(3000);

  // Font Awesome の読み込み確認
  const faLoaded = await page.evaluate(() => {
    const el = document.createElement('i');
    el.className = 'fa-solid fa-check';
    el.style.visibility = 'hidden';
    document.body.appendChild(el);
    const style = window.getComputedStyle(el, '::before');
    const loaded = style.fontFamily.includes('Font Awesome') ||
                   style.content !== 'none';
    document.body.removeChild(el);
    return loaded;
  });
  console.log(`Font Awesome loaded: ${faLoaded}`);

  // ── SLIDES_META と STEPS のタイミングを音声長に合わせて再計算 ──────────────
  if (audioDurations) {
    await page.evaluate((durs) => {
      // 各スライドの新しい開始時刻を音声長から積算
      const newStarts = [];
      let t = 0;
      for (let i = 0; i < SLIDES_META.length; i++) {
        newStarts.push(t);
        const origDur = SLIDES_META[i].end - SLIDES_META[i].start;
        t += (durs[i] !== undefined ? durs[i] : origDur);
      }

      // STEPS の絶対時刻をシフト（スライド内の相対位置は保持）
      STEPS.forEach(step => {
        const si = step.si;
        const origSlideStart = SLIDES_META[si].start;
        const relTime = step.t - origSlideStart;          // スライド内相対時刻
        step.t = newStarts[si] + relTime;                 // 新しい絶対時刻
      });

      // SLIDES_META の start/end を更新
      SLIDES_META.forEach((meta, i) => {
        const origDur = meta.end - meta.start;
        const newDur = durs[i] !== undefined ? durs[i] : origDur;
        meta.start = newStarts[i];
        meta.end   = newStarts[i] + newDur;
      });

      console.log('Timing synced:', SLIDES_META.map(m => `${m.start.toFixed(1)}-${m.end.toFixed(1)}`).join(' | '));
    }, Object.fromEntries(
      Object.entries(audioDurations).map(([k, v]) => [parseInt(k), v])
    ));
    console.log('SLIDES_META timing synced to audio durations.');
  }

  // 最初のスライドが表示されているか確認
  const firstSlide = await page.evaluate(() => {
    const s = document.querySelector('.slide.active');
    return s ? s.id : '(none)';
  });
  console.log(`Active slide at start: ${firstSlide}`);

  // 自動再生開始（#ctrl が非表示のためボタンクリックの代わりに JS で直接起動）
  await page.evaluate(() => {
    state.playing = true;
    state.elapsed = 0;
    state.lastRAF  = null;
    if (typeof $btnPlay !== 'undefined') {
      $btnPlay.textContent = '⏸ 一時停止';
    }
    // tick() を起動（内部で rAF ループが始まる）
    if (typeof tick === 'function') {
      tick();
    }
  });
  console.log(`Recording started (${totalSecs}s) ...`);

  const startTime = Date.now();
  const interval = setInterval(() => {
    const elapsed = Date.now() - startTime;
    const remaining = Math.max(0, totalSecs * 1000 - elapsed);
    process.stdout.write(`\r  ${formatTime(elapsed)} / ${formatTime(totalSecs * 1000)}  `);
  }, 5000);

  await page.waitForTimeout(totalSecs * 1000);
  clearInterval(interval);
  process.stdout.write('\n');
  console.log('Recording complete. Saving ...');

  const video = await page.video();
  await context.close();
  await browser.close();

  if (video) {
    const rawPath = await video.path();
    const destPath = path.join(outDir, 'slides_animation.webm');
    fs.renameSync(rawPath, destPath);
    const stat = fs.statSync(destPath);
    console.log(`Saved: ${destPath} (${(stat.size / 1024 / 1024).toFixed(1)} MB)`);
  } else {
    console.error('ERROR: No video recorded.');
    process.exit(1);
  }
})().catch(err => {
  console.error(err.message);
  process.exit(1);
});
