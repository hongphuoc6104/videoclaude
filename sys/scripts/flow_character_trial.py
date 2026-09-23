#!/usr/bin/env python3
"""Two real Flow generations that prove a story character is drawn from its own reference.

1. A text-only character reference (no character attached; the tool must accept it).
2. A scene attaching that reference by its Flow media id (not the mascot).

Spends two image generations, so it refuses to run without --confirm-cost.
Needs a connected B-2 session (session.mjs serve + connect) on the Flow profile.
Results and a report go to experiments/b2_illustrator/results/character-trial/<time>/.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import b2_bridge  # noqa: E402

STYLE = ('Dark 2D horror illustration, comic-book inking with cold desaturated palette, deep shadows and a single warm '
         'light source, no gore, no blood, no text')
PERSON = ('a Vietnamese woman in her late twenties, oval face, straight black hair in a low ponytail, thin silver '
          'earrings, slim build; faded olive-green cardigan over a cream blouse, dark trousers')
REFERENCE = f'{STYLE}. One full-body character on a plain dark grey background, face and clothes clearly lit: {PERSON}.'
SCENE = (f'{STYLE}. The same woman stands in a narrow rented room at night holding an oil lamp, looking at a mirror '
         'that hangs face-to-the-wall; her shadow on the wall is slightly wrong. Camera at chest height, medium shot.')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--confirm-cost', action='store_true', help='I accept two Flow image generations')
    ap.add_argument('--ratio', choices=['9:16', '16:9'], default='9:16')
    a = ap.parse_args()
    if not a.confirm_cost:
        raise SystemExit('Refused: this spends two Flow generations. Re-run with --confirm-cost.')
    out = ROOT / 'experiments/b2_illustrator/results/character-trial' / time.strftime('%Y%m%d-%H%M%S')
    out.mkdir(parents=True)
    report = {'ratio': a.ratio, 'steps': []}
    try:
        ref = b2_bridge.generate_b2_image(REFERENCE, a.ratio, no_character=True, out_dir=out / 'reference',
                                          test_case='trial-ref-' + out.name, timeout=240)
        report['steps'].append({'step': 'text-only reference', 'path': ref['path'], 'media_id': ref['media_id']})
        scene = b2_bridge.generate_b2_image(SCENE, a.ratio, char_ref_path=ref['path'], char_media_id=ref['media_id'],
                                            out_dir=out / 'scene', test_case='trial-scene-' + out.name, timeout=240)
        report['steps'].append({'step': 'scene with story reference', 'path': scene['path'], 'media_id': scene['media_id'],
                                'attached_reference_media_id': ref['media_id']})
        report['ok'] = True
    except Exception as ex:
        report.update(ok=False, error=str(ex))
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report['ok'] else 2)


if __name__ == '__main__':
    main()
