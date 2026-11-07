"""Native detector, reference-frame and coherent ray-model references (serial stdio)."""
from tests.support.nsc import setup, update, trace, detector
import asyncio
import json
import math
from pathlib import Path
import pytest
from tests.support.native import execute










@pytest.mark.zemax
def test_polar_directions_native():
    async def work(e):
        await setup(e,2)
        await update(e,[
            dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type="DetectorPolar",material="ABSORB",
                 data=dict(MaxAngle=180,RadialSize=10,NumberPPixels=181,NumberAPixels=36),
                 type_settings=dict(UsePixelInterpolation=False)),
        ])
        for theta,phi in ((20,40),(20,130),(20,220),(20,310),(20,0),(20,359),(0,0),(180,0)):
            th,ph=map(math.radians,(theta,phi))
            await update(e,[dict(object=1,data=dict(XCosine=math.sin(th)*math.cos(ph),
                         YCosine=math.sin(th)*math.sin(ph),ZCosine=math.cos(th)))])
            trace_result,_=await trace(e,f"polar_{theta}_{phi}")
            flux=await detector(e,2,width=100,height=36)
            full=json.loads(Path(flux["artifacts"][0]["path"]).read_text(encoding="utf-8"))
            assert full["nx"]==181 and full["ny"]==36
            occupied=[(i,j,v)for i,row in enumerate(full["values"])for j,v in enumerate(row)if abs(v)>1e-12]
            assert len(occupied)==(36 if theta==0 else 1),occupied
            if theta==0:
                for _,column,value in occupied:
                    assert column==theta
                    e.check("polar pole shared azimuth W",value,1/36)
            iy,ix,power=occupied[0]
            assert ix==theta
            if theta not in (0,180):assert iy==int(math.floor((phi+5)/10))%36
            e.check(f"Polar {theta},{phi} total W",flux["total_flux"],1)
            intensity=await detector(e,2,kind="intensity",x_start=ix,y_start=iy,width=1,height=1)
            e.check(f"Polar {theta},{phi} W/sr",intensity["values"][0][0],
                    power/full["pixel_solid_angle_sr"][ix])
            assert intensity["total_flux"]is None and flux["complete"]
            if (theta,phi)==(20,40):
                page=await detector(e,2,x_start=100,width=81,height=36)
                assert page["values"]==[row[100:]for row in full["values"]]
                e.check("full sphere solid angle sr",sum(full["pixel_solid_angle_sr"])*36,4*math.pi)
        await e.call("save_lens_as",dict(path=str(e.folder/"polar.zos")))
        bad=await e.call("get_detector_data",dict(request=dict(detector=2,kind="irradiance")),okay=False)
        assert not bad["ok"]and bad["error"]["code"]=="UNSUPPORTED_DETECTOR_DATA"
        caps=await e.call("get_capabilities")
        assert caps["detector_adapters"]["DetectorPolar"]["kinds"]==["flux","intensity"]
        report=await e.call("export_evaluation_report",dict(
            task_ids=[trace_result["task"]["task_id"]],title="Polar 探测器追迹结果"))
        assert {"markdown","json","csv"}<={a["kind"]for a in report["artifacts"]}
        assert trace_result["rows"][0]["detector"]==2
        e.check("saved trace detector power W",trace_result["rows"][0]["accumulated_total_flux"],1)
    asyncio.run(execute("polar_directions",work))


