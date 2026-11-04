import importlib.util
from pathlib import Path
import numpy as np

p = Path(__file__).resolve().parents[1] / 'tools' / 'diagnose_ctc_acoustic_onset_v7.py'
spec = importlib.util.spec_from_file_location('ctc_onset_v7', p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_features_silence():
    t, rms, flux = mod.features(np.zeros(16000), 16000)
    assert len(t) == len(rms) == len(flux)
    assert not rms.any() and not flux.any()


def test_candidate_respects_previous_end():
    times = np.arange(0, 5, 0.01)
    rms = np.full(len(times), .5)
    flux = np.zeros(len(times))
    flux[210] = 1.0
    flux[280] = .9
    candidates = mod.onset_candidates(times, rms, flux, peak=3.0, previous_end=2.5)
    assert candidates and all(x['time_seconds'] >= 2.5 for x in candidates)


def test_missing_peak_does_not_invent_onset():
    rows = [{'line_id': 2, 'token_peak_median': None, 'observations': []}]
    assert mod.analyze(np.zeros(16000), 16000, rows)[0]['candidate_onsets'] == []


def test_ambiguous_peaks_remain_candidates():
    times = np.arange(0, 5, .01)
    rms = np.ones(len(times))
    flux = np.zeros(len(times))
    flux[250] = 1
    flux[280] = .8
    out = mod.onset_candidates(times, rms, flux, peak=3.0)
    assert len(out) >= 2
