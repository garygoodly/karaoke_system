import copy
import pytest
from karaoke_phase0.alignment.word_quality import evaluate_word_preview


def sample():
    def line(i, start):
        return {'line_id':i,'text':'甲乙','start':start,'end':start+1.0,
                'tokens':[{'text':'甲','start':start,'end':start+0.5},
                          {'text':'乙','start':start+0.5,'end':start+1.0}]}
    original={'lines':[line(2,10),line(5,12),line(7,14)]}
    preview=copy.deepcopy(original)
    preview['ctc_word_preview_metadata']={'applied':[{'line_id':2,'observations':3},{'line_id':5,'observations':3}],
                                           'rejected':[]}
    return original,preview


def test_good_structural_preview_not_called_acoustically_accurate():
    old,new=sample()
    report=evaluate_word_preview(old,new)
    assert report['summary']['structurally_valid_unverified']==2
    assert report['summary']['unchanged_original']==1
    assert report['summary']['review_required']==0


def test_offset_cue_forces_review_even_if_valid():
    old,new=sample()
    new['ctc_word_preview_metadata']['applied'][0]['final_offset_cue']={
        'status':'possible_vocal_offset_needs_review','offset_seconds':10.9}
    report=evaluate_word_preview(old,new)
    assert report['lines'][0]['status']=='review_required'
    assert 'unverified_vocal_offset' in report['lines'][0]['issues']


def test_detects_short_long_and_overlap():
    old,new=sample()
    new['lines'][0]['tokens'][0]['end']=10.02
    new['lines'][0]['tokens'][1]['start']=10.02
    new['lines'][0]['end']=12.5
    report=evaluate_word_preview(old,new)
    assert 'short_token' in report['lines'][0]['issues']
    assert 'next_line_overlap' in report['lines'][0]['issues']


def test_rejected_fallback_not_counted_as_ctc_success():
    old,new=sample()
    new['ctc_word_preview_metadata']={'applied':[{'line_id':5}], 'rejected':[{'line_id':2,'reason':'long'}]}
    report=evaluate_word_preview(old,new)
    assert report['summary']['fallback_lines']==1
    assert report['lines'][0]['status']=='fallback_original'


def test_rejected_but_not_restored_is_flagged():
    old,new=sample()
    new['ctc_word_preview_metadata']={'applied':[], 'rejected':[{'line_id':2}]}
    new['lines'][0]['start']=10.2
    assert 'rejected_line_not_restored' in evaluate_word_preview(old,new)['lines'][0]['issues']


def test_does_not_mutate_inputs():
    old,new=sample()
    before=copy.deepcopy((old,new))
    evaluate_word_preview(old,new)
    assert (old,new)==before


def test_mismatched_identity_fails():
    old,new=sample()
    new['lines'][0]['text']='不同'
    with pytest.raises(ValueError,match='identity'):
        evaluate_word_preview(old,new)


def test_invalid_thresholds_fail():
    old,new=sample()
    with pytest.raises(ValueError,match='threshold'):
        evaluate_word_preview(old,new,max_overlap=-1)
