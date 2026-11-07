import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Preserve completed stdio calls, numerical errors and saved output evidence."""
import argparse
import json
import shutil
from pathlib import Path

ROOT=PROJECT_ROOT


def snapshot(prefix,destination):
    destination=ROOT/destination
    destination.mkdir(parents=True,exist_ok=True)
    latest={}
    for folder in sorted((ROOT/'outputs/runs').glob(prefix+'*'),key=lambda p:p.stat().st_mtime):
        calls_file=folder/'calls.json'
        if not calls_file.is_file():continue
        calls=json.loads(calls_file.read_text(encoding='utf-8'))
        if not calls or calls[-1]['tool']!='disconnect' or not calls[-1]['response']['ok']:continue
        requests=[c['arguments']['request']for c in calls if c['tool']=='run_analysis']
        if not requests:continue
        key=json.dumps(requests,sort_keys=True)
        latest[key]=(folder,calls,requests)
    cases=[]
    for folder,calls,requests in latest.values():
        saved=destination/folder.name;saved.mkdir(exist_ok=True)
        shutil.copy2(folder/'calls.json',saved/'calls.json')
        shutil.copy2(folder/'checks.json',saved/'checks.json')
        checks=json.loads((folder/'checks.json').read_text(encoding='utf-8'))
        errors={}
        for check in checks:
            label=check['label'].split(' at ')[0].split(' reload=')[0]
            error=abs(check['actual']-check['expected'])
            errors[label]=max(errors.get(label,0),error)
        tasks=[c['response']['data']for c in calls if c['tool']=='get_task_status'and c['response']['ok']and c['response']['data']['state']in {'succeeded','failed','cancelled'}]
        outputs=[]
        for source in folder.rglob('*'):
            if source.is_file()and(source.suffix.lower()in {'.png','.cfg','.txt','.md'}or source.name in {'response.json','report-debug054.json'}):
                target=saved/source.relative_to(folder);target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target);outputs.append(target.relative_to(ROOT).as_posix())
        cases.append(dict(source=folder.relative_to(ROOT).as_posix(),requests=requests,
            evidence=saved.relative_to(ROOT).as_posix(),context=calls[0]['response']['context'],
            numerical_checks=len(checks),checks_passed=all(c['passed']for c in checks),maximum_absolute_errors=errors,
            terminal_tasks=tasks,disconnect=calls[-1]['response'],saved_outputs=outputs))
    report=dict(cases=cases,count=len(cases),source='completed real MCP stdio sessions; calls.json records actual settings, task result pages and final closure')
    (destination/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(cases),checks=sum(c['numerical_checks']for c in cases)),ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('prefix');parser.add_argument('destination')
    args=parser.parse_args();snapshot(args.prefix,args.destination)
