import copy
import json
import pytest
from karaoke_phase0.alignment.controlled_adoption import propose


def fixture():
    timeline = {'status': 'review_required', 'lines': [
        {'line_id': 0, 'start': 26.5, 'end': 31.5, 'tokens': [{'text':'a','start':26.5,'end':27}], 'needs_review': True},
        {'line_id': 1, 'start': 41.5, 'end': 50, 'tokens': [{'text':'b','start':41.5,'end':42}]},
        {'line_id': 2, 'start': 67.5, 'end': 75, 'tokens': []},
        {'line_id': 3, 'start': 229.5, 'end': 234, 'tokens': []},
    ]}
    quality = {'lines': [
        {'line_id': 1, 'ctc_token_peak':39.008, 'candidate_source':'v6', 'anchored_count':2,'spread_seconds':0.003},
        {'line_id': 2, 'ctc_token_peak':64.939, 'candidate_source':'v6', 'anchored_count':2,'spread_seconds':0.017},
        {'line_id': 3, 'ctc_token_peak':229.31, 'candidate_source':'v6', 'anchored_count':2,'spread_seconds':0.396},
    ]}
    return timeline, quality


def test_proposes_only_stable_significant_changes():
    t,q=fixture(); before=copy.deepcopy(t); out=propose(t,q)
    assert out['ctc_candidate_metadata']['proposed_count']==2
    assert [x['ctc_adoption']['decision'] for x in out['lines']] == ['keep_original','propose_ctc','propose_ctc','keep_original']
    assert out['lines'][3]['ctc_adoption']['reason']=='unstable_candidate'
    assert t == before
    assert out['status']=='review_required'
    for x,y in zip(t['lines'],out['lines']):
        assert x['start']==y['start'] and x['end']==y['end'] and x['tokens']==y['tokens']


def test_missing_or_unanchored_kept():
    t,q=fixture();q['lines'][0]['candidate_source']='v4'
    out=propose(t,q)
    assert out['lines'][1]['ctc_adoption']['reason']=='not_boundary_anchored'
    assert out['lines'][0]['ctc_adoption']['reason']=='no_quality_record'


def test_rejects_invalid_and_duplicate():
    t,q=fixture();q['lines'].append(q['lines'][0]);
    with pytest.raises(ValueError,match='Duplicate'):propose(t,q)
    with pytest.raises(ValueError,match='threshold'):propose(t,{'lines':[]},max_spread=-1)


def test_no_ground_truth_leakage():
    t,q=fixture();a=propose(t,q)
    for row in q['lines']:
        row['ground_truth_start']=row['ctc_token_peak']
        row['ctc_absolute_error']=0
    assert a==propose(t,q)
