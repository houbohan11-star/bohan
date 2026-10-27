"""Local file ingestion and FFmpeg extraction; no network calls."""
import json
import math
import shutil
import subprocess
from pathlib import Path
from .contracts import write_json


def doctor():
    return {name: shutil.which(name) is not None for name in ("ffmpeg", "ffprobe")}


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=300, check=False)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr[-2000:]}")
    return result.stdout


def extract(source: Path, out: Path, interval: float):
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("Frame interval must be finite and positive")
    source = source.resolve(strict=True)
    if not source.is_file():
        raise ValueError("Source must be a local file")
    if not all(doctor().values()):
        raise RuntimeError("Install FFmpeg and ffprobe first; run bohan doctor")
    metadata = json.loads(command(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                                   "-of", "json", str(source)]))
    streams = metadata.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise ValueError("No video stream found")
    duration = float(metadata["format"]["duration"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Video duration must be finite and positive")
    # Individual timestamp requests make the sampling intent explicit, including t=0.
    # This is sparse sampling, not scene detection or frame-by-frame analysis.
    count = math.ceil(duration / interval)
    if count > 1000:
        raise ValueError("More than 1000 frames requested; increase --interval")
    frame_dir = out / "frames"
    frame_dir.mkdir()
    frames = []
    for index in range(count):
        timestamp = index * interval
        relative = f"frames/{index:06d}.jpg"
        command(["ffmpeg", "-nostdin", "-v", "error", "-ss", str(timestamp), "-i", str(source),
                 "-map", f"0:{video['index']}", "-frames:v", "1", "-q:v", "2", str(out / relative)])
        if not (out / relative).is_file():
            raise RuntimeError(f"No frame produced at {timestamp}")
        frames.append({"timestamp": timestamp, "path": relative})
    audio = None
    if any(s.get("codec_type") == "audio" for s in streams):
        audio = "audio.wav"
        command(["ffmpeg", "-nostdin", "-v", "error", "-i", str(source), "-map", "0:a:0",
                 "-vn", "-ac", "1", "-ar", "16000", str(out / audio)])
    write_json(out / "metadata.json", metadata)
    write_json(out / "frames.json", frames)
    return {"duration": duration, "frames": frames, "audio": audio}
