"""Installed STL vertices supply an independent mirror-intersection reference."""
import asyncio,json
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_installed_stl_intersection_native():
    async def work(e):
        source=Path.home()/"Documents/Zemax/Objects/CAD Files/block.stl"
        vertices=[list(map(float,line.split()[1:]))for line in source.read_text(encoding="ascii").splitlines()if line.strip().startswith("vertex ")]
        bounds=[[min(v[i]for v in vertices),max(v[i]for v in vertices)]for i in range(3)]
        x=bounds[0][0]+.3*(bounds[0][1]-bounds[0][0]);y=bounds[1][0]+.4*(bounds[1][1]-bounds[1][0])
        await setup(e,3)
        await update(e,[dict(object=1,object_type="SourceRay",x=x,y=y,data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type="CADPartSTL",file1="block.stl",material="MIRROR"),
            dict(object=3,object_type="DetectorRectangle",x=x,y=y,z=-2,material="ABSORB",data=dict(XHalfWidth=2,YHalfWidth=2,NumberXPixels=8,NumberYPixels=8))])
        _,segments=await trace(e,"stl",use_polarization=True)
        hit=next(r for r in segments if r["HitObject"]==2)
        for key,value in (("X",x),("Y",y),("Z",bounds[2][0])):e.check("STL front intersection "+key,hit[key],value)
        outgoing=next(r for r in segments if r["HitObject"]==3)
        for key,value in (("L",0),("M",0),("N",-1)):e.check("STL reflected "+key,outgoing[key],value)
        detected=(await detector(e,3))["total_flux"]
        e.check("STL detector/ZRD branch power W",detected,sum(r["Intensity"]for r in segments if r["HitObject"]==3))
        path=str(e.folder/"stl.zos")
        await e.call("save_lens_as",dict(path=path));await e.call("open_lens",dict(path=path))
        objects=await e.call("get_nsc_objects",dict(request={}))
        assert objects["rows"][1]["file1"]=="block.stl"
        (e.folder/"cad_reference.json").write_text(json.dumps(dict(input=str(source),vertex_bounds_mm=bounds,
            reference="axis-aligned closed six-face block from installed ASCII STL vertices",detected_W=detected,
            power_reference="detector and ZRD branch correspondence; no ideal-unit-reflectance assumption",
            scope="STL; other CAD formats require their own geometric reference"),indent=2),encoding="utf-8")
    asyncio.run(execute("installed_stl_reference",work))
