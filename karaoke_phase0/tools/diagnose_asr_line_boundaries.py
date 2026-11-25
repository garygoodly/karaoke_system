import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from karaoke_phase0.asr_line_refinement import run

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--timeline",required=True)
    p.add_argument("--asr",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    report=run(a.timeline,a.asr,a.output)
    print("Lines:",len(report["proposals"]))
    print("Unique ASR candidates:",sum(p["proposed_start"] is not None for p in report["proposals"]))
    print("Report:",a.output)
if __name__=="__main__":main()
