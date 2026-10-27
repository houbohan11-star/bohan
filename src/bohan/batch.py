"""Bounded sequential batch execution; one failed job does not stop the rest."""
import json
from pathlib import Path
from .contracts import write_json
from .pipeline import run
from .prompts import load_product


def run_batch(path: Path, out: Path):
    jobs = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("Batch must be a nonempty JSON array")
    ids = []
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("Each batch job must be an object")
        job_id = job.get("id", "")
        if (not isinstance(job_id, str) or not job_id or job_id in {".", ".."}
                or not all(c.isascii() and (c.isalnum() or c in "-_") for c in job_id)):
            raise ValueError("Job id must use ASCII letters, digits, '-' or '_'")
        if not isinstance(job.get("source"), str) or not job["source"]:
            raise ValueError("Each job requires source")
        ids.append(job_id)
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate batch job ids")
    out.mkdir(parents=True, exist_ok=False)
    results = []
    for job in jobs:
        try:
            source = (path.parent / job["source"]).resolve()
            product = load_product(path.parent / job["product"]) if job.get("product") else None
            result = run(source, out / job["id"], job.get("interval", 2.0), product,
                         language=job.get("language"))
            results.append({"id": job["id"], "status": result["status"]})
        except Exception as exc:
            results.append({"id": job["id"], "status": "failed", "error": str(exc)})
        write_json(out / "batch.json", results)
    return results
