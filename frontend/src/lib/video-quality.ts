// Keep the historical "standard" setup key at 864 × 480 for saved manifests.
export const VIDEO_QUALITIES = [
  {key: 'standard', preset: 0.4, width: 864, height: 480, label: 'Low'},
  {key: 'standard_608', preset: 0.6, width: 1056, height: 608, label: 'Standard'},
  {key: 'medium', preset: 0.8, width: 1216, height: 672, label: 'Medium'},
  {key: 'high', preset: 0.98, width: 1344, height: 768, label: 'High'},
] as const;
export const T2V_QUALITIES = [
  {key: 't2v_low', preset: 0.8, width: 1216, height: 672, label: 'Low'},
  {key: 't2v_standard', preset: 0.98, width: 1344, height: 768, label: 'Standard'},
  {key: 't2v_high', preset: 1.5, width: 1664, height: 928, label: 'High'},
  {key: 't2v_max', preset: 2, width: 1920, height: 1088, label: 'Max'},
] as const;
export const ALL_VIDEO_QUALITIES = [...VIDEO_QUALITIES, ...T2V_QUALITIES];
export type VideoQuality = typeof ALL_VIDEO_QUALITIES[number]['key'];
export type VideoResolution = typeof ALL_VIDEO_QUALITIES[number]['preset'];
export const VIDEO_ASPECT_RATIOS = [
  {value: '16:9', label: 'Widescreen'},
  {value: '9:16', label: 'Phone · portrait'},
  {value: '4:3', label: 'Tablet · landscape'},
  {value: '3:4', label: 'Tablet · portrait'},
  {value: '1:1', label: 'Square'},
] as const;
export type VideoAspectRatio = typeof VIDEO_ASPECT_RATIOS[number]['value'];
export const qualityDimensions = (preset: number, aspectRatio: VideoAspectRatio = '16:9') => {
  const quality = ALL_VIDEO_QUALITIES.find(item => item.preset === preset);
  if (!quality) return 'Unknown resolution';
  let {width, height}: {width: number; height: number} = quality;
  if (aspectRatio === '9:16') [width, height] = [height, width];
  else if (aspectRatio !== '16:9') {
    const [numerator, denominator] = aspectRatio.split(':').map(Number);
    const area = width * height, ratio = numerator / denominator;
    width = Math.max(32, Math.round(Math.sqrt(area * ratio) / 32) * 32);
    height = Math.max(32, Math.round(Math.sqrt(area / ratio) / 32) * 32);
  }
  return `${width} × ${height}`;
};
