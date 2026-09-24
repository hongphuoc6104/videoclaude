// Usage:
//   node renderer/render.mjs DIR --prepare        layout check + DIR/plans.json (no bundle, no render)
//   node renderer/render.mjs DIR --parts REQ.json  render the listed frame ranges, video only (muted)
//   node renderer/render.mjs DIR                   legacy single pass with audio (benchmarks, old scripts)
// The pipeline (adapters.render -> render_parts.py) uses --prepare then --parts; the
// parts are joined and the full mastered audio is muxed once in Python.
import {bundle} from '@remotion/bundler';
import {openBrowser, selectComposition, renderMedia} from '@remotion/renderer';
import {execFileSync} from 'node:child_process';
import {chromium} from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {outputPlans} from './outputs.mjs';

const [dir, mode = '--full', modeArg] = process.argv.slice(2);
const props = JSON.parse(fs.readFileSync(path.join(dir, 'props.json')));
const publicDir = path.join(dir, 'public');
// Must equal the Composition fps / calculateMetadata in index.tsx; --parts re-checks it.
const FPS = 30;

const plans = outputPlans(props, fs.existsSync(path.join(publicDir, 'narration_en.wav')));

async function layoutCheck() {
  // A pure 16:9 output hides subtitles entirely (see outputPlans in
  // outputs.mjs); checking Vietnamese cue geometry against a video that never
  // burns that text in was a check of nothing. Only 9:16/dual carry
  // burned-in subtitles, so only they get a real layout check.
  const hasSubtitles = props.aspect_ratio !== '16:9';
  let layoutResult;
  if (!hasSubtitles) {
    layoutResult = {
      passed: true,
      applies: false,
      checked_cues: 0,
      method: '16:9 output hides subtitles; no burned-in text to check',
      failures: []
    };
  } else {
    // Layout check using Playwright. Cues arrive pre-cut from Python
    // (adapters.subtitle_cues) -- this just checks the geometry of each cue
    // exactly as the renderer will show it, with no re-chunking here.
    const checkWidth = 1080;
    const checkHeight = 1920;
    const pw = await chromium.launch({executablePath: '/usr/bin/google-chrome', headless: true});
    const page = await pw.newPage({viewport: {width: checkWidth, height: checkHeight}});
    let failures = [];

    for (const cue of props.cues) {
      await page.setContent(`
        <div id="subtitle" style="position:absolute;bottom:100px;left:50%;transform:translateX(-50%);max-width:${checkWidth - 80}px;white-space:nowrap;font:800 32px/44px Arial;padding:10px 24px;box-sizing:border-box;text-align:center"></div>
      `);
      await page.locator('#subtitle').evaluate((e, t) => e.textContent = t, cue.text);
      const bad = await page.evaluate(([w, h]) => [...document.querySelectorAll('div')].flatMap(e => {
        const r = e.getBoundingClientRect();
        return r.left < 0 || r.right > w || r.top < 0 || r.bottom > h || (e.id === 'subtitle' && r.height > 100) ? [e.id] : [];
      }), [checkWidth, checkHeight]);
      if (bad.length) failures.push({text: cue.text, errors: bad});
    }
    await pw.close();

    layoutResult = {
      passed: !failures.length,
      applies: true,
      checked_cues: props.cues.length,
      method: 'matching text geometry; representative rendered stills require human review',
      failures
    };
  }
  fs.writeFileSync(path.join(dir, 'layout.json'), JSON.stringify(layoutResult, null, 2));
  if (layoutResult.failures.length) throw Error('Text overflow');
}

if (mode === '--prepare') {
  await layoutCheck();
  fs.writeFileSync(path.join(dir, 'plans.json'), JSON.stringify(plans.map(plan => ({
    file: plan.file, fps: FPS, width: plan.props.width, height: plan.props.height,
    durationInFrames: Math.ceil((plan.props.duration || 60) * FPS), props: plan.props
  })), null, 1));
  process.exit(0);
}
if (!['--full', '--parts'].includes(mode)) throw Error('Unknown mode ' + mode);

const url = await bundle({
  entryPoint: fileURLToPath(new URL('./index.tsx', import.meta.url)),
  publicDir
});
const browser = await openBrowser('chrome', {
  browserExecutable: '/usr/bin/google-chrome',
  chromiumOptions: {
    args: ['--enable-gpu', '--ignore-gpu-blocklist', '--no-sandbox']
  }
});

// Same encoder settings for every part and for the legacy single pass.
const encoding = {codec: 'h264', hardwareAcceleration: 'if-possible', pixelFormat: 'yuv420p'};

try {
  if (mode === '--parts') {
    // Each part is frames [from, to) of the full composition: the component
    // reads only the absolute frame, so transitions, Ken Burns motion and
    // subtitles are identical to a single pass. Parts are muted; Python muxes
    // the whole mastered track once after joining.
    const request = JSON.parse(fs.readFileSync(modeArg));
    const results = [];
    const compositions = new Map();
    for (const part of request.parts) {
      const started = Date.now();
      const partial = part.output.replace(/\.mp4$/, '.partial.mp4');
      try {
        const plan = plans[part.plan];
        if (!plan) throw Error('No output plan ' + part.plan);
        if (!compositions.has(part.plan)) {
          compositions.set(part.plan, await selectComposition({serveUrl: url, id: 'Pilot', inputProps: plan.props, puppeteerInstance: browser}));
        }
        const composition = compositions.get(part.plan);
        if (composition.fps !== part.fps || composition.durationInFrames !== part.total) {
          throw Error(`Composition ${composition.durationInFrames} frames @${composition.fps} differs from plan ${part.total} @${part.fps}`);
        }
        await renderMedia({serveUrl: url, composition, inputProps: plan.props, puppeteerInstance: browser, ...encoding,
          muted: true, frameRange: [part.from, part.to - 1], overwrite: true,
          concurrency: props.render_concurrency || 4, outputLocation: partial});
        fs.renameSync(partial, part.output);
        results.push({id: part.id, ok: true, seconds: (Date.now() - started) / 1000});
      } catch (error) {
        fs.rmSync(partial, {force: true});
        results.push({id: part.id, ok: false, error: String(error?.stack || error), seconds: (Date.now() - started) / 1000});
        console.error(`part ${part.id} frames ${part.from}-${part.to - 1} failed:`, error);
      }
      fs.writeFileSync(request.result, JSON.stringify(results, null, 1));
    }
  } else {
    await layoutCheck();
    let first = null;
    for (const plan of plans) {
      const composition = await selectComposition({serveUrl: url, id: 'Pilot', inputProps: plan.props, puppeteerInstance: browser});
      await renderMedia({serveUrl: url, composition, inputProps: plan.props, puppeteerInstance: browser, ...encoding,
        audioCodec: 'aac', concurrency: props.render_concurrency || 4, outputLocation: path.join(dir, plan.file)});
      first ??= composition;
    }
    // Representative stills: the middle frame of each scene, cut from the finished video.
    for (const scene of plans[0].props.scenes) {
      const frame = Math.min(first.durationInFrames - 1, Math.round((scene.start + scene.end) / 2 * first.fps));
      execFileSync('ffmpeg', ['-v', 'error', '-y', '-ss', (frame / first.fps).toFixed(3), '-i', path.join(dir, plans[0].file),
        '-frames:v', '1', path.join(dir, scene.id + '.png')]);
    }
    if (plans[0].file !== 'video.mp4') fs.copyFileSync(path.join(dir, plans[0].file), path.join(dir, 'video.mp4'));
  }
} finally {
  await browser.close({silent: true});
}
