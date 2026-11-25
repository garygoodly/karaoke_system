"""Generate a non-destructive line onset review report."""
import argparse
from karaoke_phase0.line_boundary_refinement import build_report

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--timeline',required=True)
    p.add_argument('--pitch',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    result=build_report(a.timeline,a.pitch,a.output)
    print('Line candidates:',sum(x['proposed_start'] is not None for x in result['proposals']))
    print('Report:',a.output)
