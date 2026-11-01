import { test, expect } from '@playwright/test';

test('legacy Prompts bookmark redirects to Video Create and is absent from navigation', async ({ page }) => {
  await page.route('**/api/**', route => route.fulfill({
    status: 404,
    contentType: 'application/json',
    body: JSON.stringify({ detail: 'No API fixture needed for the route compatibility check.' }),
  }));
  await page.goto('/#/prompts?workspace_id=workspace-a');
  await expect.poll(() => page.evaluate(() => window.location.hash)).toBe('#/video?workspace_id=workspace-a');
  await expect(page.getByRole('heading', { name: 'Create video' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Prompt Preparation' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Prompts' })).toHaveCount(0);
});
