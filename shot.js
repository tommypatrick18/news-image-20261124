// Screenshot page.html -> entry.png + overflow audit (Chromium 1255, puppeteer-core).
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer-core');

const DIR = '/home/hatch/workspace/makefun/news-image-20261124-work';
const CHROME = '/home/hatch/.cache/ms-playwright/chromium-1255/chrome-linux64/chrome';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: true,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--force-device-scale-factor=1',
           '--hide-scrollbars'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1024, height: 1024 });
  await page.goto('file://' + path.join(DIR, 'page.html'), { waitUntil: 'load', timeout: 60000 });
  await new Promise(r => setTimeout(r, 1500));

  const audit = await page.evaluate(() => {
    const out = { OVERFLOW_ITEMS: 0, PAGE_OVER: 0, items: [] };
    const doc = document.documentElement;
    if (doc.scrollWidth > 1024 || doc.scrollHeight > 1024) {
      out.PAGE_OVER = 1;
      out.items.push(`PAGE scroll ${doc.scrollWidth}x${doc.scrollHeight}`);
    }
    const els = document.querySelectorAll('body *');
    for (const el of els) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      // element sticking out of the 1024x1024 canvas
      if (r.right > 1024.5 || r.bottom > 1024.5 || r.left < -0.5 || r.top < -0.5) {
        out.OVERFLOW_ITEMS++;
        out.items.push(`OUT ${el.tagName}.${String(el.className).slice(0, 30)} ` +
          `rect ${r.left.toFixed(0)},${r.top.toFixed(0)} ${r.width.toFixed(0)}x${r.height.toFixed(0)} ` +
          `"${(el.textContent || '').trim().slice(0, 40)}"`);
      }
      // text clipped inside a fixed box (scroll bigger than visible box)
      if (el.children.length === 0 && el.textContent.trim()) {
        if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1) {
          const cs = getComputedStyle(el);
          if (cs.overflow === 'hidden' || cs.textOverflow === 'ellipsis' ||
              cs.whiteSpace === 'nowrap') {
            out.OVERFLOW_ITEMS++;
            out.items.push(`CLIP ${el.tagName}.${String(el.className).slice(0, 30)} ` +
              `scroll ${el.scrollWidth}x${el.scrollHeight} vs client ${el.clientWidth}x${el.clientHeight} ` +
              `"${el.textContent.trim().slice(0, 50)}"`);
          }
        }
      }
    }
    return out;
  });
  console.log('AUDIT', JSON.stringify(audit, null, 1));
  await page.screenshot({ path: path.join(DIR, 'entry.png'), type: 'png' });
  const st = fs.statSync(path.join(DIR, 'entry.png'));
  console.log('entry.png bytes:', st.size);
  await browser.close();
})().catch(e => { console.error('FATAL', e); process.exit(1); });
