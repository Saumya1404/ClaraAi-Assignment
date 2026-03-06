import argparse
import sys
from pathlib import Path

from faster_whisper import WhisperModel

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".webm", ".mp4"}

DEFAULT_DIRS = [
    "inputs/demo_calls",
    "inputs/onboarding_calls",
]


def transcribe_file(model: WhisperModel, audio_path: Path) -> str:
    segments, info = model.transcribe(
        str(audio_path),
        beam_size=5,
        language="en",
        vad_filter=True,
    )
    print(f"  Detected language: {info.language} (prob {info.language_probability:.2f})")

    lines = []
    for segment in segments:
        lines.append(segment.text.strip())
    return "\n".join(lines)


def process_path(model: WhisperModel, target: Path, overwrite: bool = False) -> int:
    count = 0

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(
            f for f in target.iterdir()
            if f.suffix.lower() in AUDIO_EXTENSIONS
        )
        if not files:
            print(f"  No audio files found in {target}")
            return 0
    else:
        print(f"  Path not found: {target}")
        return 0

    for audio_file in files:
        output_file = audio_file.with_suffix(".txt")

        if output_file.exists() and not overwrite:
            print(f"  Skipping {audio_file.name} (transcript exists, use --overwrite)")
            continue

        print(f"  Transcribing {audio_file.name}...")
        text = transcribe_file(model, audio_file)
        output_file.write_text(text, encoding="utf-8")
        print(f"  -> Saved {output_file.name} ({len(text)} chars)")
        count += 1

    return count


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio files using faster-whisper (local, zero-cost)"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to transcribe (default: inputs/demo_calls, inputs/onboarding_calls)",
    )
    parser.add_argument(
        "--model",
        default="base",
        choices=["tiny", "base", "small", "medium", "large-v3"],
        help="Whisper model size (default: base). Larger = more accurate but slower.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing .txt transcripts",
    )
    args = parser.parse_args()

    targets = [Path(p) for p in args.paths] if args.paths else [Path(d) for d in DEFAULT_DIRS]

    print(f"Loading whisper model '{args.model}' (first run downloads ~150MB)...")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    print("Model loaded.\n")

    total = 0
    for target in targets:
        print(f"Processing: {target}")
        total += process_path(model, target, overwrite=args.overwrite)

    print(f"\nDone. Transcribed {total} file(s).")


if __name__ == "__main__":
    main()