"""Fixed Binary2 analytic phase derivatives; periods per lens unit, not radians."""
import asyncio
import json
import math

import pytest
from tests.support.native import execute


def phase_reference(x, y, data_type, *, order=1, quadratic=.2, quartic=.1, norm=5):
    # Binary2: phi = m*(a2*rho**2 + a4*rho**4), radians.
    scale = order * (2*quadratic/norm**2 + 4*quartic*(x*x+y*y)/norm**4)/(2*math.pi)
    return {'PhaseSlopeX': scale*x, 'PhaseSlopeY': scale*y,
            'PhaseSlopeTangential': scale*math.hypot(x,y),
            'PhaseSlopeSagittal': 0, 'PhaseSlopeModulus': abs(scale)*math.hypot(x,y)}[data_type]


def points(result):
    for grid in result.get('grids', []):
        for iy, row in enumerate(grid['values']):
            for ix, value in enumerate(row):
                if value is not None:
                    yield grid['min_x']+ix*grid['dx'], grid['min_y']+iy*grid['dy'], value
    for series in result.get('series', []):
        for x, (y, value) in zip(series['x'], series['y'], strict=True):
            if value is not None:
                yield x, y, value


@pytest.mark.zemax
def test_surface_phase_slopes_binary2_reference():
    async def work(e):
        await e.model()
        await e.call('update_surfaces', dict(changes=[dict(surface=1,surface_type='Binary2',semi_diameter=5,replace_solves=True)]))
        await e.call('update_surfaces', dict(changes=[dict(surface=1,parameters={13:2},replace_solves=True)]))
        await e.call('update_surfaces', dict(changes=[dict(surface=1,radius='Infinity',
            parameters={**{i:0 for i in range(1,9)},13:2,14:5,15:.2,16:.1},replace_solves=True)]))
        source=str(e.folder/'binary2.zos')
        await e.call('save_lens_as', dict(path=source))
        await e.call('open_lens', dict(path=source))
        baseline=await e.call('get_surfaces',dict(request={}))
        records=[]
        for kind in ['surface_phase_slope','surface_phase_slope_cross']:
            for data_type in ['PhaseSlopeX','PhaseSlopeY','PhaseSlopeTangential','PhaseSlopeSagittal','PhaseSlopeModulus']:
                request=dict(kind=kind,surface=1,data_type=data_type)
                if kind.endswith('_cross'):
                    request['angle']=30
                result=await e.finish(await e.call('run_analysis',dict(request=request)))
                records.append(result)
                (e.folder/'phase-results.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                values=list(points(result));assert values
                for x,y,value in values:
                    e.check(kind+' '+data_type,value,phase_reference(x,y,data_type),atol=1e-8,rtol=1e-7)
                task_id=result['task']['task_id']
                if result.get('grids'):
                    page=await e.call('get_task_result',dict(task_id=task_id,grid=0,x_start=20,y_start=23,width=5,height=3))
                    assert page['grid']['values']==[r[20:25]for r in result['grids'][0]['values'][23:26]]
                else:
                    page=await e.call('get_task_result',dict(task_id=task_id,series=0,start=3,count=5))
                    assert page['series'][0]['y']==result['series'][0]['y'][3:8]
                await e.call('export_analysis_image',dict(request=dict(task_id=task_id,path=str(e.folder/f'{kind}_{data_type}.png'))))
                assert (await e.call('get_task_status',dict(task_id=task_id)))['close_attempted']
        assert await e.call('get_surfaces',dict(request={}))==baseline
        await e.call('update_surfaces',dict(changes=[dict(surface=1,parameters={15:-.2,16:-.1},replace_solves=True)]))
        for kind in ['surface_phase_slope','surface_phase_slope_cross']:
            for data_type in ['PhaseSlopeX','PhaseSlopeTangential','PhaseSlopeModulus']:
                result=await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,surface=1,data_type=data_type))))
                for x,y,value in points(result):
                    e.check(kind+' negative coefficient '+data_type,value,
                        phase_reference(x,y,data_type,quadratic=-.2,quartic=-.1),atol=1e-8,rtol=1e-7)
        # Pure power is independently removable; piston/tilt removal leaves this
        # rotationally symmetric even phase gradient unchanged.
        await e.call('update_surfaces',dict(changes=[dict(surface=1,parameters={15:.2,16:0},replace_solves=True)]))
        for kind in ['surface_phase_slope','surface_phase_slope_cross']:
            for removal in [dict(remove_power=True),dict(remove_piston=True,remove_tilt_x=True,remove_tilt_y=True)]:
                result=await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,surface=1,data_type='PhaseSlopeX',**removal))))
                for x,y,value in points(result):
                    expected=0 if removal.get('remove_power')else phase_reference(x,y,'PhaseSlopeX',quartic=0)
                    e.check(kind+' remove '+str(removal),value,expected,atol=1e-8,rtol=1e-7)
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Standard',radius=50,replace_solves=True)]))
        for kind in ['surface_phase_slope','surface_phase_slope_cross']:
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,surface=1))))
            for x,y,value in points(result):
                e.check(kind+' standard zero phase',value,0,atol=1e-8,rtol=1e-7)
    asyncio.run(execute('phase077',work))


@pytest.mark.zemax
def test_surface_phase_slopes_failure_cancel_recovery():
    async def work(e):
        import time
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Binary2',replace_solves=True)]))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,parameters={13:2},replace_solves=True)]))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,parameters={14:5,15:.2,16:.1},replace_solves=True)]))
        baseline=await e.call('get_surfaces',dict(request={}))
        records=[]
        for kind in ['surface_phase_slope','surface_phase_slope_cross']:
            error=await e.call('run_analysis',dict(request=dict(kind=kind,surface=999)),okay=False)
            assert error['error']['code']=='INDEX_OUT_OF_RANGE'
            sampling='S_1025x1025' if kind=='surface_phase_slope' else 'S_8193'
            task=await e.call('run_analysis',dict(request=dict(kind=kind,surface=1,sampling=sampling)))
            running=task['state']=='running'
            task=await e.call('cancel_task',dict(task_id=task['task_id']))
            deadline=time.monotonic()+60
            while task['state']not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02)
                task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']in {'succeeded','cancelled'} and task['close_attempted'],task
            records.append(dict(kind=kind,started_running=running,task=task))
            assert await e.call('get_surfaces',dict(request={}))==baseline
            await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,surface=1))))
        (e.folder/'cancellation.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('phase077_cancel',work))
