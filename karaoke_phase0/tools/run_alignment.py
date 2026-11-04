"""One entry point for existing CTC experiments and automated report evaluation.

Legacy tools are retained for reproducibility. GPU modes forward to those scripts;
quality mode uses a shared library and requires no model or GPU.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    quality = sub.add_parser("quality", help="Evaluate existing v4/v6 JSON against optional ground truth CSV")
    quality.add_argument("--v4", required=True)
    quality.add_argument("--v6", required=True)
    quality.add_argument("--ground-truth")
    quality.add_argument("--output", required=True)
    quality.add_argument("--tolerance", type=float, default=0.5)
    legacy = {
        "sliding": "benchmark_ctc_sliding_v4.py",
        "boundary": "diagnose_ctc_boundary_aware_v6.py",
        "onset": "diagnose_ctc_acoustic_onset_v7.py",
    }
    for name in legacy:
        sub.add_parser(name, help=f"Run existing {name} workflow with its original arguments", add_help=False)
    # Pass-through preserves the tested legacy script argument contracts.
    args, remainder = p.parse_known_args(argv)
    if args.command == "quality":
        if remainder:
            p.error("Unrecognized arguments: " + " ".join(remainder))
        from karaoke_phase0.alignment.quality_evaluation import evaluate, load_json, load_ground_truth
        gt = load_ground_truth(args.ground_truth) if args.ground_truth else {}
        result = evaluate(load_json(args.v4), load_json(args.v6), gt, tolerance=args.tolerance)
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result["summary"], indent=2))
        print("Report:", out)
        return 0
    script = Path(__file__).with_name(legacy[args.command])
    if not script.is_file():
        p.error(f"Required existing script not installed: {script.name}")
    return subprocess.call([sys.executable, str(script), *remainder])


if __name__ == "__main__":
    raise SystemExit(main())
