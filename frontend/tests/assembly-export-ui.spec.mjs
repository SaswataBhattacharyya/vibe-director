import { expect, test } from '@playwright/test';

test('accepted takes and optional audio flow through saved export playback', async ({ page }) => {
  const workspaceId = 'assembly-ui-workspace';
  const revisionId = 'accepted-screenplay-revision';
  const clipId = 'scene-1-shot-1-clip-1';
  const takeId = 'accepted-take-001';
  const audioId = 'pa-0123456789abcdef';
  const snapshotId = 'snapshot-ui-001';
  const manifestId = 'export-ui-001';
  const jobId = 'assembly-ui-job-001';
  let selections = {};
  let audioTracks = [];
  let exportJobs = [];
  let manifestSettings;

  await page.addInitScript(({ workspaceId }) => {
    localStorage.setItem('vibe-story-selected-v1', workspaceId);
  }, { workspaceId });

  await page.route(`**/api/story/workspaces/${workspaceId}/screenplay/revisions**`, route => route.fulfill({
    json: { items: [{ screenplay_revision_id: revisionId, accepted: true, stale: false }] },
  }));
  await page.route(`**/api/story/workspaces/${workspaceId}/assembly-preview**`, route => route.fulfill({
    json: { screenplay_revision_id: revisionId, clips: [{ clip_id: clipId, scene_number: 1, shot_number: 1,
      clip_number: 1, accepted_takes: [{ job_id: takeId, outputs: [{ playback_url: '/fixture/take.mp4' }] }],
      review_takes: [], missing_accepted_take: false }], missing_clip_count: 0, planning_incomplete: false, warnings: [] },
  }));
  await page.route(`**/api/story/workspaces/${workspaceId}/assembly-selection**`, async route => {
    if (route.request().method() === 'PUT') selections = (await route.request().postDataJSON()).selections;
    await route.fulfill({ json: { selections } });
  });
  await page.route(`**/api/story/workspaces/${workspaceId}/assembly-audio**`, async route => {
    if (route.request().method() === 'PUT') audioTracks = (await route.request().postDataJSON()).audio_tracks;
    await route.fulfill({ json: { audio_tracks: audioTracks } });
  });
  await page.route(`**/api/media/${workspaceId}/assets?kind=audio**`, route => route.fulfill({
    json: { total: 1, assets: [{ asset_id: audioId, workspace_id: workspaceId, kind: 'audio', filename: 'theme.wav',
      sha256: 'a'.repeat(64), media_type: 'audio/wav', size_bytes: 128, content_url: '/fixture/theme.wav',
      media: { duration_seconds: 20 } }] },
  }));
  await page.route(`**/api/story/workspaces/${workspaceId}/assembly-snapshots**`, async route => {
    if (route.request().method() === 'POST') {
      await route.fulfill({ json: { snapshot_id: snapshotId, snapshot_sha256: 'b'.repeat(64), created_at: new Date().toISOString(), snapshot: { state: 'awaiting_export_settings' } } });
    } else await route.fulfill({ json: { snapshots: [] } });
  });
  await page.route(`**/api/story/workspaces/${workspaceId}/assembly-exports**`, async route => {
    if (route.request().method() === 'POST') {
      const request = await route.request().postDataJSON();
      manifestSettings = request.settings;
      await route.fulfill({ json: { manifest_id: manifestId, manifest_sha256: 'c'.repeat(64), created_at: new Date().toISOString(),
        manifest: { state: 'ready_for_render', export_settings: request.settings } } });
    } else await route.fulfill({ json: { manifests: [] } });
  });
  await page.route(`**/api/story/workspaces/${workspaceId}/assembly-export-jobs**`, async route => {
    if (route.request().method() === 'POST') {
      exportJobs = [{ job_id: jobId, manifest_id: manifestId, state: 'completed', progress_percent: 100, output_asset_id: 'pa-exported-mp4' }];
      await route.fulfill({ json: exportJobs[0] });
    } else await route.fulfill({ json: { jobs: exportJobs } });
  });

  await page.goto('/#/take');
  const panel = page.getByRole('region', { name: 'Assemble story clips' });
  await expect(panel.getByText('Scene 1 · Shot 1 · Clip 1')).toBeVisible();
  await panel.getByRole('radio', { name: new RegExp(takeId.slice(0, 8)) }).check();
  await panel.getByRole('button', { name: 'Save choices' }).click();
  await expect(panel.getByText('1 of 1 clips selected · Saved')).toBeVisible();

  await panel.getByRole('button', { name: 'Add', exact: true }).click();
  await panel.getByRole('button', { name: 'Save audio choices' }).click();
  await expect(panel.getByRole('button', { name: 'Audio saved' })).toBeVisible();
  await panel.getByRole('button', { name: 'Freeze assembly choices' }).click();
  await expect(panel.getByText(snapshotId, { exact: true })).toBeVisible();
  await panel.getByLabel('Resolution').selectOption('720p');
  await panel.getByLabel('Frame rate').selectOption('30');
  await panel.getByLabel('Audio treatment').selectOption('preserve_and_mix');
  await panel.getByRole('button', { name: `Prepare export from ${snapshotId.slice(0, 16)}` }).click();
  await expect(panel.getByText(manifestId)).toBeVisible();
  expect(manifestSettings).toMatchObject({ resolution: '720p', frame_rate: 30, audio_policy: 'preserve_and_mix' });
  await panel.getByRole('button', { name: 'Render export' }).click();
  await expect(panel.locator('.assembly-export-result video')).toHaveAttribute('src', `/api/media/${workspaceId}/assets/pa-exported-mp4/content`);
  await expect(panel.getByRole('link', { name: 'Download MP4' })).toHaveAttribute('download', 'vibe-director-export.mp4');
  expect(selections).toEqual({ [clipId]: takeId });
  expect(audioTracks).toHaveLength(1);
  expect(audioTracks[0]).toMatchObject({ asset_id: audioId, start_seconds: 0, trim_start_seconds: 0, trim_end_seconds: 20, gain: 1 });
});
