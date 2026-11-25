import json
from pathlib import Path
from unittest.mock import patch
from karaoke_phase0.alignment.hybrid_pipeline import _build_word_preview_and_quality, build_hybrid_from_song


def _sample():
    line = {'line_id': 0, 'text': '甲', 'start': 10.0, 'end': 11.0,
            'tokens': [{'text': '甲', 'start': 10.0, 'end': 11.0}]}
    original = {'lines': [line]}
    hybrid = {'lines': [line], 'hybrid_metadata': {'selected_lines': []}}
    return original, hybrid


def test_auto_word_stage_produces_both_files_without_changing_source(tmp_path):
    original, hybrid = _sample()
    before = json.dumps(original)
    result = _build_word_preview_and_quality(tmp_path, original, hybrid, {'groups': []})
    assert result['status'] == 'completed_diagnostic_only'
    assert result['applied_count'] == 0
    assert result['quality_summary']['unchanged_original'] == 1
    assert (tmp_path / 'ctc_word_quality_report.json').is_file()
    assert json.dumps(original) == before


def test_failed_word_stage_does_not_leave_stale_outputs(tmp_path):
    original, hybrid = _sample()
    for name in ('lyrics_timeline_ctc_word_preview.json', 'ctc_word_quality_report.json'):
        (tmp_path / name).write_text('stale')
    with patch('karaoke_phase0.alignment.word_preview.build_word_preview', side_effect=RuntimeError('bad anchors')):
        result = _build_word_preview_and_quality(tmp_path, original, hybrid, {})
    assert result['status'] == 'failed'
    assert not (tmp_path / 'ctc_word_quality_report.json').exists()
    assert not (tmp_path / 'lyrics_timeline_ctc_word_preview.json').exists()


def test_hybrid_without_selected_lines_still_generates_word_quality(tmp_path):
    g = tmp_path / 'generated'
    g.mkdir()
    original, _ = _sample()
    (g / 'lyrics_timeline.json').write_text(json.dumps(original))
    (g / 'ctc_shadow_diagnostics.json').write_text(json.dumps({
        'groups': [], 'consensus': [{'line_id': 0, 'original_start': 10.0,
                                   'median_start': 10.0, 'observation_count': 1,
                                   'spread_seconds': None}]}))
    result = build_hybrid_from_song(tmp_path, shadow_status={'status': 'completed'})
    assert result['status'] == 'completed_preview_only'
    assert result['word_preview']['status'] == 'completed_diagnostic_only'
    assert (g / 'ctc_word_quality_report.json').exists()
