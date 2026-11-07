"""Native parameter paths for installed, source-backed NSC DLL candidates."""
import asyncio,json
import math
import pytest
from support.native import execute
from support.nsc import setup,update

OBJECTS=['CoatingSample.DLL','DiffractionGrating.DLL','EllipticalVolume.DLL','HalfCylinder.DLL']
SOURCES=['Cone.dll','fiber1.DLL','Lambertian_Overfill.dll']
BULK=['bulk_samp_1.DLL','Henyey-Greenstein-bulk.DLL','poly_bulk_scat.DLL','Rayleigh.DLL']


@pytest.mark.zemax
@pytest.mark.parametrize('category,name',[(c,n)for c,ns in [('object',OBJECTS),('source',SOURCES),('bulk',BULK)]for n in ns])
def test_source_backed_dll_native_parameters(category,name):
    async def work(e):
        await setup(e,1)
        change=dict(object=1)
        if category=='bulk':
            change.update(object_type='RectangularVolume',material='N-BK7',data=dict(X1HalfWidth=10,Y1HalfWidth=10,X2HalfWidth=10,Y2HalfWidth=10,ZLength=1),
                volume=dict(model='DLLDefinedScattering',settings=dict(DLL=name,MeanPath=2)))
        else:change.update(object_type='SourceDLL'if category=='source'else'UserDefinedObject',file1=name)
        await update(e,[change])
        before=await e.call('get_nsc_objects',dict(request=dict(start=1,count=1,parameter_count=250)))
        path=e.folder/'dll.zos';await e.call('save_lens_as',dict(path=str(path)));await e.call('open_lens',dict(path=str(path)))
        after=await e.call('get_nsc_objects',dict(request=dict(start=1,count=1,parameter_count=250)))
        if category=='bulk':assert after['rows'][0]['volume']['settings']['DLL']==name
        else:assert after['rows'][0]['file1']==name
        (e.folder/'dll-parameter-reference.json').write_text(json.dumps(dict(category=category,name=name,before=before,after=after,
            status='native_parameter_and_reload_only',numeric_status='requires_source_specific_ray_reference'),indent=2),encoding='utf-8')
    asyncio.run(execute('adaptation_dll_'+name.replace('.','_'),work))


@pytest.mark.zemax
@pytest.mark.parametrize('name',SOURCES)
def test_source_dll_distribution_native(name):
    from support.nsc import trace,detector
    async def work(e):
        await setup(e,2)
        # Formulae and six-standard-error budgets are fixed before tracing.
        if name=='Cone.dll':
            parameters={6:2,7:1,8:1,9:1,10:10,11:30,12:0,13:360,14:1}
            low,high=math.cos(math.radians(30)),math.cos(math.radians(10));power=high-low
        elif name=='fiber1.DLL':
            parameters={6:1,7:1,8:0,9:0,10:.2,11:0,12:0}
            low,high=math.sqrt(1-.2**2),1;power=1
        else:
            parameters={6:0,7:0,8:1,9:2,10:10,11:1}
            low,high=10/math.sqrt(101),1;power=1-low
        await update(e,[dict(object=1,object_type='SourceDLL',file1=name,parameters={1:0,2:10000,3:1,**parameters}),
            dict(object=2,object_type='DetectorPolar',material='ABSORB',data=dict(RadialSize=20,MaxAngle=180,NumberPPixels=37,NumberAPixels=36))])
        result,segments=await trace(e,'source',max_segments=30000)
        hits=[r for r in segments if r['HitObject']==2];assert len(hits)==10000
        origins=[r for r in segments if r['segment_index']==0];assert len(origins)==10000
        if name=='Cone.dll':
            for axis,half in [('X',1),('Y',.5)]:
                assert all(abs(r[axis])<=half for r in origins)
                e.check('rectangular source second moment '+axis,sum(r[axis]**2 for r in origins)/10000,half**2/3,
                    rtol=0,atol=6*math.sqrt(4*half**4/45/10000))
        elif name=='fiber1.DLL':
            radii=[r['X']**2+r['Y']**2 for r in origins];assert max(radii)<=1+1e-7
            e.check('uniform disk source radial second moment',sum(radii)/10000,.5,rtol=0,atol=6/math.sqrt(12*10000))
        else:assert all(r['X']==r['Y']==r['Z']==0 for r in origins)
        values=[r['N']for r in hits];expected=(low+high)/2;se=(high-low)/math.sqrt(12*10000)
        assert all(low-1e-12<=v<=high+1e-12 for v in values)
        e.check('source mean direction cosine',sum(values)/len(values),expected,rtol=0,atol=6*se)
        data=await detector(e,2,width=37,height=36);e.check('source DLL hemispherical fraction W',data['total_flux'],power)
        (e.folder/'source-distribution-reference.json').write_text(json.dumps(dict(name=name,seed=42,rays=10000,parameters=parameters,
            cosine_bounds=[low,high],expected_mean=expected,six_standard_errors=6*se,expected_power_W=power,
            reference='installed source: uniform solid angle; Cone/Lambertian_Overfill report hemisphere fraction, fiber1 unit relative intensity'),indent=2),encoding='utf-8')
    asyncio.run(execute('adaptation_source_distribution_'+name.replace('.','_'),work))


