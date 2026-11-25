import json
from karaoke_phase0.alignment.boundary_candidates import from_shadow
from karaoke_phase0.alignment.hybrid_pipeline import build_hybrid_from_song


def fixtures():
    timeline = {'status':'review_required','lines':[
        {'line_id':0,'text':'a','start':5.0,'end':7.0,'tokens':[{'start':5.0,'end':6.0}]},
        {'line_id':1,'text':'b','start':10.0,'end':13.0,'tokens':[{'start':10.0,'end':11.0}]},
        {'line_id':2,'text':'c','start':16.0,'end':19.0,'tokens':[{'start':16.0,'end':17.0}]}]}
    groups=[]
    for i,st in enumerate((8.0,8.02)):
        groups.append({'status':'candidate_needs_review','line_ids':[0,1,2], 'lines':[
            {'line_id':0,'original_start':5.0,'start_seconds':5.0,'end_seconds':7.0},
            {'line_id':1,'original_start':10.0,'start_seconds':st,'end_seconds':11.0},
            {'line_id':2,'original_start':16.0,'start_seconds':16.0,'end_seconds':18.0}]})
    shadow={'consensus':[{'line_id':i,'original_start':line['start'],'median_start':line['start'],'observation_count':2,'spread_seconds':0.01} for i,line in enumerate(timeline['lines'])], 'groups':groups}
    return timeline,shadow


def test_anchor_selection():
    t,s=fixtures()
    rows=from_shadow(s,t)['lines']
    assert rows[0]['anchored_count']==0
    assert rows[1]['anchored_count']==2
    assert rows[1]['token_peak_median']==8.01
    assert rows[1]['token_peak_spread_seconds']==0.02


def test_reject_unanchored_and_overlap():
    t,s=fixtures()
    s['groups'].append({'status':'candidate_needs_review','line_ids':[1,2], 'lines':[
        {'line_id':1,'original_start':10.0,'start_seconds':4.0,'end_seconds':11.0},
        {'line_id':2,'original_start':16.0,'start_seconds':10.0,'end_seconds':12.0}]})
    assert from_shadow(s,t)['lines'][1]['anchored_count']==2
    assert from_shadow(s,t)['lines'][2]['anchored_count']==2


def test_stale_group_rejected():
    import pytest
    t,s=fixtures()
    s['groups'][0]['lines'][1]['original_start']=99.0
    with pytest.raises(ValueError,match='Stale'):
        from_shadow(s,t)


def test_end_to_end_without_existing_v6(tmp_path):
    t,s=fixtures()
    g=tmp_path/'generated';g.mkdir()
    (g/'lyrics_timeline.json').write_text(json.dumps(t))
    (g/'ctc_shadow_diagnostics.json').write_text(json.dumps(s))
    r=build_hybrid_from_song(tmp_path,shadow_status={'status':'completed'})
    assert r['status']=='completed_preview_only'
    assert r['v6_generated_from_shadow'] is True
    assert r['applied_count']==1
    preview=json.loads((g/'lyrics_timeline_hybrid_preview.json').read_text())
    assert preview['lines'][1]['start']==8.01
    assert json.loads((g/'lyrics_timeline.json').read_text())==t


def test_old_v6_ignored(tmp_path):
    t,s=fixtures()
    g=tmp_path/'generated';g.mkdir()
    (g/'lyrics_timeline.json').write_text(json.dumps(t))
    (g/'ctc_shadow_diagnostics.json').write_text(json.dumps(s))
    (g/'ctc_boundary_aware_v6.json').write_text(json.dumps({'lines':[{'line_id':1,'original_start':10.0,'token_peak_median':100.0,'anchored_count':3,'token_peak_spread_seconds':0.0}]}))
    r=build_hybrid_from_song(tmp_path,shadow_status={'status':'completed'})
    assert r['applied_count']==1
