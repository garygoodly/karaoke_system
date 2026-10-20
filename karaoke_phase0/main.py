import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'src'))
from karaoke_phase0.core import probe,parse_lyrics,separate,extract_pitch,align


def main():
    p=argparse.ArgumentParser(description='Karaoke Phase 0 local AI evaluation')
    sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('inspect');a.add_argument('--song',default='samples/song.mp3');a.add_argument('--lyrics',default='samples/lyrics.txt')
    a=sub.add_parser('separate');a.add_argument('--song',default='samples/song.mp3');a.add_argument('--out',default='output');a.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    a=sub.add_parser('pitch');a.add_argument('--vocals',required=True);a.add_argument('--out',default='output/pitch.npz');a.add_argument('--start',type=float,default=0);a.add_argument('--duration',type=float)
    a=sub.add_parser('align');a.add_argument('--vocals',required=True);a.add_argument('--lyrics',default='samples/lyrics.txt');a.add_argument('--out',default='output/lyrics_timeline.json');a.add_argument('--language',default='zh');a.add_argument('--device',choices=['cpu','cuda'],default='cpu');a.add_argument('--align-model')
    a=sub.add_parser('preview');a.add_argument('--timeline',default='output/lyrics_timeline.json');a.add_argument('--pitch',default='output/pitch.npz');a.add_argument('--audio',required=True);a.add_argument('--out',default='output/preview.html')
    a=p.parse_args()
    if a.cmd=='inspect':print(json.dumps({'audio':probe(a.song),'lyrics_lines':len(parse_lyrics(a.lyrics))},ensure_ascii=False,indent=2))
    elif a.cmd=='separate':print('Stems:',separate(a.song,a.out,a.device))
    elif a.cmd=='pitch':print('Pitch frames:',extract_pitch(a.vocals,a.out,a.start,a.duration))
    elif a.cmd=='align':print(json.dumps(align(a.vocals,parse_lyrics(a.lyrics),a.out,a.language,a.device,a.align_model),ensure_ascii=False)[:2000])
    elif a.cmd=='preview':
        from karaoke_phase0.preview import generate
        generate(a.timeline,a.pitch,a.audio,a.out);print('Preview:',a.out)

if __name__=='__main__':main()
