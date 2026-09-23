/** One source of truth for language, timeline and output dimensions. */
export function outputPlans(props, hasEnglish) {
  const ratio = props.aspect_ratio || '9:16';
  if (!['9:16', '16:9', 'dual'].includes(ratio)) throw Error('Unsupported output aspect ratio');
  // 16:9 reads English unless the brief chose a Vietnamese-only 16:9 (audio_language 'vi').
  const viHorizontal = ratio === '16:9' && props.audio_language === 'vi';
  if (ratio !== '9:16' && !viHorizontal && (!hasEnglish || !props.en_scenes || !props.en_duration)) throw Error('English track and timeline required');
  // audio_files: narration mixed with the CC0 bed/effects (sound.py); plain narration when the brief has no sound.
  const vi = props.audio_files?.vi || 'narration.wav', en = props.audio_files?.en || 'narration_en.wav';
  const vertical = {...props, width: 1080, height: 1920, hideSubtitles: false, audioSrc: vi};
  const horizontal = viHorizontal
    ? {...props, width: 1920, height: 1080, hideSubtitles: true, audioSrc: vi}
    : {...props, scenes: props.en_scenes, duration: props.en_duration,
       width: 1920, height: 1080, hideSubtitles: true, audioSrc: en};
  return ratio === 'dual' ? [{file: 'video_9x16.mp4', props: vertical}, {file: 'video_16x9.mp4', props: horizontal}]
    : [{file: 'video.mp4', props: ratio === '16:9' ? horizontal : vertical}];
}
