"""Geometric line/edge outlets for a controlled defocused circular pupil."""
import asyncio
import json
import numpy as np

import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('sampling,radius',[('S_256x256',10),('S_1024x1024',20)])
def test_geometric_spread_controlled_outlets(sampling,radius):
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(
            line_atol=.03,edge_atol=.01,
            reference='uniform circular pupil imaged by focal100 paraxial lens at distance100.1; image disk radius5 micrometers',
            analytic='line peak-normalized sqrt(1-u^2); edge .5+(asin(u)+u*sqrt(1-u^2))/pi'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',parameters={'1':100},
            thickness=100.1,semi_diameter=5,is_stop=True,replace_solves=True)]))
        records=[]
        for kind in ['LineEdge','Line','Edge']:
            request=dict(kind='geometric_line_edge_spread',sampling=sampling,radius_maximum=radius,data_type=kind)
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            records.append(dict(request=request,result=result))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert status['state']=='succeeded' and status['close_attempted']
            if sampling=='S_1024x1024':
                series=result['series'][0];x=np.asarray(series['x']);values=np.asarray(series['y'])
                u=np.clip(x/5,-1,1)
                expected_line=np.sqrt(1-u*u)
                expected_edge=.5+(np.arcsin(u)+u*np.sqrt(1-u*u))/np.pi
                for line,edge,label in [(0,1,'X'),(2,3,'Y')]:
                    e.check(kind+' '+label+' circular-pupil LSF',float(abs(values[:,line]-expected_line).max()),0,atol=.03,rtol=0)
                    e.check(kind+' '+label+' circular-pupil ESF',float(abs(values[:,edge]-expected_edge).max()),0,atol=.01,rtol=0)
    asyncio.run(execute('geometric_spread322',work))
