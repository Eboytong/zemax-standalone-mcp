"""Pure geometry subprocess. Native optical objects never cross this boundary."""
import json
import os
from pathlib import Path
import sys
import time


def run(request,progress=None):
    kind=request['kind']
    if kind=='surface_gaps':
        from .geometry_patches import measure_surface_gap
        measured=[]
        for r in request['requests']:
            try:measured.append(measure_surface_gap(r))
            except (ValueError,RuntimeError)as exc:measured.append(dict(id=r['id'],state='unverified',reason=str(exc)))
        return dict(measurements=measured)
    if kind=='step':
        from .geometry_kernel import check_step_entities
        return check_step_entities(request['entities'],relations=request.get('relations',[]),budget_seconds=request['budget_seconds'],progress=progress,gap_requests=request.get('gap_requests',[]))
    if kind=='mesh':
        from .geometry import check_meshes
        return check_meshes(request['meshes'],budget_seconds=request['budget_seconds'])
    if kind=='radial':
        from .geometry import check_radial_model
        return check_radial_model(request['fact'],request['faces'],request['scale_mm'],request['budget_seconds'])
    raise ValueError('unknown_geometry_computation')


def main():
    start=time.monotonic()
    output=Path(sys.argv[2])
    def partial(value):
        path=output.with_suffix('.partial.json');temp=path.with_suffix('.tmp')
        snapshot={**value,'state':'unverified','read_complete':False}
        temp.write_text(json.dumps(snapshot,ensure_ascii=False,allow_nan=False),encoding='utf-8')
        os.replace(temp,path)
    try:
        result=run(json.loads(Path(sys.argv[1]).read_text(encoding='utf-8')),partial)
    except Exception as exc:
        result=dict(state='unverified',read_complete=False,issues=[dict(code='geometry_process_error',reason=str(exc))])
    import win32api
    import win32process
    result['compute_telemetry']={'elapsed_seconds':time.monotonic()-start,
        'peak_working_set_bytes':win32process.GetProcessMemoryInfo(win32api.GetCurrentProcess())['PeakWorkingSetSize']}
    temp=output.with_suffix('.tmp')
    temp.write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    os.replace(temp,output)


if __name__=='__main__':
    main()