@pytest.mark.zemax
def test_nsc_reference_reflection_native():
    async def work(e):
        import numpy as np
        await setup(e,4)
        tx,ty,tz=map(math.radians,(5,-7,11))
        rx=np.array([[1,0,0],[0,math.cos(tx),-math.sin(tx)],[0,math.sin(tx),math.cos(tx)]])
        ry=np.array([[math.cos(ty),0,math.sin(ty)],[0,1,0],[-math.sin(ty),0,math.cos(ty)]])
        rz=np.array([[math.cos(tz),-math.sin(tz),0],[math.sin(tz),math.cos(tz),0],[0,0,1]])
        rotation=rx@ry@rz;offset=np.array([1.,2.,3.])
        await update(e,[
            dict(object=1,object_type="NullObject",x=1,y=2,z=3,tilt_x=5,tilt_y=-7,tilt_z=11),
            dict(object=2,object_type="SourceRay",ref_object=1,
                 data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=3,object_type="Rectangle",ref_object=1,z=10,tilt_y=45,material="MIRROR",
                 data=dict(XHalfWidth=5,YHalfWidth=5)),
            dict(object=4,object_type="DetectorRectangle",ref_object=1,x=-10,z=10,tilt_y=-90,
                 material="ABSORB",data=dict(XHalfWidth=2,YHalfWidth=2,NumberXPixels=8,NumberYPixels=8)),
        ])
        objects=(await e.call("get_nsc_objects",dict(request={})))["rows"]
        for row in objects:
            i=row["object"];angle=math.radians({1:0,2:0,3:45,4:-90}[i])
            local=np.array([[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]])
            expected=rotation@local
            actual=row["global_transform"]
            for a,b in zip(np.array(actual["rotation"]).ravel(),expected.ravel()):
                e.check(f"object {i} signed global rotation",float(a),float(b))
            position={1:[0,0,0],2:[0,0,0],3:[0,0,10],4:[-10,0,10]}[i]
            for a,b in zip(actual["translation"],offset+rotation@np.array(position)):
                e.check(f"object {i} global translation mm",a,float(b))
        _,segments=await trace(e,"reflection")
        (e.folder/"segments.json").write_text(json.dumps(segments,indent=2),encoding="utf-8")
        for index,position in ((3,[0,0,10]),(4,[-10,0,10])):
            hit=next(row for row in segments if row["HitObject"]==index)
            for key,value in zip(("X","Y","Z"),offset+rotation@np.array(position)):
                e.check(f"reflection object {index} {key} mm",hit[key],float(value))
        incident=rotation@np.array([0.,0.,1.])
        normal=rotation@np.array([math.sqrt(.5),0.,math.sqrt(.5)])
        reflected=incident-2*np.dot(incident,normal)*normal
        for object_index,direction in ((3,incident),(4,reflected)):
            hit=next(row for row in segments if row["HitObject"]==object_index)
            for key,expected in zip(("L","M","N"),direction):
                e.check(f"reflection object {object_index} direction {key}",hit[key],float(expected))
        e.check("perfect mirror received W",(await detector(e,4))["total_flux"],1)
        saved=str(e.folder/"reflection.zos")
        await e.call("save_lens_as",dict(path=saved))
        await e.call("open_lens",dict(path=saved))
        loaded=(await e.call("get_nsc_objects",dict(request={})))["rows"]
        for before,after in zip(objects,loaded):
            assert after["ref_object"]==(0 if after["object"]==1 else 1)
            for a,b in zip(before["global_transform"]["translation"],after["global_transform"]["translation"]):
                e.check("saved reference translation mm",a,b)
            for row_a,row_b in zip(before["global_transform"]["rotation"],after["global_transform"]["rotation"]):
                for a,b in zip(row_a,row_b):e.check("saved reference signed rotation",a,b)
    asyncio.run(execute("nsc_reflection",work))


@pytest.mark.zemax
def test_nsc_coherent_phase_native():
    async def work(e):
        await setup(e,3)
        await update(e,[
            dict(object=i,object_type="SourceRay",
                 data=dict(NumberOfAnalysisRays=1,Power=.5,ZCosine=1,WaveNumber=1),
                 sources=dict(RandomPolarization=False,Jx=1,Jy=0,CoherenceLength=0,InitialPhaseDeg=0))
            for i in (1,2)
        ]+[dict(object=3,object_type="DetectorRectangle",z=10,material="ABSORB",
                data=dict(NumberXPixels=8,NumberYPixels=8,XHalfWidth=2,YHalfWidth=2),
                type_settings=dict(UsePixelInterpolation=False,NormalizeCoherentPower=False))])
        for power,phase in ((.5,0),(.5,90),(.5,180),(.5,270),(.25,90),(1,90)):
            await update(e,[dict(object=1,data=dict(Power=power)),
                            dict(object=2,data=dict(Power=power),sources=dict(InitialPhaseDeg=phase))])
            await trace(e,f"power_{power}_phase_{phase}",use_polarization=True)
            results={k:await detector(e,3,kind="coherent",coherent_type=k)
                     for k in ("Real","Imaginary","Amplitude","Power")}
            incoherent=await detector(e,3,kind="flux")
            # Read fields at the illuminated pixel and use the documented NSC normalization.
            iy,ix=next((iy,ix)for iy,row in enumerate(incoherent["values"])
                       for ix,v in enumerate(row)if v>1e-12)
            r,im,a,p=[results[k]["values"][iy][ix]for k in ("Real","Imaginary","Amplitude","Power")]
            e.check(f"power {power} phase {phase} incident amplitude sum",a,math.sqrt(power)*2)
            e.check(f"power {power} phase {phase} native field magnitude",r*r+im*im,2*power)
            expected=(1+math.cos(math.radians(phase)))/2
            e.check(f"power {power} phase {phase} normalized coherent ratio",p/incoherent["values"][iy][ix],expected)
            # Native Real/Imaginary carry the phase with the incoherent-power magnitude.
            # At destructive cancellation the phase has no independent physical reference.
            vector=1+complex(math.cos(math.radians(phase)),-math.sin(math.radians(phase)))
            if abs(vector)>1e-8:
                path_phase=-2*math.pi*10/.00055
                expected_field=math.sqrt(2*power)*complex(math.cos(path_phase),math.sin(path_phase))*vector/abs(vector)
                e.check(f"power {power} phase {phase} real phase component",r,expected_field.real)
                e.check(f"power {power} phase {phase} imaginary phase component",im,expected_field.imag)
        await update(e,[dict(object=3,type_settings=dict(NormalizeCoherentPower=True)),
                        dict(object=2,sources=dict(InitialPhaseDeg=90))])
        await trace(e,"normalized",use_polarization=True)
        coherent=await detector(e,3,kind="coherent",coherent_type="Power")
        flux=await detector(e,3)
        e.check("NormalizeCoherentPower total W",
                sum(sum(row)for row in coherent["values"]),flux["total_flux"])
        assert coherent["coherence"]["normalize_coherent_power"]
        saved=str(e.folder/"coherent.zos")
        await e.call("save_lens_as",dict(path=saved))
        await e.call("open_lens",dict(path=saved))
        objects=(await e.call("get_nsc_objects",dict(request={})))["rows"]
        assert objects[1]["sources"]["InitialPhaseDeg"]==90
        assert objects[1]["sources"]["CoherenceLength"]==0
        assert objects[2]["type_settings"]["NormalizeCoherentPower"]is True
    asyncio.run(execute("nsc_coherent",work))



