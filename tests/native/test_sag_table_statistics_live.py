"""Distinguish SagTable slope sampling from radial-area weighting."""
import asyncio
import json

import numpy as np
import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('sign,minimum_radius',[(1,0),(-1,0),(1,1)])
def test_sag_table_high_order_slope_statistics(sign,minimum_radius):
    async def work(e):
        conditions = dict(model=f'EvenAspheric R={sign*40} conic-1 A4={sign*1e-5} A6={-sign*1e-8}, semi-diameter5mm',
            minimum_radius=minimum_radius,
            reference='analytic surface slope minus BFS slope at native BFSD curvature',
            fitting_scope='BFS curvature is native; this independently checks statistics, not the fit',
            hypotheses=['1000 equally spaced radial nodes including endpoints', 'radial area integral',
                '1000 intervals inclusive endpoints; radius-weighted RMS; rectangular volume sum'],
            summary_atol=1e-6, summary_rtol=1e-5,
            documentation='OpticStudio2024R2 Sag_Table_1:1000 equally spaced Y-points')
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',
            radius=sign*40,conic=-1,parameters={'2':sign*1e-5,'3':-sign*1e-8},semi_diameter=5,
            thickness=20,replace_solves=True)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function')
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='sag_table',surface=1,
            minimum_radius=minimum_radius,maximum_radius=5,samples=101))))
        sampling=result['statistics_sampling']['observed_reference']
        assert sampling['intervals']==1000 and sampling['nodes']==1001
        assert len(result['rows'])==101
        curvature=result['summary']['curvature']
        def difference(y):
            return sign*(y/40+4e-5*y**3-6e-8*y**5)-curvature*y/np.sqrt(1-(curvature*y)**2)
        points=np.linspace(minimum_radius,5,1000);delta=difference(points)
        fine=np.linspace(minimum_radius,5,200001);fine_delta=difference(fine)
        refs=dict(uniform_nodes=dict(maximum_slope_difference=float(np.max(abs(delta))),
            rms_slope_difference=float(np.sqrt(np.mean(delta**2)))),
            radial_area=dict(maximum_slope_difference=float(np.max(abs(fine_delta))),
            rms_slope_difference=float(np.sqrt(2*np.trapezoid(fine_delta**2*fine,fine)/(25-minimum_radius**2)))))
        right=minimum_radius+(5-minimum_radius)*np.arange(1001)/1000
        dr=(5-minimum_radius)/1000
        slope_delta=difference(right)
        depth=sign*(right**2/80+1e-5*right**4-1e-8*right**6)-curvature*right**2/(1+np.sqrt(1-(curvature*right)**2))-result['summary']['vertex_offset']
        refs['inclusive_endpoint_area']=dict(rms_slope_difference=float(np.sqrt(np.sum(slope_delta**2*right)/np.sum(right))),
            rms_removal_depth=float(np.sqrt(np.sum(depth**2*right)/np.sum(right))),
            removal_volume=float(2*np.pi*dr*np.sum(depth*right)))
        task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
        assert task['state']=='succeeded' and not task.get('cleanup_warnings')
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        (e.folder/'statistics.json').write_text(json.dumps(dict(result=result,references=refs,
            maximum_errors={name:{key:abs(result['summary'][key]-value)for key,value in values.items()}
                for name,values in refs.items()},task_status=task),ensure_ascii=False,indent=2),encoding='utf-8')
        # Capture lifecycle before any numerical rejection.
        await e.call('disconnect')
        for key,value in refs['inclusive_endpoint_area'].items():
            e.check('1000 intervals inclusive area '+key,result['summary'][key],value,
                atol=1e-5 if key=='removal_volume'else 1e-6,rtol=1e-5)
    asyncio.run(execute(f'sag518_statistics_{sign}_{minimum_radius}',work))
