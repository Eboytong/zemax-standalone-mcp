"""Prepared native path/critical/single-ray references; execute serially after startup recovery."""
import asyncio
from pathlib import Path
import pytest
from support.native import execute
from support.nsc import setup,update,trace

async def detector_model(e):
    await setup(e,2)
    await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=10,ZCosine=1)),dict(object=2,object_type='DetectorRectangle',z=10,data=dict(NumberXPixels=7,NumberYPixels=5))])

@pytest.mark.zemax
def test_path_flux_sequence_and_pagination():
    async def work(e):
        await detector_model(e);await trace(e,'path_reference')
        baseline=await e.call('get_nsc_objects',dict(request={}))
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='path_analysis',path=str(e.folder/'path_reference.zrd')))))
        assert result['rows'] and all(row['path_sequence']for row in result['rows'])
        e.check('path total input W',result['summary']['total_flux_in_w'],1,atol=1e-8,rtol=1e-7)
        e.check('path ending flux W',sum(x['flux_out_w']for x in result['rows']),1,atol=1e-8,rtol=1e-7)
        await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=0,count=1))
        assert (await e.call('get_nsc_objects',dict(request={})))==baseline
        await e.call('export_evaluation_report',dict(task_ids=[result['task']['task_id']],title='Native path reference'))
    asyncio.run(execute('paths027_flux',work))

@pytest.mark.zemax
def test_single_ray_reference_coordinates_and_database():
    async def work(e):
        await detector_model(e);baseline=await e.call('get_nsc_objects',dict(request={}))
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='nsc_single_ray_trace'))))
        hits=[r for r in result['rows']if r['hit_object']==2];assert hits
        for r in hits:
            for axis,expected in [('x',0),('y',0),('z',10),('l',0),('m',0),('n',1)]:
                e.check('single ray '+axis,r[axis],expected,atol=1e-8,rtol=1e-7)
        assert result['summary']['wave_index']==1 and not result['summary']['truncated']
        assert (await e.call('get_nsc_objects',dict(request={})))==baseline
        assert any(a['kind']=='zrd'for a in result['artifacts'])
        await e.call('get_task_result',dict(task_id=result['task']['task_id'],count=1))
    asyncio.run(execute('paths027_single',work))

@pytest.mark.zemax
def test_critical_controlled_pass_fail_and_model_restoration():
    async def work(e):
        await setup(e,1)
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(ZCosine=1))])
        path=e.folder/'controlled.CRS'
        # Official CRS format: count, units(mm=4), date, rayset(list=4), detector tilts.
        path.write_text('2 4 20261105 4 0 0 0\n0 0 0 0 0 1 .55 1 0 7 0 0 10 0 0 1\n0 0 0 0 0 1 .55 1 0 7 1 0 10 0 0 1\n',encoding='ascii')
        baseline=await e.call('get_nsc_objects',dict(request={}))
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='critical_ray_trace',path=str(path),position_tolerance=1e-5,angle_tolerance_deg=1e-5))))
        assert len(result['rows'])==2 and [x['passed']for x in result['rows']]==[True,False]
        for a,b in zip(result['rows'][0]['actual_position'],result['rows'][0]['target_position']):e.check('CRT target',a,b,atol=1e-8,rtol=1e-7)
        assert (await e.call('get_nsc_objects',dict(request={})))==baseline
    asyncio.run(execute('paths027_critical',work))
