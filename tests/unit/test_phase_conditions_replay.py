import importlib.util
import math
from pathlib import Path

import pytest


path=Path(__file__).resolve().parents[2]/'scripts/probes/PO-01/phase_conditions_replay.py'
spec=importlib.util.spec_from_file_location('phase_conditions_replay',path)
probe=importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def fixture():
    pupils=[(i-200)/200 for i in range(401)]
    comparisons=[]
    geometry=[]
    for section in ('sagittal','tangential'):
        points=[]
        for p in pupils:
            position=[0,p,.1*p*p]
            correction=position[2]/.8-(position[1]*.6+position[2]*.8)
            phase=.01*p*p
            points.append(dict(pupil=p,raw=math.remainder(phase-correction/.001,1.),
                               propagation_waves=0.,
                               native=0. if p==0 else -phase+.01*.005**2))
            geometry.append(dict(state='succeeded',position=position,
                            input=dict(px=p if section=='sagittal' else 0.,
                                       py=p if section=='tangential' else 0.)))
        comparisons.append(dict(section=section,component='y',indeterminate=0,points=points))
    case=dict(input=dict(name='synthetic',wavelength_um=1.),poll_states=dict(g1=['succeeded']),
              incident_direction=[0,.6,.8],geometry=[dict(index_before=1.)],
              settings={},phase_header={},comparisons=comparisons)
    calls=[dict(step='run_batch_ray_trace',arguments=dict(request=dict(target_surface=1)),
                reply=dict(data=dict(task_id='g1')))]
    # Source pages can be observed in a different order; pupil identity stays explicit.
    for start,end in ((401,802),(0,401)):
        calls.append(dict(step='get_task_result',arguments=dict(task_id='g1',start=start),
                          reply=dict(data=dict(rows=geometry[start:end]))))
    return dict(cases=[case],calls=calls)


def test_off_axis_replay_removes_known_ray_launch_term_from_geometry():
    result=probe.replay(fixture())[0]
    assert result['first_surface_geometry_task_id']=='g1'
    assert all(c['neighbor_candidate_passed'] for c in result['comparisons'])
    assert all(c['compared']==400 for c in result['comparisons'])


def test_native_error_survives_replay_without_reference_fitting():
    data=fixture()
    original=probe.replay(data)[0]['comparisons'][0]['neighbor_reference_waves']
    data['cases'][0]['comparisons'][0]['points'][0]['native']+=1e-5
    result=probe.replay(data)[0]['comparisons'][0]
    assert result['neighbor_reference_waves']==original
    assert not result['neighbor_candidate_passed']


@pytest.mark.parametrize('fault',['missing_task','failed_ray','duplicate_pupil','missing_page'])
def test_replay_rejects_missing_or_ambiguous_geometry(fault):
    data=fixture()
    if fault=='missing_task':
        data['calls'][0]['arguments']['request']['target_surface']=2
    elif fault=='failed_ray':
        data['calls'][1]['reply']['data']['rows'][0]['state']='error'
    elif fault=='duplicate_pupil':
        rows=data['calls'][2]['reply']['data']['rows']
        rows[0]['input']['px']=rows[1]['input']['px']
    else:
        data['calls'].pop()
    with pytest.raises(ValueError):
        probe.replay(data)
