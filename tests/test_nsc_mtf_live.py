"""Prepared native point-detector MTF and ZRD replay reference."""
import asyncio
import cmath
import json
import math
import pytest
from support.native import execute
from support.nsc import setup,update,trace

@pytest.mark.zemax
@pytest.mark.parametrize('database',[False,True])
def test_nsc_point_detector_geometric_mtf(database):
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=10,ZCosine=1)),dict(object=2,object_type='DetectorRectangle',z=10,data=dict(NumberXPixels=7,NumberYPixels=5,XHalfWidth=1,YHalfWidth=2,PsfWaveNumber=0))])
        await trace(e,'mtf_point')
        q=dict(kind='nsc_geometric_mtf',detector=2,frequencies=[0,.625/299,.1,.3,.625])
        if database:q.update(path=str(e.folder/'mtf_point.zrd'),filter='H2')
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert result['series'] and result['frequency_unit']=='cycles/mm'
        e.check('rectangular Nyquist cycles/mm',result['detector_sampling']['nyquist_cycles_per_mm'],.625,atol=1e-12,rtol=1e-12)
        for curve in result['series']:
            for values in curve['y']:
                for value in values:e.check('single occupied detector pixel MTF',value,1,atol=1e-7,rtol=1e-7)
        await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,count=3))
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'nsc-mtf.png'))))
    asyncio.run(execute('illumination028_mtf',work))


@pytest.mark.zemax
def test_nsc_point_detector_mtf_dft_diagnostic():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=10,ZCosine=1)),dict(object=2,object_type='DetectorRectangle',z=10,data=dict(NumberXPixels=7,NumberYPixels=5,XHalfWidth=1,YHalfWidth=2,PsfWaveNumber=0))])
        await trace(e,'mtf_dft_point')
        detector=await e.call('get_detector_data',dict(request=dict(detector=2,kind='flux',width=7,height=5)))
        matrix=detector['values']
        total=sum(map(sum,matrix))
        assert total>0
        nx,ny=detector['nx'],detector['ny'];dx,dy=2/ nx,4/ ny
        x=[(i-(nx-1)/2)*dx for i in range(nx)];y=[(j-(ny-1)/2)*dy for j in range(ny)]
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='nsc_geometric_mtf',detector=2))))
        refs=[]
        for curve in result['series']:
            for frequency,values in zip(curve['x'],curve['y'],strict=True):
                for label,actual in zip(curve['labels'],values,strict=True):
                    axis='x' if label.casefold().startswith(('x','sagittal')) else 'y'
                    coords=x if axis=='x' else y
                    reference=abs(sum(matrix[j][i]*cmath.exp(-2j*math.pi*frequency*coords[i if axis=='x' else j])
                                      for j in range(ny) for i in range(nx)))/total
                    refs.append(dict(label=label,frequency=frequency,native=actual,reference=reference,error=abs(actual-reference)))
        record=dict(detector=detector,curves=result['series'],reference=refs,
                    axis_hypothesis='Tangential=detector Y; Sagittal=detector X; point image cannot distinguish axes',
                    maximum_error=max((v['error']for v in refs),default=None),
                    native_messages=result.get('native_messages'),native_text=result.get('native_text'))
        (e.folder/'mtf-dft-diagnostic.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('nsc_mtf_dft_diagnostic',work))


@pytest.mark.zemax
def test_nsc_asymmetric_detector_mtf_dft_diagnostic():
    """Separate axis assignment and native interpolation from point normalization."""
    async def work(e):
        await setup(e,4)
        cases=[('x',[(0,0,.25),(4/7,0,.75)]),
               ('y',[(0,0,.25),(0,1.6,.75)]),
               ('asymmetric',[(-4/7,-.8,.2),(0,0,.3),(4/7,1.6,.5)])]
        records=[]
        for name,sources in cases:
            changes=[dict(object=i,object_type='SourceRay',x=x,y=y,
                          data=dict(NumberOfAnalysisRays=10,Power=power,ZCosine=1))
                     for i,(x,y,power) in enumerate(sources,1)]
            if len(sources)<3:
                changes.append(dict(object=3,object_type='SourceRay',x=3,y=3,
                                    data=dict(NumberOfAnalysisRays=1,Power=.1,ZCosine=1)))
            changes.append(dict(object=4,object_type='DetectorRectangle',z=10,
                data=dict(NumberXPixels=7,NumberYPixels=5,XHalfWidth=1,YHalfWidth=2,PsfWaveNumber=0)))
            await update(e,changes)
            await trace(e,'mtf_dft_'+name)
            detector=await e.call('get_detector_data',dict(request=dict(detector=4,kind='flux',width=7,height=5)))
            matrix=detector['values'];total=sum(map(sum,matrix))
            e.check(name+' detector input W',total,1,atol=1e-8,rtol=1e-7)
            nx,ny=detector['nx'],detector['ny']
            coordinates=dict(x=[(i-(nx-1)/2)*2/nx for i in range(nx)],
                             y=[(j-(ny-1)/2)*4/ny for j in range(ny)])
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='nsc_geometric_mtf',detector=4))))
            comparisons=[]
            for curve in result['series']:
                for frequency,values in zip(curve['x'],curve['y'],strict=True):
                    for label,actual in zip(curve['labels'],values,strict=True):
                        refs={axis:abs(sum(matrix[j][i]*cmath.exp(-2j*math.pi*frequency*coords[i if axis=='x' else j])
                                          for j in range(ny) for i in range(nx)))/total
                              for axis,coords in coordinates.items()}
                        comparisons.append(dict(label=label,frequency=frequency,native=actual,
                            reference=refs,error={axis:abs(actual-value) for axis,value in refs.items()}))
            labels=result['series'][0]['labels']
            errors={label:{axis:max(r['error'][axis] for r in comparisons if r['label']==label)
                           for axis in coordinates} for label in labels}
            task=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
            assert task['state']=='succeeded' and task['close_attempted'] and not task.get('cleanup_warnings')
            records.append(dict(case=name,requested_sources=sources,detector=detector,result=result,
                                axis_maximum_errors=errors,comparison=comparisons,task=task))
            (e.folder/'asymmetric-dft.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            endpoints=[]
            for maximum in [.625/299,.1,.3]:
                endpoint=await e.finish(await e.call('run_analysis',dict(request=dict(
                    kind='nsc_geometric_mtf',detector=4,maximum_frequency=maximum))))
                for curve in endpoint['series']:
                    frequency=curve['x'][-1]
                    e.check(name+' requested frequency endpoint',frequency,maximum,atol=1e-12,rtol=1e-12)
                    for label,value in zip(curve['labels'],curve['y'][-1],strict=True):
                        axis='x' if label=='Sagittal' else 'y';coords=coordinates[axis]
                        reference=abs(sum(matrix[j][i]*cmath.exp(-2j*math.pi*frequency*coords[i if axis=='x' else j])
                                          for j in range(ny) for i in range(nx)))/total
                        e.check(name+' exact endpoint '+label,value,reference,atol=1e-7,rtol=1e-7)
                        endpoints.append(dict(requested_maximum=maximum,label=label,native=value,
                                              reference=reference,error=abs(value-reference)))
                status=await e.call('get_task_status',dict(task_id=endpoint['task']['task_id']))
                assert status['close_attempted'] and not status.get('cleanup_warnings')
            records[-1]['endpoint_probes']=endpoints
            (e.folder/'asymmetric-dft.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        # This experiment records both axis hypotheses; numerical acceptance remains separate.
    asyncio.run(execute('nsc_mtf491_asymmetric',work))
