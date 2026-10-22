"""Run isolated MFA benchmark from Karaoke root using uv Python."""
import argparse
import json
from pathlib import Path
from karaoke_phase0.mfa_workflow import run_benchmark


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--corpus',type=Path,default=Path('benchmarks/paomo'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dictionary',type=Path,required=True)
    parser.add_argument('--mfa-exe',type=Path,required=True)
    parser.add_argument('--extra-oov',action='append',default=[],help='Known compound OOV such as 泡沫; repeatable')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    result=run_benchmark(args.corpus,args.output,args.dictionary,args.mfa_exe,
                         root/'mfa_textgrid_to_chars.py',extra_oovs=args.extra_oov)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
