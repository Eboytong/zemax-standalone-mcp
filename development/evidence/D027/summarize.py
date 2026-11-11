"""Summarize observed integration results, native equality and retrieval."""
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from tests.support.disclosure_cases import run_case
from tests.support.native import Evidence
from development.evidence.D027.compare import signatures
from zemax_mcp.capability_index import search


def equal(a,b,path='root',errors=None):
    if errors is None:errors=[]
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        if abs(a-b)>1e-8+1e-7*abs(a):errors.append(dict(path=path,full=a,compact=b))
    elif isinstance(a,dict) and isinstance(b,dict):
        if a.keys()!=b.keys():errors.append(dict(path=path,error='keys'))
        for key in a.keys()&b.keys():equal(a[key],b[key],path+'.'+key,errors)
    elif isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b):errors.append(dict(path=path,error='length'))
        for i,(x,y) in enumerate(zip(a,b)):equal(x,y,path+f'[{i}]',errors)
    elif a!=b:errors.append(dict(path=path,full=a,compact=b))
    return errors


def main():
    folder=ROOT/'.local/evidence/development/D027'
    records=json.loads((folder/'comparison.json').read_text(encoding='utf-8'))['cases']
    cases=json.loads((ROOT/'development/evidence/D023/end_to_end.json').read_text(encoding='utf-8'))
    checks=[]
    for c in cases:
        values=[]
        for mode in ['full','compact']:
            calls=json.loads((folder/(c['id']+'-'+mode)/'calls.json').read_text(encoding='utf-8'))
            values.append(signatures(calls))
        errors=equal(*values)
        checks.append(dict(case=c['id'],passed=not errors,errors=errors[:10]))
    queries=json.loads((ROOT/'development/evidence/D023/tasks.json').read_text(encoding='utf-8'))
    retrieval=[]
    for c in queries:
        found=[x['capability_id'] for x in search(c['query'])['items']]
        retrieval.append(dict(id=c['id'],passed=bool(set(found)&set(c['expected'])) if c['expected'] else not found,found=found))
    modes={}
    for mode in ['full','compact']:
        selected=[r for r in records if r['mode']==mode]
        times=sorted(r['elapsed_seconds'] for r in selected)
        modes[mode]=dict(passed=sum(r['passed'] for r in selected),total=len(selected),
            median_seconds=statistics.median(times),p95_seconds=times[math.ceil(.95*len(times))-1],
            catalog_bytes=max(r['catalog_bytes'] for r in selected),model_tokens=None)
    report=dict(modes=modes,protocol_native_equivalence=checks,retrieval_passed=sum(r['passed'] for r in retrieval),
        retrieval_total=len(queries),retrieval=retrieval,agent_inference='not observed; deterministic integration only',
        host_native_discovery='available in current Codex host; no controllable independent prompt/usage capture',
        subagent_experiment='not run: parent+child model usage not observable; no demonstrated routing advantage',
        default_mode='full',decision='Keep compatible full default; compact opt-in for clients loading whole catalogs. Token threshold not observed.')
    path=ROOT/'development/evidence/D027/summary.json'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['modes','retrieval_passed','retrieval_total','default_mode']},ensure_ascii=False))
    assert len(records)==24 and all(r['passed'] for r in records),records
    assert all(c['passed'] for c in checks),[c for c in checks if not c['passed']]
    assert report['retrieval_passed']>=57

if __name__=='__main__':main()
