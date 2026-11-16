import argparse
import json
from pathlib import Path
import subprocess
import sys

script_dir=Path(__file__).resolve().parent
root=next(p for p in script_dir.parents if (p/'src/zemax_mcp').is_dir())
sys.path.insert(0,str(root/'src'))
from zemax_mcp import __version__

parser=argparse.ArgumentParser(description='Show the current compatibility run status.')
parser.add_argument('--out',type=Path,default=(root/'.local'/f'v{__version__}-2026r1'
    if script_dir == root/'scripts/compatibility/2026r1' else script_dir))
out=parser.parse_args().out.resolve()
subprocess.run([sys.executable,'-X','utf8','-B',str(script_dir/'report.py'),'--out',str(out)],stdout=subprocess.DEVNULL,check=True)
s=json.loads((out/'summary.json').read_text(encoding='utf-8'))
print(json.dumps({k:s[k] for k in ('version','out','updated','native','modules_completed','tools_seen','analyses_seen','active')},ensure_ascii=False))
seen_path=out/'reported-failures.json'
seen=set(json.loads(seen_path.read_text()) if seen_path.exists() else [])
for row in s['failed_tests']+s['skipped_tests']:
    if row['test'] not in seen:
        reason=str(row['reason'])
        if 'AssertionError:' in reason:
            reason=reason.rsplit('AssertionError:',1)[1][:2500]
        else:
            reason=reason[-2500:]
        print(row['outcome'],row['test'],reason)
        seen.add(row['test'])
seen_path.write_text(json.dumps(sorted(seen)),encoding='utf-8')
