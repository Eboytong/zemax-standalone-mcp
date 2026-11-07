"""Record native point-image deviation without changing acceptance tolerance."""
import asyncio
import json
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,trace

@pytest.mark.zemax
def test_point_mtf_detector_grid_diagnostic():
    async def work(e):
        records=[]
        for nx,ny in [(7,5),(32,16)]:
            await setup(e,2)
            await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=10,ZCosine=1)),
                dict(object=2,object_type='DetectorRectangle',z=10,data=dict(NumberXPixels=nx,NumberYPixels=ny,XHalfWidth=1,YHalfWidth=2,PsfWaveNumber=0),type_settings=dict(UsePixelInterpolation=False))])
            await trace(e,f'point_{nx}_{ny}')
            baseline=await e.call('get_nsc_objects',dict(request={}))
            for database in [False,True]:
                request=dict(kind='nsc_geometric_mtf',detector=2)
                if database:request.update(path=str(e.folder/f'point_{nx}_{ny}.zrd'),filter='H2')
                result=await e.finish(await e.call('run_analysis',dict(request=request)))
                values=[abs(v-1)for curve in result['series']for row in curve['y']for v in row]
                records.append(dict(grid=[nx,ny],database=database,max_error=max(values),tolerance=2e-7,reference_passed=max(values)<=2e-7,points=len(values)))
                assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
                await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,count=3))
                await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/f'mtf_{nx}_{ny}_{database}.png'))))
                assert await e.call('get_nsc_objects',dict(request={}))==baseline
        (e.folder/'numerical-diagnostic.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        assert len(records)==4
    asyncio.run(execute('nsc_mtf064_diagnostic',work))
