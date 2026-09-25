"""Independent Piper CPU auditions from the same approved text."""

import json
import sys
import time
import wave
from pathlib import Path

import soundfile as sf
from piper.voice import PiperVoice

OUT = Path(__file__).resolve().parent
MODELS = OUT.parents[1] / "scratch/voice-audition-piper/models/vi/vi_VN"
PASSAGES = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))["passages"]


def main():
    gpu = "--gpu" in sys.argv
    if gpu:
        import torch  # loads CUDA libraries needed by ONNX Runtime CUDA EP
    suffix = "-gpu" if gpu else ""
    rows = []
    for model in sorted(MODELS.rglob("*.onnx")):
        voice_id = model.stem.removeprefix("vi_VN-")
        tts = PiperVoice.load(model, use_cuda=gpu)
        active = tts.session.get_providers()
        if gpu and "CUDAExecutionProvider" not in active:
            raise RuntimeError("CUDA provider unavailable; refusing a mislabeled GPU sample")
        for kind, passage in PASSAGES.items():
            filename = f"piper{suffix}-{voice_id}-{kind}.wav"
            target = OUT / filename
            start = time.monotonic()
            try:
                if not target.exists():
                    with wave.open(str(target), "wb") as f:
                        tts.synthesize_wav(passage, f)
                with sf.SoundFile(target) as f:
                    seconds = round(len(f) / f.samplerate, 2)
                rows.append({"voice": voice_id, "label": voice_id,
                             "passage": kind, "file": filename,
                             "duration_seconds": seconds,
                             "elapsed_seconds": round(time.monotonic() - start, 2),
                             "status": "ok"})
                print(f"Piper {voice_id} {kind}: {seconds}s audio", flush=True)
            except Exception as exc:
                rows.append({"voice": voice_id, "label": voice_id,
                             "passage": kind, "file": filename,
                             "status": "error", "error": str(exc)})
                print(f"ERROR Piper {voice_id} {kind}: {exc}", flush=True)
            (OUT / f"piper{suffix}-manifest.json").write_text(
                json.dumps({"model": "Piper", "backend": "ONNX CUDA" if gpu else "ONNX CPU",
                            "active_providers": active,
                            "samples": rows}, ensure_ascii=False, indent=2),
                encoding="utf-8")


if __name__ == "__main__":
    main()
