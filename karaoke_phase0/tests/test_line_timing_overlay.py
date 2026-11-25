import json
from karaoke_phase0.line_timing_overlay import line_start_overrides


def test_applied_only(tmp_path):
    generated=tmp_path/'generated';generated.mkdir()
    timeline={'lines':[{'line_id':2,'text':'hello','start':41.5,'end':51.5},{'line_id':3,'text':'next','start':52,'end':58}]}
    preview={'ctc_preview_metadata':{'status':'preview_only','applied':[{'line_id':2}]},'lines':[{'line_id':2,'text':'hello','start':39.008,'end':51},{'line_id':3,'text':'next','start':50,'end':58}]}
    (generated/'lyrics_timeline_hybrid_preview.json').write_text(json.dumps(preview))
    assert line_start_overrides(tmp_path,timeline)=={2:39.008}
    preview['lines'][0]['text']='wrong'
    (generated/'lyrics_timeline_hybrid_preview.json').write_text(json.dumps(preview))
    assert line_start_overrides(tmp_path,timeline)=={}


def test_fallback(tmp_path):
    assert line_start_overrides(tmp_path,{'lines':[]})=={}
    (tmp_path/'generated').mkdir()
    (tmp_path/'generated/lyrics_timeline_hybrid_preview.json').write_text('{')
    assert line_start_overrides(tmp_path,{'lines':[]})=={}
