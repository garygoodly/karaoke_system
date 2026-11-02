from karaoke_phase0.lyrics_preview import render

def test_note_scoring_v2_ui(tmp_path):
    target=tmp_path/'player.html'
    render({'lines':[]},target,player_mode=True)
    html=target.read_text(encoding='utf-8')
    for token in ('id="scoreNoteV2"','id="scoreNoteCoverage"','id="scoreUnscoredNotes"',
                  'function segmentReferenceNotesV2(', 'function scoreCapturedNotesV2(',
                  'scoreCapturedNotesV2(pitchCapture,referenceFrames)',
                  'const result=scoreCapturedFrames(pitchCapture,referenceFrames,vocalActivityFrames)'):
        assert token in html
