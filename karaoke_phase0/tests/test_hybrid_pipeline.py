import copy
import json
from pathlib import Path
from karaoke_phase0.alignment.hybrid_pipeline import build_hybrid_from_song


def test_missing_shadow_is_safe(tmp_path):
    assert build_hybrid_from_song(tmp_path, shadow_status={'status':'failed'})['status']=='skipped_shadow_unavailable'


def test_shadow_without_v6_keeps_original(tmp_path):
    g=tmp_path/'generated';g.mkdir()
    original={'status':'review_required','lines':[{'line_id':0,'text':'abc','start':10.0,'end':12.0,'tokens':[{'start':10.0,'end':11.0}]}]}
    (g/'lyrics_timeline.json').write_text(json.dumps(original))
    (g/'ctc_shadow_diagnostics.json').write_text(json.dumps({'groups':[], 'consensus':[{'line_id':0,'original_start':10.0,'median_start':8.0,'observation_count':3,'spread_seconds':0.01}]}))
    result=build_hybrid_from_song(tmp_path,shadow_status={'status':'completed'})
    assert result['status']=='completed_preview_only'
    assert result['applied_count']==0
    assert json.loads((g/'lyrics_timeline.json').read_text())==original


def test_legacy_v6_alone_does_not_trigger_adoption(tmp_path):
    g=tmp_path/'generated';g.mkdir()
    timeline={'lines':[{'line_id':0,'text':'abc','start':10.0,'end':13.0,'tokens':[{'start':10.0,'end':11.0}]}]}
    (g/'lyrics_timeline.json').write_text(json.dumps(timeline))
    (g/'ctc_shadow_diagnostics.json').write_text(json.dumps({'groups':[], 'consensus':[{'line_id':0,'original_start':10.0,'median_start':8.1,'observation_count':3,'spread_seconds':0.01}]}))
    (g/'ctc_boundary_aware_v6.json').write_text(json.dumps({'lines':[{'line_id':0,'original_start':10.0,'token_peak_median':8.2,'anchored_count':2,'token_peak_spread_seconds':0.01}]}))
    r=build_hybrid_from_song(tmp_path,shadow_status={'status':'completed'})
    assert r['applied_count']==0
    assert r['v6_available'] is False


def test_stale_v6_is_ignored(tmp_path):
    g=tmp_path/'generated';g.mkdir()
    (g/'lyrics_timeline.json').write_text(json.dumps({'lines':[{'line_id':0,'text':'abc','start':10.0,'end':12.0,'tokens':[{'start':10.0,'end':11.0}]}]}))
    (g/'ctc_shadow_diagnostics.json').write_text(json.dumps({'groups':[], 'consensus':[{'line_id':0,'original_start':10.0,'median_start':8.0,'observation_count':3,'spread_seconds':0.01}]}))
    (g/'ctc_boundary_aware_v6.json').write_text(json.dumps({'lines':[{'line_id':0,'original_start':11.0,'token_peak_median':8.0,'anchored_count':2,'token_peak_spread_seconds':0.01}]}))
    r=build_hybrid_from_song(tmp_path,shadow_status={'status':'completed'})
    assert r['v6_available'] is False and r['applied_count']==0
