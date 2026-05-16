/**
 * Playwright で slide.html の各スライドをスクリーンショット撮影する。
 * 各スライドはすべてのアニメーション要素を表示済み状態でキャプチャする。
 *
 * Usage:
 *   NODE_PATH=/opt/node22/lib/node_modules \
 *   PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers \
 *   node screenshot_slides.js <slide.html> <out_dir>
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const slideHtmlPath = process.argv[2];
const outDir = process.argv[3];

if (!slideHtmlPath || !outDir) {
  console.error('Usage: node screenshot_slides.js <slide.html> <out_dir>');
  process.exit(1);
}

fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.setViewportSize({ width: 1280, height: 720 });

  const fileUrl = `file://${path.resolve(slideHtmlPath)}`;
  await page.goto(fileUrl);

  // フォント・CDN 読み込みを待機
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2500);

  const numSlides = await page.evaluate(() => SLIDES_META.length);
  console.log(`Slides found: ${numSlides}`);

  for (let i = 0; i < numSlides; i++) {
    // スライドを切り替えてすべての要素を表示状態にする
    await page.evaluate((idx) => {
      const meta = SLIDES_META[idx];

      // 全スライドを非表示
      document.querySelectorAll('.slide').forEach(s => s.classList.remove('active'));

      // 対象スライドを表示
      const target = document.getElementById(meta.id);
      if (!target) return;
      target.classList.add('active');

      // アニメーション要素を強制的に表示状態にする
      target.querySelectorAll('.se').forEach(el => {
        el.style.opacity = '1';
        el.style.transform = 'none';
        el.style.transition = 'none';
        el.style.filter = 'none';
      });

      // SVG 要素も表示
      target.querySelectorAll('svg').forEach(el => {
        el.style.opacity = '1';
      });
    }, i);

    await page.waitForTimeout(400);

    const imgPath = path.join(outDir, `slide_${String(i).padStart(2, '0')}.png`);
    await page.screenshot({ path: imgPath, type: 'png' });
    console.log(`  [${i + 1}/${numSlides}] ${path.basename(imgPath)}`);
  }

  await browser.close();
  console.log('Screenshots complete.');
})().catch(err => {
  console.error(err);
  process.exit(1);
});