@pytest.mark.zemax
@pytest.mark.parametrize("degrees",[0,30])
@pytest.mark.parametrize("polarization",["s","p"])
def test_nsc_glass_plate_native(degrees,polarization):
    async def work(e):
        await setup(e,4)
        coefficients=None;active=False
        for line in (Path.home()/"Documents/Zemax/Glasscat/SCHOTT.AGF").read_text(encoding="utf-8-sig",errors="replace").splitlines():
            if line.startswith("NM "):
                active=line.split()[1]=="N-BK7"
                if active:assert line.split()[2]=="2"
            if active and line.startswith("CD "):coefficients=list(map(float,line.split()[1:7]));break
        assert coefficients is not None
        l2=.55**2
        n=math.sqrt(1+sum(coefficients[i]*l2/(l2-coefficients[i+1])for i in (0,2,4)))
        angle=math.radians(degrees);sin_t=math.sin(angle)/n;cos_t=math.sqrt(1-sin_t*sin_t)
        ci=math.cos(angle)
        reflectance=(((ci-n*cos_t)/(ci+n*cos_t))**2 if polarization=="s"
                     else ((n*ci-cos_t)/(n*ci+cos_t))**2)
        await update(e,[
            dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=1,
                 WaveNumber=1,XCosine=math.sin(angle),ZCosine=ci),
                 sources=dict(RandomPolarization=False,Jx=1 if polarization=="p"else 0,
                              Jy=1 if polarization=="s"else 0,InitialPhaseDeg=0,CoherenceLength=0)),
            dict(object=2,object_type="RectangularVolume",z=5,material="N-BK7",
                 data=dict(X1HalfWidth=10,Y1HalfWidth=10,X2HalfWidth=10,Y2HalfWidth=10,ZLength=2)),
            dict(object=3,object_type="DetectorRectangle",z=-2,material="ABSORB",
                 data=dict(XHalfWidth=10,YHalfWidth=10,NumberXPixels=16,NumberYPixels=16)),
            dict(object=4,object_type="DetectorRectangle",z=12,material="ABSORB",
                 data=dict(XHalfWidth=10,YHalfWidth=10,NumberXPixels=16,NumberYPixels=16)),
        ])
        trace_result,segments=await trace(e,"glass",use_polarization=True,split_rays=True)
        (e.folder/"segments.json").write_text(json.dumps(segments,indent=2),encoding="utf-8")
        inside=next(r for r in segments if r["InsideOf"]==2)
        for key,expected in (("L",sin_t),("M",0),("N",cos_t)):
            e.check(f"Snell {degrees} deg {polarization} {key}",inside[key],expected)
        reflected=[r for r in segments if r["HitObject"]==3]
        transmitted=[r for r in segments if r["HitObject"]==4]
        assert reflected and transmitted
        first=min(reflected,key=lambda r:r["SegmentLevel"])
        e.check("first-interface Fresnel reflected W",first["Intensity"],reflectance)
        for key,expected in (("L",math.sin(angle)),("M",0),("N",-ci)):
            e.check("first reflection "+key,first[key],expected)
        outgoing=min(transmitted,key=lambda r:r["SegmentLevel"])
        for key,expected in (("L",math.sin(angle)),("M",0),("N",ci)):
            e.check("parallel-plate outgoing "+key,outgoing[key],expected)
        e.check("parallel-plate first transmission X mm",outgoing["X"],
                10*math.tan(angle)+2*sin_t/cos_t)
        detected={}
        for index,hits in ((3,reflected),(4,transmitted)):
            data=await detector(e,index)
            e.check(f"ZRD branch sum to detector {index} W",
                    sum(r["Intensity"]for r in hits),data["total_flux"])
            detected[index]=data["total_flux"]
        residual=1-sum(detected.values())
        assert residual>=-1e-8
        (e.folder/"reference.json").write_text(json.dumps(dict(
            refractive_index=n,wavelength_um=.55,degrees=degrees,polarization=polarization,
            first_interface_reflectance=reflectance,detected_power_W=detected,
            not_detected_W=residual,
            unclassified_remainder="bulk attenuation, native termination and other paths are not individually inferred",
            native_trace_summary=trace_result,
        ),ensure_ascii=False,indent=2),encoding="utf-8")
        saved=str(e.folder/"glass.zos")
        await e.call("save_lens_as",dict(path=saved))
        await e.call("open_lens",dict(path=saved))
        objects=(await e.call("get_nsc_objects",dict(request={})))["rows"]
        assert objects[1]["material"]=="N-BK7"
        e.check("saved plate thickness mm",objects[1]["data"]["ZLength"],2)
        e.check("saved source Jones X",objects[0]["sources"]["Jx"],1 if polarization=="p"else 0)
    asyncio.run(execute(f"nsc_glass_{degrees}_{polarization}",work))


