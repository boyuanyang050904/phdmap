// Render a JS-heavy page with the pre-installed Playwright Chromium.
// usage: node lib/render.js URL [waitMs]  -> JSON {status, final_url, html} on stdout
const { chromium } = require('playwright');
(async () => {
  const url = process.argv[2];
  const wait = parseInt(process.argv[3] || '2500', 10);
  const opts = {};
  if (process.env.HTTPS_PROXY) opts.proxy = { server: process.env.HTTPS_PROXY };
  const browser = await chromium.launch(opts);
  const ctx = await browser.newContext({ userAgent: process.env.PHDMAP_UA || undefined });
  const page = await ctx.newPage();
  let status = 0, html = '', final = url;
  try {
    const r = await page.goto(url, { timeout: 60000, waitUntil: 'domcontentloaded' });
    status = r ? r.status() : 0;
    await page.waitForTimeout(wait);
    html = await page.content();
    final = page.url();
  } catch (e) {
    process.stderr.write(String(e));
  }
  await browser.close();
  process.stdout.write(JSON.stringify({ status, final_url: final, html }));
})();
