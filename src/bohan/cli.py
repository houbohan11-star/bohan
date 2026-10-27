import argparse
import json
import sys
import subprocess
from pathlib import Path
from .media import doctor
from .pipeline import run
from .batch import run_batch
from .prompts import load_product


def main(argv=None):
    parser = argparse.ArgumentParser(prog="bohan")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check FFmpeg binaries; does not install/download models")
    one = sub.add_parser("run", help="Process a local video into a new output directory")
    one.add_argument("source", type=Path)
    one.add_argument("--out", type=Path, required=True)
    one.add_argument("--interval", type=float, default=2.0, help="Sparse sample interval in seconds")
    one.add_argument("--language", default=None)
    one.add_argument("--product", type=Path)
    batch = sub.add_parser("batch", help="Run local jobs sequentially from JSON")
    batch.add_argument("jobs", type=Path)
    batch.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor()
            print(json.dumps(result))
            return 0 if all(result.values()) else 1
        if args.command == "batch":
            result = run_batch(args.jobs.resolve(), args.out)
            print(json.dumps(result, ensure_ascii=False))
            return 1 if any(j["status"] == "failed" for j in result) else 0
        product = load_product(args.product) if args.product else None
        result = run(args.source, args.out, args.interval, product, language=args.language)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        print(f"bohan: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
