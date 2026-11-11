"""Current detector and ZRD display, non-square orientation and task ownership."""
import asyncio

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_detector_viewer_current_and_zrd_stdio():
    async def work(e):
        await e.call('new_system', dict(mode='NonSequential'))
        await e.call('insert_nsc_objects', dict(request=dict(at=1,count=1)))
        await e.call('update_nsc_objects', dict(request=dict(changes=[
            dict(object=1,object_type='SourceRay',x=1,y=-2,
                 data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1),replace_solves=True),
            dict(object=2,object_type='DetectorRectangle',z=10,
                 data=dict(XHalfWidth=2.5,YHalfWidth=3,NumberXPixels=5,NumberYPixels=3),replace_solves=True)])))
        zrd=e.folder/'viewer.zrd'
        await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(random_seed=42,save_zrd=str(zrd)))))
        baseline=await e.call('get_detector_data',dict(request=dict(detector=2,kind='flux',width=5,height=3)))
        assert baseline['nx']==5 and baseline['ny']==3
        assert sum(sum(row)for row in baseline['values'])==pytest.approx(1)
        before=await e.call('get_nsc_objects',dict(request=dict(start=1,count=2)))
        for source,scale,smoothing in [('current_detector','Linear',0),('current_detector','Log_Minus_5',2),
                                       ('zrd','Linear',0)]:
            request=dict(kind='detector_viewer',source=source,detector=2,scale=scale,smoothing=smoothing)
            if source=='zrd':request.update(path=str(zrd),filter='H2')
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            assert result['analysis_kind']=='detector_viewer'
            assert result['grids'] and result['grids'][0]['nx']==5 and result['grids'][0]['ny']==3
            if scale=='Linear':
                values=result['grids'][0]['values']
                if source=='current_detector':
                    assert result['grids'][0]['x_coordinates']==[-2,-1,0,1,2]
                    assert result['grids'][0]['y_coordinates']==[-2,0,2]
                for y in range(3):
                    for x in range(5):
                        # 5x6 mm / 15 pixels = 0.02 cm² per pixel.
                        e.check(f'{source} flux pixel {x},{y}', values[y][x]*.02, baseline['values'][y][x],
                                atol=1e-8,rtol=1e-6)
                page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,x_start=1,y_start=0,width=3,height=2))
                assert page['grid']['values']==[row[1:4]for row in values[:2]]
            terminal=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert terminal['close_attempted']
            await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/(source+scale+'.png')))))
            actual=await e.call('get_detector_data',dict(request=dict(detector=2,kind='flux',width=5,height=3)))
            assert actual['values']==baseline['values']
        # One-dimensional native export and empty accumulation are valid inputs.
        section=await e.finish(await e.call('run_analysis',dict(request=dict(kind='detector_viewer',
            detector=2,show_as='CrossSection_Row',row_col=1))))
        assert section['series'] or section['grids']
        invalid=await e.call('run_analysis',dict(request=dict(kind='detector_viewer',detector=1)),okay=False)
        assert invalid['error']['code'] in {'INVALID_DETECTOR','SETTING_REJECTED'}
        await e.call('clear_detectors',dict(request=dict(detector=2)))
        empty=await e.finish(await e.call('run_analysis',dict(request=dict(kind='detector_viewer',detector=2))))
        assert not empty.get('native_text_exported', True)
        assert sum(abs(v) for g in empty['grids'] for row in g['values'] for v in row)==0
        assert empty['grids'] or empty['empty_result']
        assert await e.call('get_nsc_objects',dict(request=dict(start=1,count=2)))==before
        await e.call('update_nsc_objects',dict(request=dict(changes=[
            dict(object=1,x=0,y=0),
            dict(object=2,object_type='DetectorPolar',z=0,material='ABSORB',
                 data=dict(MaxAngle=180,RadialSize=10,NumberPPixels=11,NumberAPixels=36),replace_solves=True)])))
        await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(random_seed=42))))
        angular=await e.finish(await e.call('run_analysis',dict(request=dict(kind='detector_viewer',
            detector=2,data_type='Polar_AngleSpace'))))
        assert angular['grids'] or angular['series']
        assert angular['detector_viewer']['detector_type']=='DetectorPolar'
        pending=await e.call('run_analysis',dict(request=dict(kind='detector_viewer',
            detector=2,data_type='Polar_AngleSpace')))
        await e.call('cancel_task',dict(task_id=pending['task_id']))
        terminal=await e.call('get_task_status',dict(task_id=pending['task_id']))
        for _ in range(200):
            if terminal['state'] in {'succeeded','cancelled','failed'}:break
            await asyncio.sleep(.05)
            terminal=await e.call('get_task_status',dict(task_id=pending['task_id']))
        assert terminal['state'] in {'succeeded','cancelled'} and terminal['close_attempted']


    async def guarded(e):
        try:
            await work(e)
        finally:
            await e.call('disconnect')
    asyncio.run(execute('detector_viewer_native',guarded))
