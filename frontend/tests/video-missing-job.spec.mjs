import { test, expect } from '@playwright/test';

for (const mode of ['missing-on-resume', 'missing-on-poll', 'connection-error']) {
  test(`saved video recovery: ${mode}`, async ({ page }) => {
    let reads = 0;
    let writes = 0;
    await page.addInitScript(() => {
      if (sessionStorage.getItem('recovery-seeded')) return;
      sessionStorage.setItem('recovery-seeded', '1');
      const snapshot = {workflow_id:'minimax_h3_t2v_local_v1', prompt:'Keep this bench press prompt.', duration_seconds:8, resolution_preset:0.4};
      localStorage.setItem('vibe-video-draft-v1', JSON.stringify({workspaceId:'media-test', clipId:'clip-test', workflowId:snapshot.workflow_id, prompt:snapshot.prompt, duration:8, resolution:0.4}));
      localStorage.setItem('vibe-video-active-job-v1', JSON.stringify({jobId:'deleted-test', snapshot}));
      localStorage.setItem('vibe-story-selected-v1', 'deleted-story');
    });
    await page.route('**/api/**', route => {
      const req = route.request();
      if (req.method() !== 'GET') writes++;
      if (new URL(req.url()).pathname === '/api/video/jobs/deleted-test') {
        reads++;
        if (mode === 'connection-error') return route.fulfill({status:503,json:{detail:'Temporary outage'}});
        if (mode === 'missing-on-poll' && reads === 1) return route.fulfill({json:{job_id:'deleted-test',status:'running'}});
        return route.fulfill({status:404,json:{error:{code:'not_found',message:'Job not found'}}});
      }
      return route.fulfill({status:404,json:{detail:'Unused mocked route'}});
    });
    await page.goto('/#/take');
    if (mode === 'connection-error') {
      await expect.poll(() => reads).toBeGreaterThanOrEqual(2);
      expect(await page.evaluate(() => localStorage.getItem('vibe-video-active-job-v1'))).not.toBeNull();
      await expect(page.getByText('Recovering saved job', {exact:true})).toBeVisible();
    } else {
      await expect(page.getByText(/Recovery stopped; your draft prompt is kept/)).toBeVisible();
      const stoppedAt = reads;
      await page.waitForTimeout(3000);
      expect(reads).toBe(stoppedAt);
      expect(await page.evaluate(() => localStorage.getItem('vibe-video-active-job-v1'))).toBeNull();
      expect(await page.evaluate(() => JSON.parse(localStorage.getItem('vibe-video-draft-v1')).prompt)).toBe('Keep this bench press prompt.');
      await expect(page.getByText('Assemble story clips', {exact:true})).toHaveCount(0);
      await page.reload();
      await page.waitForTimeout(3000);
      expect(reads).toBe(stoppedAt);
    }
    expect(writes).toBe(0);
  });
}
