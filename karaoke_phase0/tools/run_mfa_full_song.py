"""Run experimental MFA on an existing song's located lines (no GUI changes)."""
import argparse
import json
from pathlib import Path
from karaoke_phase0.mfa_full_song import run_full_song


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--song-folder', type=Path, required=True)
    p.add_argument('--dictionary', type=Path, required=True)
    p.add_argument('--mfa-exe', type=Path, required=True)
    p.add_argument('--output', type=Path, default=None)
    p.add_argument('--extra-oov', action='append', default=[])
    args = p.parse_args()
    output = args.output or args.song_folder/'generated'/'mfa'/'full_song_run_01'
    converter = Path(__file__).with_name('mfa_textgrid_to_chars.py')
    report = run_full_song(args.song_folder, output, args.dictionary, args.mfa_exe,
                           converter, extra_oovs=args.extra_oov)
    print(json.dumps({k:report[k] for k in ('status','source_line_count','processed_lines','failed_lines')},
                     ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
