"""Stable adapter boundaries. Time values are seconds, never frame indices."""
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Protocol
import json

SCHEMA_VERSION = 1

@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str

@dataclass
class Transcript:
    language: str
    segments: list[TranscriptSegment]
    status: str = "needs_review"
    timing: str = "asr_estimate"  # Not forced alignment.

@dataclass
class Observation:
    start: float
    end: float
    observation: str
    evidence: list[str] = field(default_factory=list)

@dataclass
class VisionAnalysis:
    observations: list[Observation]
    status: str = "needs_review"

class Transcriber(Protocol):
    def transcribe(self, audio: Path, language: str | None) -> Transcript: ...

class VisionAnalyzer(Protocol):
    def analyze(self, frames: list[dict], job_dir: Path) -> VisionAnalysis: ...


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_interval(start, end, duration):
    import math
    if (isinstance(start, bool) or isinstance(end, bool)
            or not isinstance(start, (int, float)) or not isinstance(end, (int, float))
            or not math.isfinite(start) or not math.isfinite(end)
            or not 0 <= start < end <= duration + 0.05):
        raise ValueError("Invalid observation/segment time interval")


def validate_transcript(value: Transcript, duration: float):
    if not value.language or value.status not in {"needs_review", "reviewed"}:
        raise ValueError("Transcript language/status is invalid")
    if value.timing != "asr_estimate":
        raise ValueError("Forced alignment is not implemented in v0.1")
    for s in value.segments:
        check_interval(s.start, s.end, duration)
        if not s.text.strip():
            raise ValueError("Transcript segment is empty")
    return asdict(value)


def validate_vision(value: VisionAnalysis, duration: float, frames: list[dict]):
    known = {f["path"] for f in frames}
    if value.status not in {"needs_review", "reviewed"}:
        raise ValueError("Vision status is invalid")
    for item in value.observations:
        check_interval(item.start, item.end, duration)
        if not item.observation.strip() or not item.evidence or not set(item.evidence) <= known:
            raise ValueError("Vision observations require extracted frame references")
    return asdict(value)
