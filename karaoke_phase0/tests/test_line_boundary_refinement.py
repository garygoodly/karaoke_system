from karaoke_phase0.line_boundary_refinement import voiced_runs, propose_line_starts


def test_detects_voiced_run():
    frames=[{'time':i*.02,'hz':220,'periodicity':.9} for i in range(15)]
    assert len(voiced_runs(frames))==1


def test_unique_onset_is_review_only():
    timeline={'lines':[{'start':10,'text':'a'}]}
    pitch={'frames':[{'time':10.8+i*.02,'hz':220,'periodicity':.9} for i in range(15)]}
    result=propose_line_starts(timeline,pitch)
    assert result['status']=='diagnostic_only'
    assert result['proposals'][0]['proposed_start']==10.8
    assert timeline['lines'][0]['start']==10


def test_ambiguous_onsets_are_not_applied():
    timeline={'lines':[{'start':10}]}
    pitch={'frames':([{'time':9+i*.02,'hz':220,'periodicity':.9} for i in range(15)]+
                     [{'time':11+i*.02,'hz':220,'periodicity':.9} for i in range(15)])}
    assert propose_line_starts(timeline,pitch)['proposals'][0]['proposed_start'] is None
