import pytest
from karaoke_phase0.alignment.context_fallback import diagnose_unanchored


def fixture():
    timeline = {'lines': [{'line_id': i, 'start': float(i * 10), 'end': float(i * 10 + 7)} for i in range(4)]}
    shadow = {'excluded_lines': {'1': 'unknown_or_inexact_tokenization'}, 'groups': [
        {'status': 'candidate_needs_review', 'line_ids': [2, 3], 'lines': [
            {'line_id': 2, 'original_start': 20., 'start_seconds': 18.99, 'end_seconds': 25.},
            {'line_id': 3, 'original_start': 30., 'start_seconds': 29.0}]},
        {'status': 'candidate_needs_review', 'line_ids': [3], 'lines': [
            {'line_id': 3, 'original_start': 30., 'start_seconds': 29.02}]},
    ]}
    return shadow, timeline


def test_all_groups_retained_and_provenance():
    report = diagnose_unanchored(*fixture())
    row = report['lines'][3]
    assert row['observations'] == [29.0, 29.02]
    assert row['group_indices'] == [0, 1]
    assert row['candidate_start'] == 29.01
    assert row['group_evidence'][0]['predecessor_anchored'] is True
    assert row['group_evidence'][1]['predecessor_anchored'] is False
    assert row['auto_adopt'] is False


def test_missing_and_excluded_have_reason():
    report = diagnose_unanchored(*fixture())
    assert report['lines'][1]['status'] == 'excluded_tokenization'
    assert report['lines'][0]['status'] == 'no_candidate'


def test_duplicate_in_group_rejected():
    shadow, timeline = fixture()
    shadow['groups'][0]['lines'].append(dict(shadow['groups'][0]['lines'][1]))
    with pytest.raises(ValueError, match='Duplicate'):
        diagnose_unanchored(shadow, timeline)


def test_stale_shadow_rejected():
    shadow, timeline = fixture()
    shadow['groups'][0]['lines'][0]['original_start'] = 19.
    with pytest.raises(ValueError, match='Stale'):
        diagnose_unanchored(shadow, timeline)


def test_identical_group_times_not_independent_confidence():
    shadow, timeline = fixture()
    shadow['groups'][1]['lines'][0]['start_seconds'] = 29.
    row = diagnose_unanchored(shadow, timeline)['lines'][3]
    assert row['spread_seconds'] == 0
    assert row['auto_adopt'] is False
