"""Unequal edge-contact expansions and signed relative mount rotations."""
import asyncio
import json
import math
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_unequal_curved_mounts_relative_tilt_native():
    async def work(e):
        import numpy as np
        await e.model();await e.call("insert_surfaces",dict(at=2,count=5))
        await e.call("update_system_settings",dict(settings=dict(global_reference_surface=1,temperature_c=20,adjust_index_to_environment=True)))
        await e.call("update_surfaces",dict(changes=[
            dict(surface=2,surface_type="CoordinateBreak",parameters={4:5},thickness=0,replace_solves=True),
            dict(surface=3,radius=50,semi_diameter=3,thickness=10,tce=100,replace_solves=True),
            dict(surface=4,thickness=0,semi_diameter=3,replace_solves=True),
            dict(surface=5,surface_type="CoordinateBreak",parameters={3:-3},thickness=0,replace_solves=True),
            dict(surface=6,radius=70,semi_diameter=2,thickness=7,tce=50,replace_solves=True)]))
        await e.call("update_configurations",dict(request=dict(actions=[dict(action="add",copy_current=True)],operands=[
            dict(type="TEMP",cells=[dict(configuration=1,value=20),dict(configuration=2,value=50)]),
            dict(type="THIC",parameters={1:3},cells=[dict(configuration=1,value=10),dict(configuration=2,value=10)]),
            dict(type="THIC",parameters={1:6},cells=[dict(configuration=1,value=7),dict(configuration=2,value=7)])])))
        rows=(await e.call("get_configurations",dict(request={})))["rows"]
        for row in rows[-2:]:
            await e.call("update_configurations",dict(request=dict(operands=[dict(operand=row["operand"],cells=[dict(configuration=2,solve=dict(mode="thermal_pickup",configuration=1))])])) )
        a,b=map(math.radians,(5,-3))
        ry=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
        rx=np.array([[1,0,0],[0,math.cos(b),-math.sin(b)],[0,math.sin(b),math.cos(b)]])
        rotation=ry@rx;records=[]
        for configuration,temperature in ((1,20),(2,50)):
            await e.call("set_configuration",dict(configuration=configuration))
            lengths=[]
            for surface,L,R,r,cte in ((3,10,50,3,100),(6,7,70,2,50)):
                scale=1+cte*1e-6*(temperature-20)
                sag=lambda h:h*h/(R+math.sqrt(R*R-h*h))
                expected=(L-sag(r))*scale+sag(r*scale)
                actual=(await e.call("get_surfaces",dict(start=surface,count=1)))["surfaces"][0]["cells"]["thickness"]["value"]
                e.check(f"asymmetric mount {surface} spacing mm",actual,expected);lengths.append(expected)
            geom=await e.call("get_surface_geometry",dict(request=dict(surface=7)))
            transform=geom["global_transform"];point=ry@np.array([0,0,lengths[0]])+rotation@np.array([0,0,lengths[1]])
            for i in range(3):
                for j in range(3):e.check("relative mount rotation",transform["rotation"][i][j],float(rotation[i,j]))
                e.check("asymmetric thermal endpoint mm",transform["translation"][i],float(point[i]))
            records.append(dict(configuration=configuration,temperature_C=temperature,lengths_mm=lengths,expected_translation_mm=point.tolist(),actual=transform))
        path=e.folder/"asymmetric_mounts.zos";await e.call("save_lens_as",dict(path=str(path)));await e.call("open_lens",dict(path=str(path)))
        geom=await e.call("get_surface_geometry",dict(request=dict(surface=7)))
        for i,v in enumerate(records[-1]["expected_translation_mm"]):e.check("reloaded endpoint mm",geom["global_transform"]["translation"][i],v)
        (e.folder/"thermal-reference.json").write_text(json.dumps(dict(records=records,
            reference="manual curved-front/planar-rear edge contact formula, separate CTE100/50ppm/C, signed Ry(5)Rx(-3)",
            scope="two unequal mount intervals; no thermoelastic stress or arbitrary mechanical contact model"),indent=2),encoding="utf-8")
    asyncio.run(execute("thermal_asymmetric",work))
