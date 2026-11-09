import argparse
import json
from pathlib import Path
from .model import today_uk
from .pipeline import collect, load_state, load_registry, effective_records

def main():
    parser=argparse.ArgumentParser(description='Collect publisher facts and render Forthcoming Poetry')
    parser.add_argument('command',choices=['collect','build','update','status','import-csv'])
    parser.add_argument('csv_file',nargs='?',type=Path,help='CSV file for import-csv')
    parser.add_argument('--dry-run',action='store_true',help='Validate an import and report counts without saving or rebuilding')
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--publisher',action='append',help='Collect selected publisher IDs only')
    args=parser.parse_args(); root=args.root.resolve(); today=today_uk()
    if args.command=='import-csv':
        if args.csv_file is None:parser.error('import-csv requires a CSV file')
        from .imports import import_csv
        try:summary=import_csv(root,args.csv_file,dry_run=args.dry_run)
        except (ValueError,OSError) as e:parser.exit(2,f'Import failed: {e}\n')
        print(('Dry run: ' if args.dry_run else 'Imported: ')+', '.join(f'{v} {k}' for k,v in summary.items()))
        if not args.dry_run:
            from .render import render
            render(root,today)
        return
    if args.csv_file is not None or args.dry_run:parser.error('CSV file and --dry-run apply only to import-csv')
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
