import importlib.util
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'tools'/'benchmark_note_scoring.py'
spec=importlib.util.spec_from_file_location('benchmark_note_scoring',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_reference_segments_and_note_score():
    ref=[{'time':i*.02,'hz':220,'periodicity':.9} for i in range(20)]
    ref += [{'time':.4+i*.02,'hz':330,'periodicity':.9} for i in range(20)]
    notes=m.segment_notes(ref)
    assert len(notes)==2
    users=[{'time':i*.02,'hz':220,'periodicity':.9} for i in range(20)]
    users += [{'time':.4+i*.02,'hz':330,'periodicity':.9} for i in range(20)]
    result=m.score_notes(notes,users)
    assert result['summary']['note_score']==100

def test_missing_user_note_not_scored_zero():
    notes=[{'start':0,'end':.5,'reference_hz':220,'reference_frames':25}]
    result=m.score_notes(notes,[])
    assert result['summary']['note_score'] is None
    assert result['summary']['note_coverage']==0

def test_octave_mode():
    notes=[{'start':0,'end':.5,'reference_hz':220,'reference_frames':25}]
    users=[{'time':.1+i*.05,'hz':440,'periodicity':.9} for i in range(6)]
    assert m.score_notes(notes,users)['summary']['note_score']==0
    assert m.score_notes(notes,users,octave_invariant=True)['summary']['note_score']==100
