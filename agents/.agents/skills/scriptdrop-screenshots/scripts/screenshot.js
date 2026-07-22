#!/usr/bin/env node
/**
 * Playwright screenshot template for ScriptDrop UI verification.
 *
 * Copy this file to <worktree>/tmp/screenshot.js and customize:
 *  - The target URL (default: pharmacy show page for ID 539)
 *  - Any page interactions before the screenshot
 *
 * Run inside the Docker container:
 *   docker exec -w /tmp <container> node /tmp/screenshot.js
 */

const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();

  // Login
  await page.goto('http://localhost:4000/sessions/new');
  await page.fill('#username', 'superuser@example.com');
  await page.fill('input[type="password"]', 'supersecret');
  await page.click('button:has-text("Login")');
  await page.waitForTimeout(2000);

  // Accept ToS if needed
  if (page.url().includes('terms_of_service')) {
    const acceptBtn = page.locator('button:has-text("I Agree")');
    if (await acceptBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
      await acceptBtn.click();
      await page.waitForTimeout(2000);
    }
  }

  // Navigate to target page — replace URL as needed
  await page.goto('http://localhost:4000/pharmacies/539');
  await page.waitForTimeout(3000);

  // Screenshots
  await page.screenshot({ path: '/tmp/fullpage.png', fullPage: true });
  console.log('Full page screenshot saved');

  await browser.close();
})();
