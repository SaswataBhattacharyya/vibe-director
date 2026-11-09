/** Real CPU MCP acceptance. All media/state lives in a test-owned temporary root. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { mkdtemp, readFile, rm, stat, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const runtime = resolve(process.argv[2] ?? 'local_data/runtimes/kdenlive-mcp');
const requireRuntime = createRequire(join(runtime, 'apps/mcp-server/package.json'));
const { Client } = await import(pathToFileURL(requireRuntime.resolve('@modelcontextprotocol/sdk/client/index.js')));
const { StdioClientTransport } = await import(pathToFileURL(requireRuntime.resolve('@modelcontextprotocol/sdk/client/stdio.js')));
const scratch = await mkdtemp(join(tmpdir(), 'vibe-kdenlive-check-'));
const meltAudit = join(scratch, 'melt-calls.log');
const meltWrapper = join(scratch, 'melt-audit');
await writeFile(meltWrapper, `#!/bin/sh\nprintf '%s\\n' "$@" >> '${meltAudit}'\nexec /usr/bin/melt "$@"\n`, { mode: 0o700 });
const client = new Client({ name: 'vibe-cpu-acceptance', version: '1.0.0' });
const transport = new StdioClientTransport({ command: process.execPath,
  args: [join(runtime, 'apps/mcp-server/dist/cli.js'), '--root', scratch, '--client-id', 'vibe-cpu-acceptance'],
  cwd: runtime, stderr: 'pipe',
  env: { ...process.env, QT_QPA_PLATFORM: 'offscreen', MELT_PATH: meltWrapper,
    FFMPEG_PATH: '/usr/bin/ffmpeg', FFPROBE_PATH: '/usr/bin/ffprobe' } });
let diagnostics = '';
transport.stderr?.on('data', chunk => { diagnostics = (diagnostics + chunk).slice(-12000); });
const call = async (name, args = {}) => {
  const response = await client.callTool({ name, arguments: args }, undefined, { timeout: 60000 });
  const envelope = response.structuredContent;
  if (response.isError || !envelope?.ok) throw new Error(`${name}: ${JSON.stringify(envelope ?? response.content)}`);
  return envelope.data;
};
const wait = async id => {
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    const job = await call('job_get', { jobId: id });
    if (job.status === 'succeeded') return job;
    if (['failed', 'cancelled'].includes(job.status)) throw new Error(JSON.stringify(job));
    await new Promise(done => setTimeout(done, 100));
  }
  await call('job_cancel', { jobId: id });
  throw new Error('MCP job exceeded 60 seconds');
};
const hash = async path => createHash('sha256').update(await readFile(path)).digest('hex');
try {
  const media = ['a.mkv', 'b.mkv'].map(name => join(scratch, name));
  for (const [index, path] of media.entries()) execFileSync('/usr/bin/ffmpeg', ['-v', 'error',
    '-f', 'lavfi', '-i', `testsrc2=size=320x180:rate=30:duration=2`,
    '-f', 'lavfi', '-i', `sine=frequency=${440 + index * 100}:sample_rate=48000:duration=2`,
    '-shortest', '-c:v', 'ffv1', '-c:a', 'pcm_s16le', path], { timeout: 30000 });
  const originalHashes = await Promise.all(media.map(hash));
  await client.connect(transport);
  const catalog = await client.listTools();
  for (const name of ['project_create', 'media_import', 'timeline_trim_clip', 'preview_submit',
    'render_submit', 'job_verify', 'interchange_export', 'job_cancel']) {
    assert(catalog.tools.some(tool => tool.name === name), `Missing tool: ${name}`);
  }
  const project = await call('project_create', { path: join(scratch, 'project'), name: 'Vibe CPU test',
    settings: { fps: { numerator: 30, denominator: 1 }, width: 320, height: 180, audioSampleRate: 48000 } });
  const imported = await call('media_import', { projectId: project.id, expectedRevision: project.revision,
    paths: media, mode: 'managed' });
  const clips = await call('timeline_add_clips', { projectId: project.id, expectedRevision: imported.revision,
    requests: imported.imported.map(asset => ({ assetId: asset.id, sourceIn: 0, sourceOut: 60, linkedAv: true })),
    options: { mode: 'append' } });
  const videoTrack = clips.project.tracks.find(track => track.kind === 'video');
  const second = videoTrack.clips[1];
  // Trim both linked streams identically, retaining their shared timeline start.
  let revision = clips.revision;
  for (const clipId of [second.id, ...second.linkedClipIds]) {
    const result = await call('timeline_trim_clip', { projectId: project.id, expectedRevision: revision,
      clipId, options: { sourceIn: 15, preserveTimelineStart: true } });
    revision = result.revision;
  }
  const conflict = await client.callTool({ name: 'timeline_add_track', arguments: {
    projectId: project.id, expectedRevision: project.revision, kind: 'video' } });
  assert.equal(conflict.structuredContent?.error?.code, 'REVISION_CONFLICT');
  const preview = await call('preview_submit', { projectId: project.id, kind: 'range', start: 45, end: 75 });
  const previewJob = await wait(preview.id);
  const render = await call('render_submit', { projectId: project.id, profileId: 'mezzanine-ffv1', outputName: 'join' });
  const rendered = await wait(render.id);
  const verification = await call('job_verify', { jobId: render.id });
  assert.equal(verification.valid, true, JSON.stringify(verification));
  assert.equal(verification.metrics.videoFrames, 105);
  assert.equal(verification.metrics.durationSeconds, 3.5);
  assert((await readFile(meltAudit, 'utf8')).includes('-consumer'), 'Actual melt rendering was not observed');
  const probe = JSON.parse(execFileSync('/usr/bin/ffprobe', ['-v', 'error', '-show_streams',
    '-show_format', '-of', 'json', rendered.outputPath], { encoding: 'utf8', timeout: 10000 }));
  assert.equal(Number(probe.format.duration), 3.5);
  assert(probe.streams.some(stream => stream.codec_type === 'audio'));
  const exported = await call('interchange_export', { projectId: project.id, format: 'kdenlive', outputName: 'editable' });
  assert((await readFile(exported.path, 'utf8')).includes('<mlt'));
  const cancelled = await call('render_submit', { projectId: project.id, profileId: 'mezzanine-ffv1', outputName: 'cancel-test' });
  await call('job_cancel', { jobId: cancelled.id });
  const cancelledJob = await call('job_get', { jobId: cancelled.id });
  assert.equal(cancelledJob.status, 'cancelled');
  assert.deepEqual(await Promise.all(media.map(hash)), originalHashes);
  console.log(JSON.stringify({ runtime, tools: catalog.tools.length, revision, preview: previewJob,
    render: rendered, verification, export: { targetVersion: exported.targetVersion, fidelity: exported.fidelity },
    cancellation: cancelledJob.status, actualMeltObserved: true, sourceHashesUnchanged: true }, null, 2));
} catch (error) {
  console.error(diagnostics);
  throw error;
} finally {
  await client.close();
  await transport.close();
  await rm(scratch, { recursive: true, force: true });
  await assert.rejects(stat(scratch), { code: 'ENOENT' });
  console.log('Cleanup verified: temporary media, project and MCP state removed.');
}
