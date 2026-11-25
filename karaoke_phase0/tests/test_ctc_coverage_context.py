from karaoke_phase0.alignment.ctc_text_coverage import prepare_ctc_text
from karaoke_phase0.alignment.context_fallback import diagnose_unanchored
from karaoke_phase0.alignment.boundary_candidates import from_shadow

class Converter:
    def convert(self, s): return s

class Tokenizer:
    unk_token_id = 0
    def __call__(self, s, add_special_tokens=False):
        return type('R', (), {'input_ids': [0 if c in '冉烬龘' else ord(c) for c in s]})()
    def decode(self, ids, skip_special_tokens=True):
        return ''.join(chr(i) for i in ids if i)

def test_exact_unchanged():
    assert prepare_ctc_text('你好', Converter(), Tokenizer())['status'] == 'exact'

def test_proxy_audited():
    result = prepare_ctc_text('仍将冉冉升起', Converter(), Tokenizer())
    assert result['status'] == 'phonetic_proxy_diagnostic_only'
    assert result['text'] == '仍将然然升起'
    assert len(result['proxies']) == 2

def test_unsupported_remains_excluded():
    assert prepare_ctc_text('冉龘', Converter(), Tokenizer())['status'] == 'unsupported'

def test_unanchored_consensus_never_auto_adopt():
    timeline = {'lines':[{'line_id':18,'start':183.5,'end':190.52}, {'line_id':19,'start':192.5,'end':203.52}]}
    shadow = {'groups':[{'status':'candidate_needs_review','line_ids':[19], 'lines':[{'line_id':19,'original_start':192.5,'start_seconds':189.0}]}, {'status':'candidate_needs_review','line_ids':[19], 'lines':[{'line_id':19,'original_start':192.5,'start_seconds':189.02}]}]}
    r = next(x for x in diagnose_unanchored(shadow, timeline)['lines'] if x['line_id'] == 19)
    assert r['candidate_start'] == 189.01
    assert r['overlap_previous_original_seconds'] == 1.51
    assert r['auto_adopt'] is False

def test_proxy_context_not_auto_anchored():
    t={'lines':[{'line_id':0,'start':1.0},{'line_id':1,'start':5.0}]}
    s={'consensus':[], 'phonetic_proxy_lines':{'0':[{'original':'冉','proxy':'然'}]}, 'groups':[{'status':'candidate_needs_review','line_ids':[0,1],'lines':[{'line_id':0,'original_start':1.0,'start_seconds':1.0,'end_seconds':3.0},{'line_id':1,'original_start':5.0,'start_seconds':4.0,'end_seconds':6.0}]}]}
    assert from_shadow(s,t)['lines'][1]['anchored_count']==0
