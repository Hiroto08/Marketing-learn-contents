/**
 * Playwright でスライドのアニメーション再生を丸ごと録画する。
 *
 * 流れ:
 *   1. slide.html を headless Chrome で開く（video recording 有効）
 *   2. #btn-play を押して自動再生を開始
 *   3. 全スライドの再生が終わるまで待機
 *   4. webm として保存 → 呼び出し側で mp4 に変換
 *
 * Usage:
 *   NODE_PATH=/opt/node22/lib/node_modules \
 *   PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *   node record_animation.js <slide.html> <out_dir> [total_secs]
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const slideHtmlPath = process.argv[2];
const outDir = process.argv[3];
const totalSecs = parseInt(process.argv[4] || '605', 10);

if (!slideHtmlPath || !outDir) {
  console.error('Usage: node record_animation.js <slide.html> <out_dir> [total_secs]');
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });

function formatTime(ms) {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    args: [
      '--disable-web-security',
      '--autoplay-policy=no-user-gesture-required',
    ],
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

  console.log('Loading slide.html ...');
  await page.goto(fileUrl);
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2000); // フォント・CDN の読み込みを待機

  // 最初のスライドが表示されているか確認
  const firstSlideVisible = await page.evaluate(() => {
    const s = document.querySelector('.slide.active');
    return s ? s.id : '(none)';
  });
  console.log(`First active slide: ${firstSlideVisible}`);

  // 自動再生ボタンをクリック
  await page.click('#btn-play');
  console.log(`Auto-play started. Recording ${totalSecs}s ...`);

  // 進捗を 30 秒ごとに表示
  const start = Date.now();
  const interval = setInterval(() => {
    const elapsed = Date.now() - start;
    const remaining = Math.max(0, totalSecs * 1000 - elapsed);
    console.log(`  ${formatTime(elapsed)} elapsed / ${formatTime(remaining)} remaining`);
  }, 30000);

  await page.waitForTimeout(totalSecs * 1000);
  clearInterval(interval);

  console.log('Recording complete. Saving video ...');

  // video.path() は context.close() 後に解決される
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
