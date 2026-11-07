import asyncio
import json
import math
import sys
from pathlib import Path
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from zemax_mcp.config import PROJECT_ROOT
from support.paths import run_dir

@pytest.mark.zemax
def test_modeling_over_stdio():
    async def scenario():
        output=run_dir("modeling")
        events=[]
        params=StdioServerParameters(command=sys.executable,args=["-B","-m","zemax_mcp"],cwd=PROJECT_ROOT,env={"PYTHONUTF8":"1","ZEMAX_OUTPUT_DIR":str(output)})
        try:
            async with Client(params,read_timeout_seconds=120) as client:
                async def call(name,args=None):
                    result=(await client.call_tool(name,args or {})).structured_content
                    events.append(dict(tool=name,arguments=args,response=result))
                    assert result and result["ok"], result
                    return result["data"]
                await call("connect")
                await call("open_lens",{"path":str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")})
                original=await call("get_system_settings")
                await call("get_capabilities")
                await call("update_system_settings",{"settings":{"material_catalogs":original["material_catalogs"]+["CORNING"]}})
                await call("update_system_settings",{"settings":{"material_catalogs":original["material_catalogs"]}})
                for kind in ("catalogs","coatings","coating_files","scatter_profiles","abg_files","gradium_profiles"):
                    await call("get_system_resources",{"request":{"kind":kind,"count":2}})
                await call("get_system_resources",{"request":{"kind":"materials","catalog":"SCHOTT","query":"BK7"}})
                await call("update_system_settings",{"settings":{"material_catalogs":original["material_catalogs"],"polarization":{"unpolarized":False,"jx":1,"jy":0,"x_phase":0,"y_phase":90,"method":"YAxisMethod","convert_thin_film_phase":False},"ray_aiming":{"mode":"Paraxial","method":"Heuristic","cache":False,"robust":False},"field_normalization":"Rectangular","field_updates":[{"number":1,"vdx":0.01,"vdy":0.02,"vcx":0.03,"vcy":0.04,"van":5}],"files":{"coating_file":original["files"]["coating_file"]}}})
                changed=await call("get_system_settings")
                assert changed["fields"][0]["vdx"]==pytest.approx(.01)
                await call("update_surfaces",{"changes":[{"surface":1,"radius":50,"replace_solves":True,"coating":"","aperture":{"type":"CircularAperture","maximum_radius":10}}]})
                geometry=await call("get_surface_geometry",{"request":{"surface":1,"points":[{"x":3,"y":0}]}})
                assert geometry["rows"][0]["sag"]==pytest.approx(50-math.sqrt(2500-9),rel=1e-7,abs=1e-8),geometry
                await call("update_surfaces",{"changes":[{"surface":2,"tilt_decenter":{"before_decenter_x":2,"before_tilt_y":5}}]})
                transform=(await call("get_surface_geometry",{"request":{"surface":2}}))["global_transform"]
                assert transform["rotation"][0][0]==pytest.approx(math.cos(math.radians(5)),rel=1e-7,abs=1e-8),transform
                assert abs(transform["rotation"][0][2])==pytest.approx(math.sin(math.radians(5)),rel=1e-7,abs=1e-8),transform
                for surface_type in ("OddAsphere","Toroidal","Biconic","Paraxial","Standard"):
                    await call("update_surfaces",{"changes":[{"surface":2,"surface_type":surface_type,"replace_solves":True}]})
                rows=(await call("get_surfaces",{"start":1,"count":3}))["surfaces"]
                assert "available_solves" in rows[0]["cells"]["thickness"]
                for mode,surface,cell,extra in (("marginal_ray_height",6,"thickness",{"height":0}), ("chief_ray_height",6,"thickness",{"height":0}), ("edge_thickness",1,"thickness",{"thickness":2,"radial_height":1}), ("position",6,"thickness",{"source_surface":1,"length":50})):
                    await call("update_surfaces",{"changes":[{"surface":surface,"replace_solves":True,"solves":{cell:{"mode":mode,**extra}}}]})
                    await call("get_surfaces",{"start":surface,"count":1})
                    await call("update_surfaces",{"changes":[{"surface":surface,"replace_solves":True,"solves":{cell:{"mode":"fixed"}}}]})
                await call("update_surfaces",{"changes":[{"surface":2,"surface_type":"CoordinateBreak","replace_solves":True,"solves":{"parameter_1":{"mode":"pickup_chief_ray","field":1,"wavelength":1}}}]})
                await call("get_surfaces",{"start":2,"count":1})
                await call("update_surfaces",{"changes":[{"surface":2,"surface_type":"Standard","replace_solves":True}]})
                for aperture in ({"type":"RectangularAperture","x_half_width":5,"y_half_width":4},{"type":"EllipticalObscuration","x_half_width":1,"y_half_width":1},{"type":"None"}):
                    await call("update_surfaces",{"changes":[{"surface":2,"aperture":aperture}]})
                await call("update_surfaces",{"changes":[{"surface":2,"aperture":{"pickup_from":1}}]})
                await call("update_surfaces",{"changes":[{"surface":2,"aperture":{"type":"None","replace_pickup":True}}]})
                copied=await call("copy_surfaces",{"request":{"start":1,"count":1,"at":2}})
                after=(await call("get_surfaces",{"start":1,"count":7}))["surfaces"]
                assert [r["surface"] for r in after if r["is_stop"]]==[copied["stop_surface"]]
                path=str(output/"design.zos")
                await call("save_lens_as",{"path":path})
                await call("open_lens",{"path":path})
                loaded=await call("get_system_settings")
                assert loaded["polarization"]==changed["polarization"]
                assert loaded["fields"][0]["vdx"]==pytest.approx(.01)
                await call("disconnect")
        finally:
            (output/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
            print("Modeling evidence:",output,flush=True)
    asyncio.run(scenario())
