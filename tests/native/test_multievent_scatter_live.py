"""Near-forward bulk scattering gives an independently Poisson event fixture."""
import asyncio
import json
import math
from collections import Counter,defaultdict
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,detector


@pytest.mark.zemax
def test_multievent_poisson_path_reference_native():
    async def work(e):
        await setup(e,3)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=10000,Power=1,ZCosine=1)),
            dict(object=2,object_type="RectangularVolume",z=5,material="N-BK7",
                data=dict(X1HalfWidth=100,Y1HalfWidth=100,X2HalfWidth=100,Y2HalfWidth=100,ZLength=6),
                volume=dict(model="AngleScattering",settings=dict(MeanPath=2,Angle=.00001))),
            dict(object=3,object_type="DetectorPolar",z=5,material="ABSORB",data=dict(MaxAngle=180,RadialSize=200,NumberPPixels=91,NumberAPixels=36))])
        by_ray=defaultdict(list)
        zrd=e.folder/"multievent.zrd"
        await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(save_zrd=str(zrd),random_seed=42,scatter_rays=True))))
        # Bounded native reads avoid one enormous task exceeding the polling budget.
        for start in range(0,10000,500):
            result=await e.finish(await e.call("read_zrd",dict(request=dict(path=str(zrd),start_ray=start,max_segments=5000))))
            for row in result["rows"]:
                if start<=row["ray_index"]<start+500:by_ray[row["RayNumber"]].append(row)
            assert len([i for i in by_ray if start<i<=start+500])==500
        assert len(by_ray)==10000
        events=[];first=[];lengths=[]
        for rows in by_ray.values():
            scattering=[r for r in rows if r["SegBulkScattered"]]
            hits=[r for r in rows if r["HitObject"]==3]
            assert len(hits)==1
            count=len(scattering);events.append(count)
            first.append(scattering[0]["Z"]-5 if count else 6.)
            lengths.extend(r["PathLength"]for r in scattering)
        hist=Counter(events);n=len(events);mean=3.
        checks=[]
        for k in range(7):
            expected=math.exp(-mean)*mean**k/math.factorial(k);observed=hist[k]/n
            tolerance=6*math.sqrt(expected*(1-expected)/n)
            checks.append(dict(events=k,expected_fraction=expected,actual_fraction=observed,tolerance=tolerance))
            e.check(f"bulk Poisson N={k}",observed,expected,rtol=0,atol=tolerance)
        e.check("bulk mean events",sum(events)/n,3.,rtol=0,atol=6*math.sqrt(3/n))
        for distance in (.5,1.,2.,4.):
            expected=1-math.exp(-distance/2);observed=sum(v<=distance for v in first)/n
            e.check(f"first free path CDF {distance}mm",observed,expected,rtol=0,atol=6*math.sqrt(expected*(1-expected)/n))
        flux=await detector(e,3,width=91,height=36)
        assert 0<flux["total_flux"]<=1+1e-7
        await e.call("save_lens_as",dict(path=str(e.folder/"multievent.zos")))
        (e.folder/"multievent-reference.json").write_text(json.dumps(dict(seed=42,rays=n,mean_free_path_mm=2,axial_path_mm=6,
            scattering_angle_deg=.00001,histogram=dict(hist),checks=checks,
            scope="near-forward independent Poisson events and censored first-path CDF; finite-angle random walk remains separate",
            energy=dict(detected_W=flux["total_flux"],unclassified_W=1-flux["total_flux"])),indent=2),encoding="utf-8")
    asyncio.run(execute("multievent_scatter",work))
