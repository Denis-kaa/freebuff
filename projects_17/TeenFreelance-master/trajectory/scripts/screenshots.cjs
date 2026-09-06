/**
 * Playwright browser pass over the deployed Freeстарт presentation (:8022).
 *
 * Runs on whimco (global playwright + chromium cache):
 *   NODE_PATH=$(npm root -g) node screenshots.cjs
 *
 * Produces: /opt/teenfreelance/frontend/freestart/shots/*.png
 * Report:   console errors, page errors, failed requests, video state.
 */
const { chromium } = require('playwright');

const BASE = 'http://127.0.0.1:8022';
const OUT = '/opt/teenfreelance/frontend/freestart/shots';

const fs = require('fs');
fs.mkdirSync(OUT, { recursive: true });

const report = { console: [], pageErrors: [], requestFailed: [], video: {}, shots: [] };

function watch(page, label) {
  page.on('console', (m) => {
    if (m.type() === 'error') report.console.push(`[${label}] ${m.text()}`);
  });
  page.on('pageerror', (e) => report.pageErrors.push(`[${label}] ${e.message}`));
  page.on('requestfailed', (r) => report.requestFailed.push(`[${label}] ${r.url()} → ${r.failure()?.errorText}`));
}

async function shot(page, name) {
  const p = `${OUT}/${name}.png`;
  await page.screenshot({ path: p, fullPage: false });
  report.shots.push(name);
  console.log('shot:', name);
}

(async () => {
  const browser = await chromium.launch();

  // ---------- DESKTOP ----------
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  watch(page, 'desktop');

  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await shot(page, '01-desktop-intro-top');

  // video state (autoplay muted loop)
  const video = await page.evaluate(() => {
    const v = document.querySelector('video');
    if (!v) return { present: false };
    return {
      present: true,
      paused: v.paused,
      muted: v.muted,
      readyState: v.readyState,
      duration: v.duration,
      posterLoaded: v.poster !== '',
    };
  });
  report.video = video;

  // scroll to diagnosis (anchor travel under sticky header)
  await page.evaluate(() => document.querySelector('#concept-diagnosis')?.scrollIntoView());
  await page.waitForTimeout(600);
  await shot(page, '02-desktop-diagnosis');

  // Skill Score section
  await page.evaluate(() => document.querySelector('#skill-score')?.scrollIntoView());
  await page.waitForTimeout(400);
  await shot(page, '03-desktop-skill-score');

  // open questions (end of concept)
  await page.evaluate(() => document.querySelector('#open-questions')?.scrollIntoView());
  await page.waitForTimeout(400);
  await shot(page, '04-desktop-open-questions');

  // demo dashboard view
  await page.evaluate(() => {
    window.location.hash = 'dashboard';
  });
  await page.waitForTimeout(900);
  await shot(page, '05-desktop-dashboard');

  // ---------- MOBILE ----------
  const mob = await browser.newPage({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  watch(mob, 'mobile');

  await mob.goto(BASE + '/', { waitUntil: 'networkidle' });
  await mob.waitForTimeout(1200);
  await shot(mob, '06-mobile-intro');

  await mob.evaluate(() => {
    window.location.hash = 'dashboard';
  });
  await mob.waitForTimeout(900);
  await shot(mob, '07-mobile-dashboard');

  await browser.close();

  console.log('---REPORT---');
  console.log(JSON.stringify(report, null, 2));
})().catch((e) => {
  console.error('FATAL', e);
  process.exit(1);
});
