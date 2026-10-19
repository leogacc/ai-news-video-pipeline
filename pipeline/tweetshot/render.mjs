#!/usr/bin/env node
/* Screenshot a self-contained local HTML file's card element with the
 * bundled Chromium. Everything (images, CSS, fonts) must be inlined in
 * the HTML — the browser has no network access in this environment.
 * Usage: node render.mjs <html_path> <selector> <out_png> [width_px] */
import puppeteer from 'puppeteer-core';
import fs from 'fs';

const [htmlPath, selector, outPng, widthArg] = process.argv.slice(2);
const width = parseInt(widthArg || '1080', 10);
if (!htmlPath || !selector || !outPng) {
  console.error('usage: node render.mjs <html> <selector> <out.png> [width]');
  process.exit(2);
}

const browser = await puppeteer.launch({
  executablePath: '/opt/meta-chromium/chrome',
  args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage',
         '--force-color-profile=srgb', '--font-render-hinting=none'],
  headless: true,
});
try {
  const page = await browser.newPage();
  await page.setViewport({ width, height: 800, deviceScaleFactor: 2 });
  await page.goto('file://' + htmlPath, { waitUntil: 'load', timeout: 30000 });
  await page.evaluate(() => document.fonts.ready.then(() => {}).catch(() => {}));
  await new Promise(r => setTimeout(r, 600));
  const el = await page.$(selector);
  if (!el) throw new Error('selector not found: ' + selector);
  await el.screenshot({ path: outPng });
  const st = fs.statSync(outPng);
  console.log(`[tweetshot] ${outPng} (${st.size} bytes)`);
} finally {
  await browser.close();
}
