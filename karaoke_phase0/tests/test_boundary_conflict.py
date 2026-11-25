import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from karaoke_phase0.alignment.boundary_conflict import diagnose_boundary


def test_repeated_character_is_diagnostic_only():
    timeline={'lines':[{'line_id':18,'text':'仍將燃燒思念','end':190.52}, {'line_id':19,'text':'燒毀了我','start':192.5}]}
    shadow={'groups':[{'status':'candidate_needs_review','lines':[{'line_id':19,'start_seconds':189.0}]}, {'status':'candidate_needs_review','lines':[{'line_id':19,'start_seconds':189.02}]}]}
    out=diagnose_boundary(shadow,timeline)
    assert out['ctc_candidate_median']==189.01
    assert out['ctc_spread_seconds']==0.02
    assert out['repeated_token_ambiguity']
    assert '燒' in out['repeated_boundary_characters']
    assert out['auto_adopt'] is False
    assert out['acoustic_evidence']['status']=='not_available'


def test_no_ctc_path_never_approves():
    timeline={'lines':[{'line_id':18,'text':'abc','end':190.52},{'line_id':19,'text':'def','start':192.5}]}
    out=diagnose_boundary({'groups':[]},timeline)
    assert out['ctc_candidate_median'] is None
    assert not out['repeated_token_ambiguity']
    assert not out['auto_adopt']


def test_integration_idempotent(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    from integrate_boundary_conflict import integrate
    p=tmp_path/'hybrid_pipeline.py'
    p.write_text("def run():\n    _write_atomic(generated / 'ctc_context_fallback_diagnostics.json', context_report)\n")
    assert integrate(p)=='applied'
    once=p.read_text()
    assert integrate(p)=='already_applied'
    assert p.read_text()==once
