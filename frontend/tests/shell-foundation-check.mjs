import assert from 'node:assert/strict';
import { chromium } from 'playwright';
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'], executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE || undefined });
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 850 } });
  await page.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:8082'}/#/home`);
  const profile = page.getByRole('button', { name: 'Open appearance settings' });
  await profile.click();
  assert.equal(await page.getByRole('dialog', { name: 'Appearance' }).count(), 1);
  assert.equal(await page.evaluate(() => document.activeElement?.getAttribute('data-palette')), 'quiet');
  for (const [name, id] of [['Concrete & ink','grit'], ['Midnight mixtape','mixtape'], ['Quiet comic','quiet']]) {
    await page.getByRole('button', { name, exact: true }).click();
    assert.equal(await page.locator('html').getAttribute('data-palette'), id);
    assert.equal(await page.getByRole('button', { name, exact: true }).getAttribute('aria-pressed'), 'true');
  }
  await page.getByRole('button', { name: 'Midnight mixtape', exact: true }).click();
  await page.reload();
  assert.equal(await page.locator('html').getAttribute('data-palette'), 'mixtape');
  await page.getByRole('button', { name: 'Open appearance settings' }).click();
  await page.keyboard.press('Escape');
  assert.equal(await page.getByRole('dialog').isVisible(), false);
  assert.equal(await page.evaluate(() => document.activeElement?.getAttribute('aria-label')), 'Open appearance settings');
  await page.getByRole('link', { name: 'Start a story' }).click();
  await page.waitForURL('**/#/story');
  assert.equal(await page.locator('.mascot').getAttribute('data-pose'), 'neutral');
  assert.equal(await page.getByRole('button', { name: 'Replay Clapper hello' }).count(), 1);
  await page.getByRole('button', { name: 'Replay Clapper hello' }).click();
  const mobile = await browser.newPage({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  await mobile.goto(`${process.env.VIBE_UI_BASE_URL || 'http://127.0.0.1:8082'}/#/home`);
  await mobile.getByRole('button', { name: 'Open navigation menu' }).click();
  assert.equal(await mobile.getByRole('navigation', { name: 'Studio navigation' }).count(), 1);
  await mobile.getByRole('link', { name: 'Start a story' }).click();
  await mobile.waitForURL('**/#/story');
  const metrics = await mobile.evaluate(() => {
    const footer = document.querySelector('.studio-taskbar').getBoundingClientRect();
    const content = document.querySelector('.studio-page-content').getBoundingClientRect();
    const svg = document.querySelector('.mascot .body-group');
    return { footerTop: footer.top, footerBottom: footer.bottom, innerHeight, scrollHeight: document.documentElement.scrollHeight, paddingBottom: getComputedStyle(document.querySelector('.studio-shell')).paddingBottom, motion: getComputedStyle(svg).animationName, pose: document.querySelector('.mascot').dataset.pose };
  });
  assert.equal(metrics.footerBottom, 844);
  assert.ok(parseFloat(metrics.paddingBottom) >= 56);
  assert.equal(metrics.motion, 'none');
  assert.equal(metrics.pose, 'neutral');
  assert.ok(await mobile.getByRole('link', { name: 'Video Create', exact: true }).isVisible());
  console.log('PASS: profile palette, all themes, Escape/focus, story route, Clapper replay, mobile navigation/taskbar, reduced motion');
} finally { await browser.close(); }
