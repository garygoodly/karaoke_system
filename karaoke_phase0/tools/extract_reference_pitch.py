"""Extract song reference F0; never modifies the original lyrics timeline."""
import argparse
from pathlib import Path
from karaoke_phase0.reference_pitch import extract_reference


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--song-folder', required=True, type=Path)
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    parser.add_argument('--threshold', type=float, default=0.35)
    args = parser.parse_args()
    generated = args.song_folder / 'generated'
    source = generated / 'vocals.wav'
    if not source.is_file():
        parser.error(f'Missing {source}')
    output = generated / 'reference_pitch.json'
    if output.exists():
        parser.error(f'{output} exists; move it first to preserve previous results')
    result = extract_reference(source, output, device=args.device, periodicity_threshold=args.threshold)
    print(f"Saved {len(result['frames'])} reference frames: {output}")


if __name__ == '__main__':
    main()
