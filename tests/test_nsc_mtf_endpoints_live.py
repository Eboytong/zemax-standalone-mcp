"""Native frequency endpoint queries against independent detector Fourier sums."""
import asyncio
import cmath
import json
import math
import time

import pytest
from support.native import execute
from support.nsc import setup,update,trace


@pytest.mark.zemax
@pytest.mark.parametrize('database',[False,True])
@pytest.mark.parametrize('shape',['point','asymmetric'])
def test_nsc_mtf_requested_frequency_endpoints(database,shape):
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(
            reference='Normalized discrete Fourier magnitude of independently read7x5 pixel powers; T=Y,S=X',
            source='SourceRay objects with1W detected at pixel centers',shape=shape,
            atol=1e-7,rtol=1e-7,database=database),indent=2),encoding='utf-8')
        await setup(e,4)
        sources=([(-4/7,-.8,.2),(0,0,.3),(4/7,1.6,.5)]if shape=='asymmetric'else
                 [(0,0,1),(3,3,.1),(3,3,.1)])
        await update(e,[dict(object=i,object_type='SourceRay',x=x,y=y,
            data=dict(NumberOfAnalysisRays=10,Power=p,ZCosine=1))for i,(x,y,p)in enumerate(sources,1)]+[
            dict(object=4,object_type='DetectorRectangle',z=10,
                data=dict(NumberXPixels=7,NumberYPixels=5,XHalfWidth=1,YHalfWidth=2,PsfWaveNumber=0))])
        # Prepare native spectral-table defaults before establishing the reload baseline.
        prepared=str(e.folder/'prepared-model.zos')
        await e.call('save_lens_as',dict(path=prepared));await e.call('open_lens',dict(path=prepared))
        await trace(e,'endpoint_input')
        detector=await e.call('get_detector_data',dict(request=dict(detector=4,kind='flux',width=7,height=5)))
        before=await e.call('get_nsc_objects',dict(request={}));settings=await e.call('get_system_settings')
        frequencies=[0,.625/299,.037,.1,.211,.3,.499,.625]
        q=dict(kind='nsc_geometric_mtf',detector=4,frequencies=frequencies)
        if database:q.update(path=str(e.folder/'endpoint_input.zrd'),filter='H4')
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert result['frequency_sampling']=='native_frequency_endpoints'
        assert len(result['rows'])==len(frequencies)
        comparisons=[];matrix=detector['values'];total=sum(map(sum,matrix))
        e.check('detector input W',total,1,atol=1e-8,rtol=1e-7)
        for query,frequency in zip(result['native_queries'],frequencies,strict=True):
            assert query['actual_settings']['MaximumFrequency']==frequency
            child=await e.call('get_task_status',dict(task_id=query['child_task_id']))
            assert child['state']=='succeeded'and child['close_attempted']and not child.get('cleanup_warnings'),child
        for curve in result['series']:
            assert curve['x']==frequencies
            for frequency,values in zip(curve['x'],curve['y'],strict=True):
                for label,actual in zip(curve['labels'],values,strict=True):
                    assert label in {'Tangential','Sagittal'}
                    reference=abs(sum(matrix[j][i]*cmath.exp(-2j*math.pi*frequency*(
                        (i-3)*2/7 if label=='Sagittal'else(j-2)*4/5))for j in range(5)for i in range(7)))/total
                    comparisons.append(dict(frequency=frequency,label=label,native=actual,
                        reference=reference,error=abs(actual-reference)))
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=2,count=3))
        assert page['rows']==result['rows'][2:5]
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],
            path=str(e.folder/'endpoint-mtf.png'))))
        assert await e.call('get_nsc_objects',dict(request={}))==before and await e.call('get_system_settings')==settings
        # Cancel a long frequency series while a child is active, then reuse the detector.
        long=await e.call('run_analysis',dict(request=q|dict(frequencies=[i*.625/300 for i in range(301)])))
        deadline=time.monotonic()+60
        while not long.get('active_step'):
            assert time.monotonic()<deadline and long['state']=='running',long
            await asyncio.sleep(.02);long=await e.call('get_task_status',dict(task_id=long['task_id']))
        long=await e.call('cancel_task',dict(task_id=long['task_id']))
        while long['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);long=await e.call('get_task_status',dict(task_id=long['task_id']))
        assert long['state']=='cancelled',long
        cancelled=await e.call('get_task_result',dict(task_id=long['task_id']))
        if long.get('active_step'):
            child=await e.call('get_task_status',dict(task_id=long['active_step']['task_id']))
            assert child['state']in {'succeeded','cancelled'}and child['close_attempted'],child
        rerun=await e.finish(await e.call('run_analysis',dict(request=q|dict(frequencies=[0,.1]))))
        assert rerun['series'][0]['y']==result['series'][0]['y'][:1]+result['series'][0]['y'][3:4]
        assert await e.call('get_nsc_objects',dict(request={}))==before and await e.call('get_system_settings')==settings
        model_path=str(e.folder/'endpoint-model.zos')
        await e.call('save_lens_as',dict(path=model_path));await e.call('open_lens',dict(path=model_path))
        assert await e.call('get_nsc_objects',dict(request={}))==before
        assert await e.call('get_system_settings')==settings
        if not database:await trace(e,'endpoint_reloaded')
        reloaded=await e.finish(await e.call('run_analysis',dict(request=q|dict(frequencies=[0,.1]))))
        assert reloaded['series'][0]['y']==rerun['series'][0]['y']
        (e.folder/'endpoint-reference.json').write_text(json.dumps(dict(result=result,detector=detector,
            comparison=comparisons,cancelled=cancelled,rerun=rerun,reloaded=reloaded),ensure_ascii=False,indent=2),encoding='utf-8')
        await e.call('disconnect')
        for row in comparisons:e.check(row['label']+' endpoint '+str(row['frequency']),
            row['native'],row['reference'],atol=1e-7,rtol=1e-7)
    asyncio.run(execute('nsc562_endpoints_'+shape+'_'+str(database),work))
