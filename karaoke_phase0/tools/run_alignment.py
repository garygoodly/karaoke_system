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
    adoption = sub.add_parser("adoption", help="Create read-only CTC candidate timeline from existing quality report")
    adoption.add_argument("--timeline", required=True)
    adoption.add_argument("--quality", required=True)
    adoption.add_argument("--output", required=True)
    adoption.add_argument("--max-spread", type=float, default=0.10)
    adoption.add_argument("--min-shift", type=float, default=1.0)
    adoption.add_argument("--max-shift", type=float, default=4.0)
    playable = sub.add_parser("playable-preview", help="Create an isolated, uniformly shifted line/token preview")
    playable.add_argument("--timeline", required=True)
    playable.add_argument("--candidate", required=True)
    playable.add_argument("--output", required=True)
    playable.add_argument("--max-shift", type=float, default=4.0)
    word = sub.add_parser("word-preview", help="Reconstruct character intervals from Joint CTC anchors")
    word.add_argument("--timeline", required=True)
    word.add_argument("--hybrid", required=True)
    word.add_argument("--shadow", required=True)
    word.add_argument("--audio", help="Optional separated vocals.wav for conservative final-token offset cues")
    word.add_argument("--output", required=True)
    word_quality = sub.add_parser("word-quality", help="Read-only structural quality report for CTC word preview")
    word_quality.add_argument("--timeline", required=True)
    word_quality.add_argument("--word-preview", required=True)
    word_quality.add_argument("--output", required=True)
    word_quality.add_argument("--min-duration", type=float, default=0.035)
    word_quality.add_argument("--max-duration", type=float, default=3.0)
    word_quality.add_argument("--max-overlap", type=float, default=0.10)
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
    if args.command == "adoption":
        if remainder:
            p.error("Unrecognized arguments: " + " ".join(remainder))
        from karaoke_phase0.alignment.controlled_adoption import propose
        from karaoke_phase0.alignment.quality_evaluation import load_json
        timeline_path = Path(args.timeline).resolve()
        output_path = Path(args.output).resolve()
        if output_path == timeline_path or output_path.name == "lyrics_timeline.json":
            p.error("Refusing to overwrite the authoritative lyrics_timeline.json")
        result = propose(load_json(timeline_path), load_json(args.quality),
                         max_spread=args.max_spread, min_shift=args.min_shift,
                         max_shift=args.max_shift)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result["ctc_candidate_metadata"], indent=2))
        print("Report:", output_path)
        return 0
    if args.command == "playable-preview":
        if remainder:
            p.error("Unrecognized arguments: " + " ".join(remainder))
        from karaoke_phase0.alignment.playable_timeline import build_preview
        from karaoke_phase0.alignment.quality_evaluation import load_json
        timeline_path = Path(args.timeline).resolve()
        candidate_path = Path(args.candidate).resolve()
        output_path = Path(args.output).resolve()
        if output_path in (timeline_path, candidate_path) or output_path.name == "lyrics_timeline.json":
            p.error("Refusing to overwrite original timeline or candidate")
        result = build_preview(load_json(timeline_path), load_json(candidate_path), max_shift=args.max_shift)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result["ctc_preview_metadata"], ensure_ascii=False, indent=2))
        print("Preview:", output_path)
        return 0
    if args.command == "word-preview":
        if remainder:
            p.error("Unrecognized arguments: " + " ".join(remainder))
        from karaoke_phase0.alignment.word_preview import build_word_preview
        source = Path(args.timeline).resolve()
        hybrid = Path(args.hybrid).resolve()
        shadow = Path(args.shadow).resolve()
        dest = Path(args.output).resolve()
        if dest in (source, hybrid, shadow) or dest.name == "lyrics_timeline.json":
            p.error("Refusing to overwrite input or authoritative timeline")
        result = build_word_preview(json.loads(source.read_text(encoding="utf-8")),
                                    json.loads(hybrid.read_text(encoding="utf-8")),
                                    json.loads(shadow.read_text(encoding="utf-8")), audio_path=args.audio)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result["ctc_word_preview_metadata"], ensure_ascii=False, indent=2))
        print("Preview:", dest)
        return 0
    if args.command == "word-quality":
        if remainder:
            p.error("Unrecognized arguments: " + " ".join(remainder))
        from karaoke_phase0.alignment.word_quality import evaluate_word_preview
        source = Path(args.timeline).resolve()
        preview = Path(args.word_preview).resolve()
        dest = Path(args.output).resolve()
        if dest in (source, preview) or dest.name == "lyrics_timeline.json":
            p.error("Refusing to overwrite source or preview timeline")
        result = evaluate_word_preview(json.loads(source.read_text(encoding="utf-8")),
                                       json.loads(preview.read_text(encoding="utf-8")),
                                       min_duration=args.min_duration,
                                       max_duration=args.max_duration,
                                       max_overlap=args.max_overlap)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result["summary"], indent=2))
        print("Report:", dest)
        return 0
    script = Path(__file__).with_name(legacy[args.command])
    if not script.is_file():
        p.error(f"Required existing script not installed: {script.name}")
    return subprocess.call([sys.executable, str(script), *remainder])


if __name__ == "__main__":
    raise SystemExit(main())
