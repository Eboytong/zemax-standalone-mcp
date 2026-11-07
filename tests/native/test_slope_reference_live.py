"""Predeclared analytic derivative reference and axis-orientation diagnostics."""
import asyncio,json,math
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_surface_slope_sphere_reference():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,semi_diameter=5,replace_solves=True)]))
        source=str(e.folder/'sphere.zos');await e.call('save_lens_as',dict(path=source));await e.call('open_lens',dict(path=source))
        baseline=await e.call('get_surfaces',dict(request={}))
        records=[]
        for kind in ['surface_slope','surface_slope_cross']:
            for data in ['XSlope','YSlope','SlopeModulus','TangentialSlope','SagittalSlope']:
                q=dict(kind=kind,surface=1,data_type=data)
                if kind.endswith('_cross'):q['angle']=30
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                records.append(result)
                (e.folder/'reference.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                if kind=='surface_slope':
                    g=result['grids'][0]
                    comparisons=[]
                    for iy,row in enumerate(g['values']):
                        for ix,v in enumerate(row):
                            if v is None:continue
                            x=g['min_x']+ix*g['dx'];y=g['min_y']+iy*g['dy']
                            den=math.sqrt(2500-x*x-y*y);r=math.hypot(x,y)
                            expected={'XSlope':x/den,'YSlope':y/den,'SlopeModulus':r/den,'TangentialSlope':r/den,'SagittalSlope':0}[data]
                            comparisons.append(dict(x=x,y=y,value=v,expected=expected))
                    (e.folder/(data+'-comparisons.json')).write_text(json.dumps(comparisons,indent=2),encoding='utf-8')
                    for row in comparisons:e.check(kind+' '+data,row['value'],row['expected'],atol=1e-8,rtol=1e-7)
                else:
                    assert result['series']
                    for series in result['series']:
                        for x,(y,v)in zip(series['x'],series['y']):
                            if v is None:continue
                            den=math.sqrt(2500-x*x-y*y);r=math.hypot(x,y)
                            expected={'XSlope':x/den,'YSlope':y/den,'SlopeModulus':r/den,'TangentialSlope':r/den,'SagittalSlope':0}[data]
                            e.check(kind+' '+data,v,expected,atol=1e-8,rtol=1e-7)
                            e.check('30 degree section Y coordinate',y,x*math.tan(math.pi/6),atol=1e-10,rtol=1e-7)
                taskid=result['task']['task_id']
                if kind=='surface_slope':
                    page=await e.call('get_task_result',dict(task_id=taskid,grid=0,x_start=27,y_start=19,width=5,height=3))
                    assert page['grid']['values']==[r[27:32]for r in result['grids'][0]['values'][19:22]]
                else:
                    page=await e.call('get_task_result',dict(task_id=taskid,series=0,start=3,count=5))
                    assert page['series'][0]['y']==result['series'][0]['y'][3:8]
                await e.call('export_analysis_image',dict(request=dict(task_id=taskid,path=str(e.folder/f'{kind}_{data}.png'))))
                assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
        assert await e.call('get_surfaces',dict(request={}))==baseline
        for radius,conic,removal in [(0,0,'None'),(50,0,'BaseROC'),(50,-.5,'None'),(-50,-.5,'None')]:
            await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=radius,conic=conic,replace_solves=True)]))
            current=await e.call('get_surfaces',dict(request={}))
            for kind in ['surface_slope','surface_slope_cross']:
                q=dict(kind=kind,surface=1,data_type='XSlope',remove_option=removal)
                if kind.endswith('_cross'):q['angle']=30
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                points=[]
                if result.get('grids'):
                    g=result['grids'][0]
                    points=[(g['min_x']+ix*g['dx'],g['min_y']+iy*g['dy'],v)for iy,row in enumerate(g['values'])for ix,v in enumerate(row)if v is not None]
                else:
                    points=[(x,row[0],row[1])for s in result['series']for x,row in zip(s['x'],s['y'])if row[1]is not None]
                for x,y,v in points:
                    expected=0 if radius==0 or removal=='BaseROC'else x/(radius*math.sqrt(1-(1+conic)*(x*x+y*y)/(radius*radius)))
                    e.check(f'{kind} R={radius} k={conic} remove={removal}',v,expected,atol=1e-8,rtol=1e-7)
                assert await e.call('get_surfaces',dict(request={}))==current
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,conic=0,replace_solves=True)]))
        for kind in ['surface_slope','surface_slope_cross']:
            for criterion in ['MinimumVolume','MinimumRMS','MinimumRMSWithOffset']:
                result=await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,surface=1,data_type='XSlope',remove_option='BestFitSphere',best_fit_sphere=criterion))))
                values=[v for g in result.get('grids',[])for row in g['values']for v in row if v is not None]
                values.extend(row[1]for s in result.get('series',[])for row in s['y']if row[1]is not None)
                for v in values:e.check(kind+' best-fit sphere '+criterion,v,0,atol=1e-8,rtol=1e-7)
    asyncio.run(execute('slopes075',work))


@pytest.mark.zemax
def test_surface_slopes_failure_cancel_recovery():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,replace_solves=True)]))
        baseline=await e.call('get_surfaces',dict(request={}))
        records=[]
        for kind in ['surface_slope','surface_slope_cross']:
            invalid=await e.call('run_analysis',dict(request=dict(kind=kind,surface=999)),okay=False)
            assert invalid['error']['code']=='INDEX_OUT_OF_RANGE'
            request=dict(kind=kind,surface=1,sampling='S_1025x1025'if kind=='surface_slope'else'S_8193')
            task=await e.call('run_analysis',dict(request=request))
            started=task['state']=='running'
            task=await e.call('cancel_task',dict(task_id=task['task_id']))
            import time
            deadline=time.monotonic()+60
            while task['state']not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']in {'succeeded','cancelled'} and task['close_attempted'],task
            records.append(dict(kind=kind,started_running=started,task=task))
            assert await e.call('get_surfaces',dict(request={}))==baseline
            await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,surface=1))))
        (e.folder/'cancellation.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('slopes075_cancel',work))
