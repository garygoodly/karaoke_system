import copy
import pytest
from karaoke_phase0.alignment.playable_timeline import build_preview


def fixture():
    t={'status':'ready','lines':[
        {'line_id':0,'text':'a','start':0.0,'end':3.0,'tokens':[{'text':'a','start':0.0,'end':3.0}]},
        {'line_id':1,'text':'bc','start':5.0,'end':9.0,'tokens':[{'text':'b','start':5.0,'end':7.0},{'text':'c','start':7.0,'end':9.0}]},
        {'line_id':2,'text':'d','start':12.0,'end':14.0,'tokens':[{'text':'d','start':12.0,'end':14.0}]}]}
    c=copy.deepcopy(t)
    c['lines'][1]['ctc_adoption']={'decision':'propose_ctc','original_start':5.0,'proposed_start':4.0}
    return t,c


def test_shift_tokens_preserves_durations_and_source():
    t,c=fixture(); before=copy.deepcopy(t)
    out=build_preview(t,c)
    assert t==before
    assert out['lines'][1]['start']==4.0 and out['lines'][1]['end']==8.0
    assert [x['start'] for x in out['lines'][1]['tokens']]==[4.0,6.0]
    assert out['lines'][1]['needs_review'] is True
    assert out['status']=='review_required'
    assert out['ctc_preview_metadata']['applied_count']==1


def test_rejects_neighbor_overlap_without_changing_line():
    t,c=fixture();c['lines'][1]['ctc_adoption']['proposed_start']=2.5
    out=build_preview(t,c)
    assert out['lines'][1]==t['lines'][1]
    assert out['ctc_preview_metadata']['rejected'][0]['reason']=='previous_line_overlap'


def test_rejects_stale_candidate_and_bad_tokens():
    t,c=fixture();c['lines'][1]['ctc_adoption']['original_start']=8
    assert build_preview(t,c)['ctc_preview_metadata']['rejected'][0]['reason']=='stale_candidate_original_start'
    t,c=fixture();t['lines'][1]['tokens'][0]['end']=20
    assert build_preview(t,c)['ctc_preview_metadata']['rejected'][0]['reason']=='invalid_token_intervals'


def test_rejects_mismatched_ids():
    t,c=fixture();c['lines'][1]['line_id']=100
    with pytest.raises(ValueError,match='IDs'):build_preview(t,c)


def test_kept_lines_unmodified():
    t,c=fixture();o=build_preview(t,c)
    assert o['lines'][0]==t['lines'][0] and o['lines'][2]==t['lines'][2]
