/** One source of truth for language, timeline and output dimensions. */
export function outputPlans(props, hasEnglish) {
  const ratio = props.aspect_ratio || '9:16';
  if (!['9:16', '16:9', 'dual'].includes(ratio)) throw Error('Unsupported output aspect ratio');
  // 16:9 reads English unless the brief chose a Vietnamese-only 16:9 (audio_language 'vi').
  const viHorizontal = ratio === '16:9' && props.audio_language === 'vi';
  if (ratio !== '9:16' && !viHorizontal && (!hasEnglish || !props.en_scenes || !props.en_duration)) throw Error('English track and timeline required');
  const vertical = {...props, width: 1080, height: 1920, hideSubtitles: false, audioSrc: 'narration.wav'};
  const horizontal = viHorizontal
    ? {...props, width: 1920, height: 1080, hideSubtitles: true, audioSrc: 'narration.wav'}
    : {...props, scenes: props.en_scenes, duration: props.en_duration,
       width: 1920, height: 1080, hideSubtitles: true, audioSrc: 'narration_en.wav'};
  return ratio === 'dual' ? [{file: 'video_9x16.mp4', props: vertical}, {file: 'video_16x9.mp4', props: horizontal}]
    : [{file: 'video.mp4', props: ratio === '16:9' ? horizontal : vertical}];
}
