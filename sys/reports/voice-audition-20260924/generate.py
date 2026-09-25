"""Generate independent voice auditions from an existing approved story.

This does not touch Pilot jobs, revisions, or review decisions.
"""

import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
STORY = ROOT / "runs/thu-5p-h007g/revisions/content/1/content.json"
SCENES = json.loads(STORY.read_text(encoding="utf-8"))["scenes"]
PASSAGES = {
    "tu_su": SCENES[1]["narration"].split(" Căn gác", 1)[0],
    "hoi_hop": SCENES[4]["narration"].split(" Khi tôi khẽ", 1)[0],
}
assert all(len(t) <= 256 for t in PASSAGES.values())


def save_manifest(rows, info):
    (OUT / "manifest.json").write_text(
        json.dumps({"source": str(STORY), "passages": PASSAGES,
                    "engine": info, "samples": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main():
    from vieneu import Vieneu
    mode = sys.argv[1] if len(sys.argv) > 1 else "gpu"
    if mode == "gpu":
        tts = Vieneu(mode="v3turbo", backend="pytorch", device="cuda",
                     dtype="float32", max_batch_size=1)
        info = {"model": "VieNeu v3 Turbo", "backend": "PyTorch CUDA FP32",
                "style": "Style cố định theo giọng mẫu; style= bị bỏ qua trong vieneu 3.8.1"}
    else:
        tts = Vieneu(mode="v3turbo", backend="onnx", precision="fp32")
        info = {"model": "VieNeu v3 Turbo", "backend": "ONNX CPU FP32",
                "style": "Style cố định theo giọng mẫu; style= bị bỏ qua trong vieneu 3.8.1"}
    rows = []
    for i, (label, voice) in enumerate(tts.list_preset_voices(), 1):
        for kind, passage in PASSAGES.items():
            name = f"{i:02d}-{kind}.wav"
            dest = OUT / name
            started = time.monotonic()
            try:
                if not dest.exists():
                    audio = tts.infer(passage, voice=voice)
                    audio = np.asarray(audio, dtype=np.float32).reshape(-1)
                    if len(audio) < tts.sample_rate or not np.isfinite(audio).all():
                        raise RuntimeError("Audio empty or invalid")
                    sf.write(dest, audio, tts.sample_rate, subtype="PCM_16")
                with sf.SoundFile(dest) as f:
                    seconds = round(len(f) / f.samplerate, 2)
                rows.append({"number": i, "voice": voice, "label": label,
                             "passage": kind, "file": name,
                             "duration_seconds": seconds,
                             "elapsed_seconds": round(time.monotonic() - started, 2),
                             "status": "ok"})
                print(f"{i:02d}/25 {voice} {kind}: {seconds}s audio", flush=True)
            except Exception as exc:
                rows.append({"number": i, "voice": voice, "label": label,
                             "passage": kind, "file": name, "status": "error",
                             "error": str(exc)})
                print(f"ERROR {i:02d} {voice} {kind}: {exc}", flush=True)
            save_manifest(rows, info)


if __name__ == "__main__":
    main()
