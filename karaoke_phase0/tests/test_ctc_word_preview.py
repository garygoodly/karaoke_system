from karaoke_phase0.alignment.word_preview import reconstruct, build_word_preview, inspect_character_anchors


def line(start=10):
    return {'line_id': 2, 'text': '甲乙丙', 'start': start, 'end': start+1.5,
            'tokens': [{'text': c, 'start': start+i*.5, 'end': start+(i+1)*.5} for i,c in enumerate('甲乙丙')]}


def test_reconstruct_midpoints():
    tokens, reason = reconstruct(line(), [[10.2,10.7,11.2],[10.21,10.71,11.21]])
    assert reason is None
    assert tokens[0]['end'] == 10.455
    assert tokens[1]['start'] == tokens[0]['end']
    assert tokens[-1]['end'] == 11.5


def test_reject_unstable():
    assert reconstruct(line(), [[10.2,10.7,11.2],[10.6,10.8,11.3]])[1] == 'unstable_character_anchors'


def test_reject_mismatch():
    assert reconstruct(line(), [[10.2,10.7],[10.2,10.7]])[1] == 'token_character_mismatch'


def test_reject_single_context():
    assert reconstruct(line(), [[10.2,10.7,11.2]])[1] == 'insufficient_contexts'


def test_fallback_does_not_mutate():
    original = {'lines': [line()]}
    hybrid = {'lines': [line(10.1)], 'hybrid_metadata': {'selected_lines': [2]}}
    shadow = {'groups': []}
    result = build_word_preview(original, hybrid, shadow)
    assert result['ctc_word_preview_metadata']['rejected_count'] == 1
    assert result['lines'][0] == original['lines'][0]
    assert hybrid['lines'][0]['tokens'] != original['lines'][0]['tokens']


def test_apply_two_contexts():
    original = {'lines': [line()]}
    hybrid = {'lines': [line()], 'hybrid_metadata': {'selected_lines': [2]}}
    shadow = {'groups': [{'status': 'candidate_needs_review', 'lines': [{'line_id': 2, 'character_anchors': anchors}]}
                         for anchors in ([10.2,10.7,11.2], [10.21,10.71,11.21])]}
    result = build_word_preview(original, hybrid, shadow)
    assert result['ctc_word_preview_metadata']['applied_count'] == 1
    assert result['lines'][0]['tokens'][0]['end'] == 10.455


def test_long_gap_diagnostic_identifies_character_and_neighbor_gaps():
    item = line()
    item['end'] = 20.0
    observations = [[10.2, 18.0, 19.0], [10.21, 18.01, 19.01]]
    details = inspect_character_anchors(item, observations)
    assert details['status'] == 'long_intervals_found'
    assert details['anomalies'][0]['character'] == '甲'
    assert details['anomalies'][0]['next_anchor_gap_seconds'] > 7.0
    assert reconstruct(item, observations)[1] == 'implausibly_long_character'


def test_rejected_line_includes_diagnostics_without_mutating_original():
    item = line()
    item['end'] = 20.0
    original = {'lines': [item]}
    hybrid = {'lines': [item], 'hybrid_metadata': {'selected_lines': [2]}}
    observations = [[10.2, 18.0, 19.0], [10.21, 18.01, 19.01]]
    shadow = {'groups': [{'status': 'candidate_needs_review', 'lines': [{'line_id': 2, 'character_anchors': obs}]} for obs in observations]}
    result = build_word_preview(original, hybrid, shadow)
    rejected = result['ctc_word_preview_metadata']['rejected'][0]
    assert rejected['reason'] == 'implausibly_long_character'
    assert rejected['anchor_diagnostics']['anomalies']
    assert result['lines'][0] == item


def test_final_offset_requires_explicit_cue():
    item = line()
    item['end'] = 16.0
    anchors = [[10.2, 10.7, 11.2], [10.21, 10.71, 11.21]]
    assert reconstruct(item, anchors)[1] == 'implausibly_long_character'
    tokens, reason = reconstruct(item, anchors, final_offset=12.3)
    assert reason is None
    assert tokens[-1]['end'] == 12.3
    assert item['end'] == 16.0


def test_offset_cue_sustained_silence(tmp_path):
    import numpy as np
    import soundfile as sf
    from karaoke_phase0.alignment.word_preview import estimate_final_vocal_offset
    sr = 16000
    audio = np.zeros(sr * 6, dtype='float32')
    audio[2*sr:4*sr] = 0.1 * np.sin(2 * np.pi * 200 * np.arange(2*sr) / sr)
    path = tmp_path / 'vocal.wav'
    sf.write(path, audio, sr)
    cue = estimate_final_vocal_offset(path, 3.7, 5.5)
    assert cue is not None
    assert 3.95 <= cue['offset_seconds'] <= 4.05


def test_offset_cue_rejects_continuous_vocals(tmp_path):
    import numpy as np
    import soundfile as sf
    from karaoke_phase0.alignment.word_preview import estimate_final_vocal_offset
    sr = 16000
    audio = 0.1 * np.sin(2 * np.pi * 200 * np.arange(sr*6) / sr)
    path = tmp_path / 'vocal.wav'
    sf.write(path, audio.astype('float32'), sr)
    assert estimate_final_vocal_offset(path, 3.7, 5.5) is None