@pytest.mark.zemax
@pytest.mark.parametrize('name',OBJECTS)
def test_object_dll_controlled_native(name):
    from support.nsc import trace,detector
    async def work(e):
        await setup(e,3)
        parameters={1:2,2:2,3:.25,4:1}if name=='CoatingSample.DLL'else({1:1,2:2,3:32}if name=='HalfCylinder.DLL'else({1:2,2:2,3:2}if name=='DiffractionGrating.DLL'else{1:2,2:1,3:2,4:32}))
        optical=dict(object=2,object_type='UserDefinedObject',file1=name,material=''if name=='CoatingSample.DLL'else'MIRROR',parameters=parameters)
        if name=='DiffractionGrating.DLL':optical['diffraction']=dict(DLL='diff_samp_1.DLL',StartOrder=0,StopOrder=0)
        await update(e,[dict(object=1,object_type='SourceRay',x=.2,y=.3,z=-2,data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            optical,
            dict(object=3,object_type='DetectorRectangle',z=3 if name=='CoatingSample.DLL'else -3,material='ABSORB',data=dict(XHalfWidth=3,YHalfWidth=3,NumberXPixels=8,NumberYPixels=8))])
        result,segments=await trace(e,'object',use_polarization=True,split_rays=name=='DiffractionGrating.DLL')
        hit=next(r for r in segments if r['HitObject']==2)
        for key,value in [('X',.2),('Y',.3),('Z',0)]:e.check('source-defined object front intersection mm',hit[key],value)
        data=await detector(e,3)
        if name=='CoatingSample.DLL':e.check('source-defined object detector W',data['total_flux'],.25)
        else:
            outgoing=next(r for r in segments if r['HitObject']==3)
            for key,expected in [('L',0),('M',0),('N',-1)]:e.check('source-defined cap reflection direction',outgoing[key],expected)
            e.check('MIRROR native branch/detector W',data['total_flux'],outgoing['Intensity'])
            assert 0<data['total_flux']<=1
        path=e.folder/'object.zos';await e.call('save_lens_as',dict(path=str(path)));await e.call('open_lens',dict(path=str(path)))
        assert(await e.call('get_nsc_objects',dict(request=dict(start=2,count=1))))['rows'][0]['file1']==name
    asyncio.run(execute('adaptation_object_reference_'+name.replace('.','_'),work))


@pytest.mark.zemax
@pytest.mark.parametrize('name',BULK)
def test_bulk_dll_source_distribution_native(name):
    from collections import defaultdict
    from support.nsc import detector
    async def work(e):
        await setup(e,3)
        parameters={0:1}
        if name=='Henyey-Greenstein-bulk.DLL':parameters[1]=.4
        if name=='poly_bulk_scat.DLL':parameters.update({i:0 for i in range(1,16)});parameters[1]=1
        if name=='Rayleigh.DLL':parameters={0:.55,1:1}
        settings=dict(DLL=name,MeanPath=2)
        if name not in ('Henyey-Greenstein-bulk.DLL','Rayleigh.DLL'):settings['Angle']=30
        await update(e,[dict(object=1,object_type='RectangularVolume',z=-50,material='N-BK7',
            data=dict(X1HalfWidth=50,Y1HalfWidth=50,X2HalfWidth=50,Y2HalfWidth=50,ZLength=100),
            volume=dict(model='DLLDefinedScattering',settings=settings,parameters=parameters)),
            dict(object=2,object_type='SourceRay',inside_of=1,data=dict(NumberOfAnalysisRays=10000,Power=1,ZCosine=1)),
            dict(object=3,object_type='DetectorPolar',inside_of=1,material='ABSORB',data=dict(RadialSize=3,MaxAngle=180,NumberPPixels=91,NumberAPixels=36))])
        path=e.folder/'bulk.zrd'
        await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(random_seed=42,scatter_rays=True,use_polarization=True,save_zrd=str(path)))),timeout_seconds=600)
        by_ray=defaultdict(list)
        for start in range(0,10000,500):
            data=await e.finish(await e.call('read_zrd',dict(request=dict(path=str(path),start_ray=start,max_segments=10000))),timeout_seconds=600)
            for row in data['rows']:
                if start<=row['ray_index']<start+500:by_ray[row['RayNumber']].append(row)
            assert len([i for i in by_ray if start<i<=start+500])==500
        assert len(by_ray)==10000
        first=[];mu=[]
        for rows in by_ray.values():
            events=[(i,r)for i,r in enumerate(rows)if r['SegBulkScattered']]
            if not events:first.append(3);continue
            i,r=events[0]
            first.append(math.sqrt(sum((r[k]-rows[0][k])**2 for k in ('X','Y','Z'))))
            assert i+1<len(rows)
            mu.append(max(-1,min(1,sum(r[k]*rows[i+1][k]for k in ('L','M','N')))))
        for distance in (.5,1,2,2.5):
            probability=1-math.exp(-distance/2)
            e.check('DLL first free path CDF '+str(distance),sum(v<=distance for v in first)/10000,probability,
                rtol=0,atol=6*math.sqrt(probability*(1-probability)/10000))
        for limit in (-.5,0,.5):
            if name in ('bulk_samp_1.DLL','poly_bulk_scat.DLL'):continue
            if name=='Rayleigh.DLL':probability=3/8*(limit+limit**3/3+4/3)
            else:
                g=.4;probability=(1-g*g)/(2*g)*(1/math.sqrt(1+g*g-2*g*limit)-1/(1+g))
            e.check('DLL angular cosine CDF '+str(limit),sum(v<=limit for v in mu)/len(mu),probability,
                rtol=0,atol=6*math.sqrt(probability*(1-probability)/len(mu)))
        if name in ('bulk_samp_1.DLL','poly_bulk_scat.DLL'):
            for fraction in (.25,.5,.75):
                e.check('DLL uniform theta CDF '+str(fraction),sum(math.acos(v)<=math.radians(30)*fraction for v in mu)/len(mu),fraction,
                    rtol=0,atol=6*math.sqrt(fraction*(1-fraction)/len(mu))+1e-7)
        flux=await detector(e,3,width=91,height=36)
        assert 0<flux['total_flux']<=1+1e-7
        await e.call('save_lens_as',dict(path=str(e.folder/'bulk.zos')))
        (e.folder/'bulk-source-reference.json').write_text(json.dumps(dict(name=name,parameters=parameters,seed=42,rays=10000,
            mean_path_mm=2,first_events=len(mu),criterion='six binomial standard errors; first path <=2.5mm avoids detector facet boundary',
            reference='source-defined exponential free path and angular CDF; bulk_samp/poly C0 use uniform theta, HG g=.4, Rayleigh 3/8*(1+mu²)',
            detected_W=flux['total_flux'],checks=e.checks),indent=2),encoding='utf-8')
    asyncio.run(execute('adaptation_bulk_distribution_'+name.replace('.','_'),work))
