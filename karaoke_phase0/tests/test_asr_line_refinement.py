import json
import pytest
from karaoke_phase0.asr_line_refinement import rank_lines,run

def test_exact_match_candidate():
    t={"lines":[{"line_id":0,"text":"看 回憶這把刀","start":26.5}]}
    a={"asr_segments":[{"index":1,"start":27,"end":32,"text":"看回憶這把刀"}],"line_matches":[{"line_id":0,"similarity":1.0}]}
    p=rank_lines(t,a)["proposals"][0]
    assert p["proposed_start"]==27
    assert p["delta_seconds"]==0.5

def test_ambiguous_repeated_text_not_applied():
    t={"lines":[{"line_id":0,"text":"細數自己","start":10}]}
    a={"asr_segments":[{"index":0,"start":9.9,"end":11,"text":"細數自己"},{"index":1,"start":10.1,"end":11.2,"text":"細數自己"}],"line_matches":[{"line_id":0,"similarity":1.0}]}
    assert rank_lines(t,a)["proposals"][0]["proposed_start"] is None

def test_missing_asr_does_not_guess():
    assert rank_lines({"lines":[{"line_id":0,"text":"abc","start":1}]},{})["proposals"][0]["proposed_start"] is None

def test_refuses_overwrite(tmp_path):
    p=tmp_path/'x.json';p.write_text(json.dumps({"lines":[]}),encoding='utf8')
    with pytest.raises(ValueError):run(p,p,p)
