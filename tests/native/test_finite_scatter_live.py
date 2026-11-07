"""Finite-angle event/path laws and absorption, without a forward-path approximation."""
import asyncio
import json
import math
from collections import defaultdict
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,detector
from tests.support.scatter_reference import sphere_transport


def absorption_reference():
    selected=False
    for line in (Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF').read_text(encoding='utf-8-sig',errors='replace').splitlines():
        if line.startswith('NM '):selected=line.split()[1]=='N-BK7'
        if selected and line.startswith('IT ')and float(line.split()[1])==.3:
            _,w,t,length=line.split()[:4]
            return float(w),-math.log(float(t))/float(length)
    raise ValueError('Exact catalog absorption wavelength unavailable')


@pytest.mark.zemax
@pytest.mark.parametrize('angle',[10,45,90])
def test_finite_angle_sphere_transport_native(angle):
    async def work(e):
        import numpy as np
        wavelength,alpha=absorption_reference();await setup(e,3)
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=wavelength)])))
        await update(e,[dict(object=1,object_type='RectangularVolume',z=-50,material='N-BK7',
            data=dict(X1HalfWidth=50,Y1HalfWidth=50,X2HalfWidth=50,Y2HalfWidth=50,ZLength=100),
            volume=dict(model='AngleScattering',settings=dict(MeanPath=2,Angle=angle))),
            dict(object=2,object_type='SourceRay',inside_of=1,data=dict(NumberOfAnalysisRays=10000,Power=1,ZCosine=1)),
            dict(object=3,object_type='DetectorPolar',inside_of=1,material='ABSORB',
                data=dict(RadialSize=3,MaxAngle=180,NumberPPixels=91,NumberAPixels=36))])
        zrd=e.folder/'rays.zrd'
        trace=await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(random_seed=42,use_polarization=True,scatter_rays=True,save_zrd=str(zrd)))))
        data=await e.finish(await e.call('read_zrd',dict(request=dict(path=str(zrd),max_segments=100000))))
        rows=data['rows'];assert data.get('next_read')is None or len(rows)<100000,'Unexpected truncation; use explicit continuation'
        by_ray=defaultdict(list)
        for r in rows:by_ray[r['RayNumber']].append(r)
        assert len(by_ray)==10000
        counts=[];paths=[];first=[];mu=[];azimuth=[];powers=[]
        for ray in by_ray.values():
            hits=[r for r in ray if r['HitObject']==3];assert len(hits)==1
            events=[(i,r)for i,r in enumerate(ray)if r['SegBulkScattered']]
            counts.append(len(events));paths.append(sum(r['PathLength']for r in ray));powers.append(hits[0]['Intensity'])
            if events:
                i,r=events[0];first.append(r['PathLength'])
                outgoing=ray[i+1];mu.append(sum(r[k]*outgoing[k]for k in ('L','M','N')))
                azimuth.append(math.atan2(outgoing['M'],outgoing['L'])%(2*math.pi))
            else:first.append(3.)
        reference_counts,reference_paths=sphere_transport(angle)
        records=[]
        def compare(label,actual,expected,tolerance):
            records.append(dict(label=label,actual=float(actual),expected=float(expected),atol=float(tolerance),passed=abs(actual-expected)<=tolerance))
        for k in range(6):
            actual=sum((v==k if k<5 else v>=5)for v in counts)/10000
            expected=float(np.mean(reference_counts==k if k<5 else reference_counts>=5))
            tolerance=6*math.sqrt(expected*(1-expected)*(1/10000+1/len(reference_counts)))+1e-6
            compare(f'event bin {k}',actual,expected,tolerance)
        for distance in (3,4,6,10):
            # The unscattered atom is exactly at radius=3 mm; roundoff in a
            # sum of path segments must not split that atom across the boundary.
            actual=sum(v<=distance+1e-8 for v in paths)/10000
            expected=float(np.mean(reference_paths<=distance+1e-8))
            tolerance=6*math.sqrt(expected*(1-expected)*(1/10000+1/len(reference_paths)))+1e-5
            compare(f'path CDF {distance}mm',actual,expected,tolerance)
        c=math.cos(math.radians(angle));u=[(v-c)/(1-c)for v in mu]
        for q in (.25,.5,.75):
            compare(f'first cone solid-angle CDF {q}',sum(v<=q for v in u)/len(u),q,6*math.sqrt(q*(1-q)/len(u))+2e-6)
        for quadrant in range(4):
            compare(f'first-event azimuth quadrant {quadrant}',sum(quadrant*math.pi/2<=v<(quadrant+1)*math.pi/2 for v in azimuth)/len(azimuth),.25,6*math.sqrt(.25*.75/len(azimuth)))
        for distance in (.5,1,2,2.5):
            p=1-math.exp(-distance/2)
            compare(f'first free path CDF {distance}mm',sum(v<=distance for v in first)/10000,p,6*math.sqrt(p*(1-p)/10000))
        expected_power=math.fsum(math.exp(-alpha*length)/10000 for length in paths)
        actual_power=(await detector(e,3,width=91,height=36))['total_flux']
        compare('actual-path Beer Lambert W',actual_power,expected_power,1e-8+1e-7*abs(expected_power))
        compare('ZRD detector power sum W',math.fsum(powers),actual_power,1e-8+1e-7*abs(actual_power))
        await e.call('save_lens_as',dict(path=str(e.folder/'model.zos')))
        (e.folder/'transport-reference.json').write_text(json.dumps(dict(angle_deg=angle,seed=42,rays=10000,reference_rays=100000,
            radius_mm=3,mean_path_mm=2,wavelength_um=wavelength,absorption_per_mm=alpha,
            geometry='sphere wholly inside homogeneous glass; no refracting boundary before absorption detector',
            native_trace=trace,checks=records),indent=2),encoding='utf-8')
        assert all(r['passed']for r in records),[r for r in records if not r['passed']]
    asyncio.run(execute('finite_scatter_'+str(angle),work))


