import csv
import json
import tempfile
from pathlib import Path
import pytest
from karaoke_phase0.alignment.quality_evaluation import evaluate, load_ground_truth


def sample():
    return ({"consensus": [{"line_id": 2, "original_start": 41.5, "median_start": 39.01, "observation_count": 3, "spread_seconds": .03}, {"line_id": 5, "original_start": 67.5, "median_start": 64.93, "observation_count": 3, "spread_seconds": .02}, {"line_id": 24, "original_start": 229.5, "median_start": 229.112, "observation_count": 3, "spread_seconds": 1.126}]},
            {"lines": [{"line_id": 2, "token_peak_median": 39.008, "anchored_count": 2, "token_peak_spread_seconds": .003},
                       {"line_id": 5, "token_peak_median": 64.939, "anchored_count": 2, "token_peak_spread_seconds": .017},
                       {"line_id": 24, "token_peak_median": 229.31, "anchored_count": 2, "token_peak_spread_seconds": .396}]})


def test_regression_three_lines():
    a, b = sample()
    r = evaluate(a, b, {2: 39.39, 5: 65.3, 24: 229.728})
    assert r["summary"]["labeled_lines"] == 3
    assert r["summary"]["original_mae_seconds"] == pytest.approx(1.5127, abs=.0001)
    assert r["summary"]["ctc_mae_seconds"] == pytest.approx(.387, abs=.0001)
    assert r["summary"]["disagreement_count"] == 0


def test_missing_and_single_observation():
    a, b = sample()
    b["lines"][0]["anchored_count"] = 1
    b["lines"][1]["token_peak_median"] = None
    r = evaluate(a, b)
    assert r["lines"][0]["status"] == "single_observation"
    assert r["lines"][1]["candidate_source"] == "v4"


def test_spread_disagreement():
    a, b = sample()
    b["lines"][2]["token_peak_spread_seconds"] = 1.126
    assert evaluate(a, b)["lines"][2]["status"] == "disagreement"


def test_ground_truth_csv():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "truth.csv"
        p.write_text("line_id,start_seconds\\n2,39.39\\n5,65.3\\n".replace('\\n','\n'), encoding="utf-8")
        assert load_ground_truth(p) == {2:39.39, 5:65.3}


def test_reject_bad_csv():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "bad.csv"
        p.write_text("line_id,unknown\n2,39\n", encoding="utf-8")
        with pytest.raises(ValueError): load_ground_truth(p)


def test_v4_fallback_and_true_missing():
    a, b = sample()
    a["consensus"].append({"line_id": 9, "original_start": 96.5, "median_start": 96.987, "observation_count": 3, "spread_seconds": .02})
    a["consensus"].append({"line_id": 10, "original_start": 103.5, "median_start": None, "observation_count": 0})
    r = evaluate(a, b)
    by_id = {x["line_id"]: x for x in r["lines"]}
    assert by_id[9]["candidate_source"] == "v4"
    assert by_id[10]["status"] == "missing_prediction"
    assert r["summary"]["missing_prediction_count"] == 1
    assert r["summary"]["disagreement_count"] == 0

def test_unobserved_ground_truth_not_model_failure():
    r = evaluate({"consensus": []}, {"lines": []}, {99: 5.0})
    assert r["summary"]["not_evaluated_count"] == 1
    assert r["summary"]["missing_prediction_count"] == 0
