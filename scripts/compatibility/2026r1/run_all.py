"""Run all native test modules serially in isolated processes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
env = os.environ.copy()
env.update(PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1',ZEMAX_INSTALL_DIR=r'C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio',
    PYTHONPATH=os.pathsep.join([str(OUT),str(ROOT/'src'),str(ROOT)]), MPLCONFIGDIR=str(OUT/'matplotlib'),
    ZEMAX_STATE_DIR=str(OUT/'state'))
files = [str(p.relative_to(ROOT)).replace('\\','/') for p in sorted((ROOT/'tests/native').glob('test_*.py'))]
if sys.argv[1:]==['--retry-pending']:
    collected=json.loads((OUT/'collected-tests.json').read_text(encoding='utf-8'))
    retry_plan=json.loads((OUT/'retry-plan.json').read_text(encoding='utf-8'))
    plan=set(retry_plan['modules'])
    latest={}
    for line in (OUT/'test-results.jsonl').read_text(encoding='utf-8').splitlines():
        row=json.loads(line);latest[row['test']]=row['outcome']
    files=[t for t in collected if t.startswith('tests/native/') and t not in retry_plan.get('exclude',[]) and
        (t not in latest or (t.split('::')[0] in plan and latest[t]=='failed'))]
elif len(sys.argv)>1:
    files=sys.argv[1:]
(OUT/'logs').mkdir(exist_ok=True)
(OUT/'xml').mkdir(exist_ok=True)
(OUT/'tmp').mkdir(exist_ok=True)
for index,target in enumerate(files,1):
    relative,separator,selection=target.partition('::')
    path=ROOT/relative
    selector=str(path)+(separator+selection if separator else '')
    basename=path.stem+(f'_case{index}' if separator else '')
    name = basename
    attempt=1
    while (OUT/'logs'/f'{name}.log').exists():
        attempt+=1
        name=f'{basename}_attempt{attempt}'
    started = time.time()
    print(f'[{index}/{len(files)}] {name} START',flush=True)
    command = [sys.executable,'-X','utf8','-B','-m','pytest',selector,'--run-zemax','-vv','--tb=short','-r','a',
        '-p','no:cacheprovider','-p','compat_plugin','--basetemp',str(OUT/'tmp'/name),'--junitxml',str(OUT/'xml'/f'{name}.xml')]
    with (OUT/'logs'/f'{name}.log').open('w',encoding='utf-8') as log:
        process = subprocess.Popen(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        (OUT/'active.json').write_text(json.dumps(dict(module=str(path.relative_to(ROOT)),pid=process.pid,start=started,index=index,total=len(files))),encoding='utf-8')
        try:
            limit=int(os.environ.get('ZEMAX_TEST_MODULE_TIMEOUT','3600'))
            code = process.wait(timeout=limit)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
            code = f'timeout_{limit}s'
    result = dict(module=str(path.relative_to(ROOT)),selector=target,exit_code=code,seconds=time.time()-started,attempt=attempt)
    with (OUT/'module-results.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps(result)+'\n')
    print(f'[{index}/{len(files)}] {name} END {code} {result["seconds"]:.1f}s',flush=True)
(OUT/'active.json').write_text(json.dumps(dict(state='finished',time=time.time())),encoding='utf-8')
