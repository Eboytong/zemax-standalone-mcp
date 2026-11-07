"""Native detector formats, color and voxel references through stdio."""
import asyncio,json
from pathlib import Path
import pytest
from support.native import execute
from support.nsc import setup,update,detector


@pytest.mark.zemax
@pytest.mark.parametrize("kind,extension",[("DetectorRectangle","ddr"),("DetectorPolar","ddp"),("DetectorColor","ddc"),("DetectorVolume","ddv")])
def test_detector_formats_native(kind,extension):
    async def work(e):
        await setup(e,2)
        params=dict(MaxAngle=180,RadialSize=10,NumberPPixels=11,NumberAPixels=36) if kind=="DetectorPolar" else dict(XHalfWidth=2,YHalfWidth=3,NumberXPixels=3,NumberYPixels=5)
        if kind=="DetectorVolume":params.update(ZHalfWidth=1,NumberZPixels=4)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type=kind,z=0 if kind=="DetectorPolar"else 10,data=params)])
        await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(random_seed=42))))
        args=dict(width=10,height=10,**(dict(depth=4) if kind=="DetectorVolume"else {}))
        original=await detector(e,2,**args)
        if kind=="DetectorVolume":
            assert (original["nx"],original["ny"],original["nz"])==(3,5,4)
            for z in range(4):e.check("one ray entering voxel plane W",sum(v for r in original["values"][z]for v in r),1)
            assert original["total_flux"]is None
        else:e.check("detector total W",original["total_flux"],1)
        file=str(e.folder/("detector."+extension))
        await e.call("save_detector_data",dict(request=dict(detector=2,path=file)))
        await e.call("clear_detectors",dict(request={}))
        await e.call("load_detector_data",dict(request=dict(detector=2,path=file)))
        loaded=await detector(e,2,**args)
        assert not loaded["history_known"]and not loaded["complete"]and loaded["loaded_sources"]
        await e.call("load_detector_data",dict(request=dict(detector=2,path=file,mode="accumulate")))
        accumulated=await detector(e,2,**args)
        if kind=="DetectorVolume":
            for z in range(4):e.check("loaded voxel accumulation W",sum(v for r in accumulated["values"][z] for v in r),2)
        else:e.check("loaded detector accumulation W",accumulated["total_flux"],2)
        if kind=="DetectorColor":
            for channel in ("photometric_flux","chromaticity_x","chromaticity_y","tristimulus_x","tristimulus_y","tristimulus_z"):
                values=await detector(e,2,color_channel=channel,width=10,height=10)
                (e.folder/(channel+".json")).write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding="utf-8")
        bad=e.folder/("invalid."+extension);bad.write_text("invalid native detector data",encoding="ascii")
        failure=await e.call("load_detector_data",dict(request=dict(detector=2,path=str(bad))),okay=False)
        assert not failure["ok"]and failure["error"]["code"]=="DETECTOR_LOAD_FAILED",failure
        assert failure["error"]["details"]["restored"]
        await e.call("save_lens_as",dict(path=str(e.folder/"detector.zos")))
    asyncio.run(execute("extended_"+kind,work))
