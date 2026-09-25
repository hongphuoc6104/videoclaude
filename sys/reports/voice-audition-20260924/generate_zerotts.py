"""Independent ZeroTTS CPU auditions using the same approved story excerpts."""

import json
import sys
import time
from pathlib import Path

import soundfile as sf
from zerotts import ZeroTTS

OUT = Path(__file__).resolve().parent
PASSAGES = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))["passages"]


def main():
    gpu = "--gpu" in sys.argv
    if gpu:
        import torch  # loads CUDA libraries needed by ONNX Runtime CUDA EP
    providers = (["CUDAExecutionProvider", "CPUExecutionProvider"] if gpu
                 else ["CPUExecutionProvider"])
    tts = ZeroTTS.from_pretrained("zeroweight-ai/ZeroTTS", providers=providers)
    active = tts.prefix_step_sess.get_providers()
    if gpu and "CUDAExecutionProvider" not in active:
        raise RuntimeError("CUDA provider unavailable; refusing a mislabeled GPU sample")
    suffix = "-gpu" if gpu else ""
    rows = []
    for voice in tts.list_voices():
        info = tts.load_voice(voice)
        label = getattr(info, "display_name", voice)
        for kind, passage in PASSAGES.items():
            filename = f"zerotts{suffix}-{voice}-{kind}.wav"
            target = OUT / filename
            start = time.monotonic()
            try:
                if not target.exists():
                    audio = tts.synthesize(passage, voice=voice)
                    tts.save_audio(audio, str(target))
                with sf.SoundFile(target) as f:
                    seconds = round(len(f) / f.samplerate, 2)
                rows.append({"voice": voice, "label": label, "passage": kind,
                             "file": filename, "duration_seconds": seconds,
                             "elapsed_seconds": round(time.monotonic() - start, 2),
                             "status": "ok"})
                print(f"ZeroTTS {voice} {kind}: {seconds}s audio", flush=True)
            except Exception as exc:
                rows.append({"voice": voice, "label": label, "passage": kind,
                             "file": filename, "status": "error", "error": str(exc)})
                print(f"ERROR ZeroTTS {voice} {kind}: {exc}", flush=True)
            (OUT / f"zerotts{suffix}-manifest.json").write_text(
                json.dumps({"model": "ZeroTTS", "backend": "ONNX CUDA FP32" if gpu else "ONNX CPU FP32",
                            "active_providers": active,
                            "samples": rows}, ensure_ascii=False, indent=2),
                encoding="utf-8")


if __name__ == "__main__":
    main()
