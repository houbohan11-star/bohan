"""Whisper/faster-whisper adapter boundary; weights are not bundled."""
from pathlib import Path
from .contracts import Transcriber, validate_transcript, write_json


def run(audio: Path | None, out: Path, duration: float,
        backend: Transcriber | None = None, language: str | None = None):
    if audio is None:
        value = {"status": "skipped", "reason": "no_audio_stream", "segments": []}
    elif backend is None:
        value = {"status": "pending", "reason": "transcriber_not_configured", "segments": []}
    else:
        value = validate_transcript(backend.transcribe(audio, language), duration)
    write_json(out / "transcript.json", value)
    return value