@pytest.mark.zemax
def test_nsc_detector_history_native():
    async def work(e):
        await setup(e,3)
        await update(e,[
            dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type="DetectorRectangle",z=5,material="",
                 data=dict(NumberXPixels=8,NumberYPixels=8)),
            dict(object=3,object_type="DetectorRectangle",z=10,material="ABSORB",
                 data=dict(NumberXPixels=8,NumberYPixels=8)),
        ])
        await trace(e,"baseline")
        a,b=await detector(e,2),await detector(e,3)
        assert a["complete"]and b["complete"]
        await e.call("clear_detectors",dict(request=dict(detector=2)))
        a,b=await detector(e,2),await detector(e,3)
        assert a["trace_history"]==[]and a["complete"]
        assert len(b["trace_history"])==1 and b["complete"]
        await trace(e,"accumulated",detector_policy="accumulate")
        e.check("selective-clear detector W",(await detector(e,2))["total_flux"],1)
        e.check("uncleared detector accumulated W",(await detector(e,3))["total_flux"],2)
        await update(e,[dict(object=1,data=dict(Power=.5))])
        stale=await detector(e,3)
        assert not stale["complete"] and not stale["model_matches_history"]
        await trace(e,"mixed",detector_policy="accumulate")
        mixed=await detector(e,3)
        assert mixed["mixed_conditions"]and not mixed["complete"]and mixed["history_known"]
        e.check("mixed revision accumulated W",mixed["total_flux"],2.5)
        await trace(e,"fresh")
        fresh=await detector(e,3)
        assert fresh["complete"]and not fresh["mixed_conditions"]and len(fresh["trace_history"])==1
        e.check("fresh model W",fresh["total_flux"],.5)
        saved=str(e.folder/"history.zos")
        await e.call("save_lens_as",dict(path=saved))
        await e.call("open_lens",dict(path=saved))
        loaded=await detector(e,3)
        assert not loaded["history_known"]and not loaded["complete"]
        # A long trace provides a real cancellation boundary; no assertion claims instant cancellation.
        await update(e,[dict(object=1,data=dict(NumberOfAnalysisRays=10000000))])
        task=await e.call("run_nsc_ray_trace",dict(request=dict(random_seed=42)))
        task=await e.call("cancel_task",dict(task_id=task["task_id"]))
        for _ in range(2000):
            if task["state"]in {"succeeded","failed","cancelled"}:break
            await asyncio.sleep(.02)
            task=await e.call("get_task_status",dict(task_id=task["task_id"]))
        assert task["state"]=="cancelled"
        partial=await detector(e,3)
        assert not partial["complete"]and partial["trace_history"][-1]["state"]=="cancelled"
    asyncio.run(execute("nsc_history",work))