@pytest.mark.zemax
def test_finite_two_region_forward_transport_native():
    """Two 3-mm intervals have independent Poisson means 1.5 and 0.75."""
    async def work(e):
        await setup(e,4)
        await update(e,[
            dict(object=1,object_type='RectangularVolume',z=-10,material='N-BK7',
                data=dict(X1HalfWidth=100,Y1HalfWidth=100,X2HalfWidth=100,Y2HalfWidth=100,ZLength=13),
                volume=dict(model='AngleScattering',settings=dict(MeanPath=2,Angle=.00001))),
            dict(object=2,object_type='RectangularVolume',z=3,material='N-BK7',
                data=dict(X1HalfWidth=100,Y1HalfWidth=100,X2HalfWidth=100,Y2HalfWidth=100,ZLength=10),
                volume=dict(model='AngleScattering',settings=dict(MeanPath=4,Angle=.00001))),
            dict(object=3,object_type='SourceRay',inside_of=1,
                data=dict(NumberOfAnalysisRays=10000,Power=1,ZCosine=1)),
            dict(object=4,object_type='DetectorRectangle',z=6,inside_of=2,material='ABSORB',
                data=dict(NumberXPixels=1,NumberYPixels=1,XHalfWidth=100,YHalfWidth=100))])
        zrd=e.folder/'two-regions.zrd'
        await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(random_seed=42,
            scatter_rays=True,use_polarization=True,save_zrd=str(zrd)))))
        data=await e.finish(await e.call('read_zrd',dict(request=dict(path=str(zrd),max_segments=100000))))
        assert len(data['rows'])<100000, 'Use bounded continuation before interpreting the full sample'
        by_ray=defaultdict(list)
        for row in data['rows']:by_ray[row['RayNumber']].append(row)
        assert len(by_ray)==10000
        records=[]
        for rows in by_ray.values():
            hits=[r for r in rows if r['HitObject']==4]
            assert len(hits)==1
            events=[r for r in rows if r['SegBulkScattered']]
            records.append(dict(first=sum(r['Z']<3 for r in events),second=sum(r['Z']>=3 for r in events),
                                path_mm=sum(r['PathLength']for r in rows)))
        (e.folder/'two-region-reference.json').write_text(json.dumps(dict(seed=42,rays=10000,
            interval_lengths_mm=[3,3],mean_paths_mm=[2,4],cone_deg=.00001,rows=records,
            scope='near-forward two-region event statistics; finite-angle transport tested separately'),indent=2),encoding='utf-8')
        for key,mean in (('first',1.5),('second',.75)):
            e.check(key+' mean event count',sum(r[key]for r in records)/10000,mean,
                    atol=6*math.sqrt(mean/10000),rtol=0)
            for k in range(5):
                expected=math.exp(-mean)*mean**k/math.factorial(k)
                actual=sum(r[key]==k for r in records)/10000
                e.check(key+f' Poisson bin {k}',actual,expected,
                        atol=6*math.sqrt(expected*(1-expected)/10000),rtol=0)
        e.check('two-region maximum geometric path error mm',max(abs(r['path_mm']-6)for r in records),0,
                atol=1e-8+1e-7*6,rtol=0)
        await e.call('save_lens_as',dict(path=str(e.folder/'model.zos')))
    asyncio.run(execute('finite_scatter_two_regions',work))
