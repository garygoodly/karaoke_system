"""Opt-in automatic hybrid preview from existing CTC shadow diagnostics.

Never modifies authoritative lyrics_timeline.json. The existing v6 boundary
report is optional: without it the conservative selector will not adopt v4
peaks, because raw v4 consensus has not been validated for automatic use.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from .quality_evaluation import evaluate
from .controlled_adoption import propose
from .playable_timeline import build_preview


def _read(path):
    with Path(path).open(encoding='utf-8-sig') as f:
        return json.load(f)


def _write_atomic(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    try:
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def build_hybrid_from_song(song, *, shadow_status=None):
    """Run quality -> selection -> safe playable preview, without ground truth.

    Returns an explicit skip/failure status rather than treating a missing
    v6 refinement as a low-confidence prediction.
    """
    generated = Path(song) / 'generated'
    timeline_path = generated / 'lyrics_timeline.json'
    shadow_path = generated / 'ctc_shadow_diagnostics.json'
    v6_path = generated / 'ctc_boundary_aware_v6.json'
    out_path = generated / 'lyrics_timeline_hybrid_preview.json'
    if (shadow_status or {}).get('status') != 'completed':
        return {'status': 'skipped_shadow_unavailable', 'reason': (shadow_status or {}).get('status', 'not_run')}
    if not timeline_path.is_file() or not shadow_path.is_file():
        return {'status': 'skipped_missing_inputs'}
    timeline, shadow = _read(timeline_path), _read(shadow_path)
    if not isinstance(shadow, dict) or not isinstance(shadow.get('consensus'), list):
        raise ValueError('Invalid shadow consensus report')
    # Derive boundary-anchored candidates from the CURRENT shadow run, not
    # a historical v6 JSON that may belong to an earlier model/timeline.
    from .boundary_candidates import from_shadow
    v6 = from_shadow(shadow, timeline)
    from .context_fallback import diagnose_unanchored
    context_report = diagnose_unanchored(shadow, timeline)
    _write_atomic(generated / 'ctc_context_fallback_diagnostics.json', context_report)
    # Diagnostic only: repeated lyric tokens and vocal RMS cannot authorize adoption.
    from .boundary_conflict import diagnose_boundary
    if len(timeline.get('lines', [])) > 19:
        audio_path = generated / 'vocals.wav'
        conflict = diagnose_boundary(shadow, timeline, previous_line_id=18,
                                     audio_path=audio_path if audio_path.is_file() else None)
        _write_atomic(generated / 'ctc_boundary_conflict_18_19.json', conflict)
    quality = evaluate(shadow, v6, truth={})
    candidate = propose(timeline, quality)
    preview = build_preview(timeline, candidate)
    preview['hybrid_metadata'] = {
        'status': 'preview_only',
        'source': 'automatic_ctc_shadow_quality_and_fresh_boundary_anchors',
        'warning': 'Experimental, not validated for automatic playback. Original timeline unchanged.',
        'selected_lines': [x['line_id'] for x in preview['ctc_preview_metadata']['applied']],
    }
    _write_atomic(out_path, preview)
    # Word preview is optional and must never affect the line-level preview.
    # A failure is reported separately, without replacing any authoritative data.
    word_result = _build_word_preview_and_quality(generated, timeline, preview, shadow)
    return {'word_preview': word_result, 'status': 'completed_preview_only', 'output': str(out_path),
            'proposed_count': candidate['ctc_candidate_metadata']['proposed_count'],
            'applied_count': preview['ctc_preview_metadata']['applied_count'],
            'rejected_count': preview['ctc_preview_metadata']['rejected_count'],
            'v6_available': any(row['anchored_count'] for row in v6['lines']),
            'v6_generated_from_shadow': True,
            'context_fallback_diagnostic_count': sum(bool(x['group_evidence']) for x in context_report['lines'])}


def _build_word_preview_and_quality(generated, original, hybrid, shadow):
    """Create read-only word preview and quality report from this run's data.

    Quality status is diagnostic: no word timing is auto-approved for playback.
    """
    from .word_preview import build_word_preview
    from .word_quality import evaluate_word_preview

    word_path = generated / 'lyrics_timeline_ctc_word_preview.json'
    quality_path = generated / 'ctc_word_quality_report.json'
    try:
        audio = generated / 'vocals.wav'
        word = build_word_preview(original, hybrid, shadow,
                                  audio_path=audio if audio.is_file() else None)
        quality = evaluate_word_preview(original, word)
        # Do not publish a partial pair if construction/validation failed.
        _write_atomic(word_path, word)
        _write_atomic(quality_path, quality)
        return {
            'status': 'completed_diagnostic_only',
            'output': str(word_path), 'quality_output': str(quality_path),
            'applied_count': word['ctc_word_preview_metadata']['applied_count'],
            'rejected_count': word['ctc_word_preview_metadata']['rejected_count'],
            'quality_summary': quality['summary'],
        }
    except Exception as exc:
        # A failed run must not leave previous outputs masquerading as current.
        for path in (word_path, quality_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        return {'status': 'failed', 'reason': str(exc)}
