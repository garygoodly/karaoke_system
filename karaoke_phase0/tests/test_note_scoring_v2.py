import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from benchmark_note_scoring_v2 import segment_notes_v2

def test_sustained_vibrato_merges():
    frames=[{'time':i*.02,'hz':220*(2**(((-1)**i*28)/1200)),'periodicity':.9} for i in range(70)]
    notes=segment_notes_v2(frames,0,1.38)
    assert len(notes)==1
    assert abs(notes[0]['reference_hz']-220)<5

def test_separate_notes_and_rest():
    frames=[{'time':i*.02,'hz':220 if i<30 else (None if i<50 else 330),'periodicity':.9} for i in range(90)]
    notes=segment_notes_v2(frames,0,1.78)
    assert len(notes)==2

def test_restrict_capture_window():
    frames=[{'time':i*.02,'hz':220,'periodicity':.9} for i in range(200)]
    notes=segment_notes_v2(frames,1,2)
    assert len(notes)==1 and notes[0]['start']>=1 and notes[0]['end']<=2
