import argparse
import json
from pathlib import Path
from .model import today_uk
from .pipeline import collect, load_state, load_registry, effective_records

def main():
    parser=argparse.ArgumentParser(description='Collect publisher facts and render Forthcoming Poetry')
    parser.add_argument('command',choices=['collect','build','update','status'])
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--publisher',action='append',help='Collect selected publisher IDs only')
    args=parser.parse_args(); root=args.root.resolve(); today=today_uk()
    if args.command in ('collect','update'): collect(root,today,args.publisher)
    if args.command in ('build','update'):
        from .render import render
        render(root,today)
    if args.command=='status':
        state=load_state(root)
        for p in load_registry(root):
            s=state['sources'].get(p['id'],{})
            print(f"{p['name']}: {s.get('status','not_checked')} — {s.get('scope',p['coverage'])}")

if __name__=='__main__': main()
