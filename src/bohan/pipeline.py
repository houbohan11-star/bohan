"""Sequential stages, explicit states, and isolated output per job."""
from datetime import datetime, timezone
from pathlib import Path
from .contracts import SCHEMA_VERSION, write_json
from .media import extract
from . import transcription, vision, prompts


def run(source: Path, out: Path, interval=2.0, product=None, transcriber=None,
        vision_analyzer=None, language=None):
    # Refuse existing job directories rather than overwrite evidence or mix products.
    out.mkdir(parents=True, exist_ok=False)
    manifest = {"schema_version": SCHEMA_VERSION, "source": str(source.resolve()),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "parameters": {"interval_seconds": interval, "language": language},
                "status": "running", "stages": {}}
    manifest_path = out / "manifest.json"
    write_json(manifest_path, manifest)
    stage = "extraction"
    try:
        media = extract(source, out, interval)
        manifest["stages"][stage] = "completed"
        write_json(manifest_path, manifest)
        stage = "transcription"
        transcript = transcription.run(out / media["audio"] if media["audio"] else None,
                                       out, media["duration"], transcriber, language)
        manifest["stages"][stage] = transcript["status"]
        stage = "vision"
        analysis = vision.run(media["frames"], out, media["duration"], vision_analyzer)
        manifest["stages"][stage] = analysis["status"]
        stage = "prompt"
        manifest["stages"][stage] = prompts.render(product, out)
        manifest["status"] = "needs_review"
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["stages"][stage] = "failed"
        manifest["error"] = {"stage": stage, "type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        write_json(manifest_path, manifest)
    return manifest
