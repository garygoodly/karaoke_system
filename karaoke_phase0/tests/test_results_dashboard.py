import csv
import json
from pathlib import Path
import importlib.util
_spec = importlib.util.spec_from_file_location("build_results_dashboard", Path(__file__).resolve().parents[1] / "tools" / "build_results_dashboard.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
make_report, render_html = _mod.make_report, _mod.render_html

def test_offline_dashboard(tmp_path):
    r=tmp_path/'r.json';r.write_text(json.dumps({'frames':[{'time':0,'hz':200},{'time':.1,'hz':200},{'time':.2,'hz':None}]}))
    t=tmp_path/'t.json';t.write_text(json.dumps({'lines':[{'line_id':0,'text':'<script>alert(1)</script>','start':0,'end':.3}]}))
    u=tmp_path/'u.csv';u.write_text('time_s,crepe_hz,crepe_periodicity\n0,200,.9\n.1,220,.9\n.2,,0\n')
    d=make_report(r,u,t);assert d['meta']['matched_frames']==2
    assert d['lines'][0]['matched']==2
    h=render_html(d);assert '<script>alert(1)</script>' not in h
    assert 'Offline Diagnostics' in h
