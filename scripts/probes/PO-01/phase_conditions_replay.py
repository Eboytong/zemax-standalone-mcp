"""Test a local-Z launch phase prediction against retained off-axis controls."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from phase_reference_diagnostics import diagnose


def replay(data):
    output = []
    for case in data['cases']:
        if case.get('error'):
            output.append(dict(name=case['input']['name'], source_error=case['error']))
            continue
        task_ids = set(case['poll_states'])
        starts = [c['reply']['data']['task_id'] for c in data['calls']
                  if c['step']=='run_batch_ray_trace'
                  and c['arguments']['request'].get('target_surface')==1
                  and c['reply'].get('data',{}).get('task_id') in task_ids]
        if len(starts)!=1:
            raise ValueError('one first-surface geometry task is required per control')
        pages = sorted((c for c in data['calls'] if c['step']=='get_task_result'
                        and c['arguments']['task_id']==starts[0]),
                       key=lambda c:c['arguments'].get('start',0))
        rows = [row for page in pages for row in page['reply']['data']['rows']]
        if any(r['state']!='succeeded' for r in rows):
            raise ValueError('the geometry task must contain only successful rays')
        sections=list(dict.fromkeys(c['section'] for c in case['comparisons']))
        if len(rows)!=len(sections)*401:
            raise ValueError('the controlled first-surface geometry must contain 401 rays per fan')
        direction=case['incident_direction']
        index=case['geometry'][0]['index_before']
        wavelength=case['input']['wavelength_um']*.001
        if abs(direction[2])<=1e-12:
            raise ValueError('local-Z launch plane requires nonzero axial direction')
        differences=[index*(r['position'][2]/direction[2]
                            -sum(a*b for a,b in zip(r['position'],direction))) for r in rows]
        comparisons=[]
        for comparison in case['comparisons']:
            section=comparison['section']
            start=sections.index(section)*401
            coordinate='px' if section=='sagittal' else 'py'
            correction={r['input'][coordinate]:v for r,v in
                        zip(rows[start:start+401],differences[start:start+401])}
            if len(correction)!=401 or 0. not in correction:
                raise ValueError('first-surface rays must have unique pupil coordinates and a chief')
            chief=correction[0.]
            points=[dict(p,propagation_waves=p['propagation_waves']+
                         (correction[p['pupil']]-chief)/wavelength)
                    for p in comparison['points']]
            comparisons.append(diagnose(dict(comparison,points=points)))
        output.append(dict(name=case['input']['name'], phase_header=case['phase_header'],
                           actual_settings=case['settings'],
                           model_settings_preserved=case.get('model_settings_preserved'),
                           model_surfaces_preserved=case.get('model_surfaces_preserved'),
                           restoration=case.get('restoration'),
                           first_surface_geometry_task_id=starts[0],
                           launch_reference='n0*z_first/direction_z; actual ray travel from a common local-Z launch plane',
                           comparisons=comparisons))
    return output


def run(source,output):
    source,output=Path(source).resolve(),Path(output).resolve()
    data=json.loads(source.read_text(encoding='utf-8'))
    result=dict(source=str(source),new_native_session=False,cases=replay(data),
                source_close_receipt=data.get('close_receipt'))
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
    print(json.dumps([dict(name=c['name'],source_error=c.get('source_error'),
                    comparisons=[{k:v for k,v in x.items() if k!='points'}
                                 for x in c.get('comparisons',[])]) for c in result['cases']],
                    ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    args=parser.parse_args()
    run(args.source,args.output)
