import math
from karaoke_phase0.pitch_scoring import cents_error, score_cents, score_tracks


def test_cents_and_octave():
    assert abs(cents_error(220, 440) - 1200) < 0.001
    assert abs(cents_error(220, 440, True)) < 0.001
    assert cents_error(0, 440) is None


def test_score_curve():
    assert score_cents(30) == 100
    assert score_cents(300) == 0
    assert score_cents(-175) == 50


def test_matching_offset():
    refs = [{'time': 0.0, 'hz': 220, 'periodicity': .9}, {'time': .2, 'hz': 440, 'periodicity': .9}]
    users = [{'time': .1, 'hz': 220, 'periodicity': .9}, {'time': .3, 'hz': 440, 'periodicity': .9}]
    result = score_tracks(refs, users, offset_seconds=-.1)
    assert result['summary']['score'] == 100
    assert result['summary']['counts']['matched'] == 2


def test_missing_and_confidence():
    refs = [{'time': 0, 'hz': 220, 'periodicity': .1}, {'time': .1, 'hz': 220, 'periodicity': .9}]
    users = [{'time': 0, 'hz': 220, 'periodicity': .9}, {'time': .1, 'hz': None}]
    r = score_tracks(refs, users)
    assert r['summary']['score'] is None
    assert r['summary']['counts']['reference_unvoiced'] == 1
    assert r['summary']['counts']['user_unvoiced'] == 1


def test_duplicate_reference_times():
    refs = [{'time': 1, 'hz': 220}, {'time': 1, 'hz': 220}, {'time': 1.02, 'hz': 220}]
    r = score_tracks(refs, [{'time': 1.01, 'hz': 220}])
    assert r['summary']['counts']['matched'] == 1


def test_empty_input():
    assert score_tracks([], [])['summary']['score'] is None
