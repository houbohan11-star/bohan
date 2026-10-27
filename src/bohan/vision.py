"""Qwen3-VL adapter boundary. Every observation must cite extracted frames."""
from pathlib import Path
from .contracts import VisionAnalyzer, validate_vision, write_json


def run(frames: list[dict], out: Path, duration: float, backend: VisionAnalyzer | None = None):
    value = ({"status": "pending", "reason": "vision_analyzer_not_configured", "observations": []}
             if backend is None else validate_vision(backend.analyze(frames, out), duration, frames))
    write_json(out / "vision.json", value)
    return value
