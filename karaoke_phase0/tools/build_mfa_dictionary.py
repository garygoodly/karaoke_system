"""Standalone CLI for Karaoke MFA G2P dictionary augmentation."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from karaoke_phase0.mfa_g2p import extend_dictionary


def main():
    p = argparse.ArgumentParser(description='Generate derived MFA pronunciation dictionary')
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--lyrics', type=Path, required=True, help='UTF-8 lyrics TXT (one line per phrase)')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--mfa', required=True, help='Full path to MFA executable in karaoke-mfa Conda env')
    p.add_argument('--oov-file', type=Path, help='Optional one-word-per-line MFA OOV report')
    a = p.parse_args()
    if a.output.exists():
        p.error('Output exists: choose a new path to preserve previous results')
    lyrics = [s.strip() for s in a.lyrics.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    extra = []
    if a.oov_file:
        extra = [s.split('\t')[0].strip() for s in a.oov_file.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    report = extend_dictionary(a.base, a.output, lyrics, a.mfa, extra_oovs=extra)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['requires_review']:
        print('WARNING: unresolved pronunciations; review before alignment.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
