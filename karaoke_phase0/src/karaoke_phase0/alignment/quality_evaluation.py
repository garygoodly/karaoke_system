"""Read-only alignment quality metrics and regression evaluation.

All timestamps in seconds. Token peaks are not validated acoustic onsets.
No heuristic threshold is claimed to be a calibrated confidence probability.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean, median


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_ground_truth(path):
    """Accept CSV with line_id and one of the documented time column names."""
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "line_id" not in reader.fieldnames:
            raise ValueError("Ground truth CSV requires line_id column")
        possible = ("onset_seconds", "start_seconds", "manual_start_seconds", "time_seconds", "onset_s", "manual_onset_seconds")
        column = next((x for x in possible if x in reader.fieldnames), None)
        if column is None:
            raise ValueError("Unknown ground truth time column; supported: " + ", ".join(possible))
        out = {}
        for row in reader:
            if not row["line_id"].strip() or not (row.get(column) or "").strip():
                continue
            key, value = int(row["line_id"]), float(row[column])
            if key in out:
                raise ValueError(f"Duplicate ground truth line_id: {key}")
            out[key] = value
    return out


def evaluate(v4, v6, truth=None, *, tolerance=0.5):
    """Merge full-song v4 coverage with optional v6 boundary refinements.

    A missing v6 row means *not evaluated by v6*, not missing CTC inference.
    """
    if tolerance < 0:
        raise ValueError("tolerance must be nonnegative")
    truth = truth or {}
    baseline = {int(x["line_id"]): x for x in v4.get("consensus", [])}
    constrained = {int(x["line_id"]): x for x in v6.get("lines", [])}
    rows = []
    for i in sorted(set(baseline) | set(constrained) | set(truth)):
        a, b = baseline.get(i, {}), constrained.get(i, {})
        original = a.get("original_start", b.get("original_start"))
        v4_peak = a.get("median_start")
        v4_count = int(a.get("observation_count") or 0)
        v4_spread = a.get("spread_seconds")
        v6_peak = b.get("token_peak_median")
        v6_count = int(b.get("anchored_count") or 0)
        v6_spread = b.get("token_peak_spread_seconds")
        # Prefer a usable v6 refinement; otherwise fall back to the full-song v4.
        if v6_peak is not None and v6_count:
            peak, count, spread, source = v6_peak, v6_count, v6_spread, "v6"
        elif v4_peak is not None and v4_count:
            peak, count, spread, source = v4_peak, v4_count, v4_spread, "v4"
        else:
            peak, count, spread, source = None, 0, None, None
        if source is None:
            status = "missing_prediction" if i in baseline or i in constrained else "not_evaluated"
        elif count < 2:
            status = "single_observation"
        elif spread is None:
            status = "unknown_consistency"
        elif spread > tolerance:
            status = "disagreement"
        else:
            status = "consistent_candidate"
        actual = truth.get(i)
        rows.append({
            "line_id": i, "original_start": original,
            "ctc_token_peak": peak, "candidate_source": source,
            "v6_evaluated": i in constrained,
            "anchored_count": count, "spread_seconds": spread,
            "status": status, "ground_truth_start": actual,
            "original_absolute_error": abs(float(original)-actual) if actual is not None and original is not None else None,
            "ctc_absolute_error": abs(float(peak)-actual) if actual is not None and peak is not None else None,
        })
    def mae(key):
        values = [r[key] for r in rows if r[key] is not None]
        return round(mean(values), 4) if values else None
    return {
        "status": "diagnostic_only", "method": "ctc_quality_evaluation_v2",
        "warning": "MAE uses labeled rows only; CTC token peaks are not verified acoustic onsets. No timeline modified.",
        "summary": {
            "lines": len(rows), "labeled_lines": len(truth),
            "original_mae_seconds": mae("original_absolute_error"),
            "ctc_mae_seconds": mae("ctc_absolute_error"),
            "not_evaluated_count": sum(r["status"] == "not_evaluated" for r in rows),
            "missing_prediction_count": sum(r["status"] == "missing_prediction" for r in rows),
            "disagreement_count": sum(r["status"] == "disagreement" for r in rows),
            "v4_prediction_count": sum(x.get("median_start") is not None and int(x.get("observation_count") or 0) > 0 for x in baseline.values()),
            "v6_refinement_count": sum(r["candidate_source"] == "v6" for r in rows),
        }, "lines": rows,
    }
