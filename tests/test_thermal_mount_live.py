"""Tilted mounting interval: local thermal expansion transformed to global axes."""
import asyncio,json,math
import pytest
from support.native import execute


@pytest.mark.zemax
def test_tilted_thermal_mount_spacing_native():
    async def work(e):
        await e.model();await e.call("insert_surfaces",dict(at=2,count=2))
        await e.call("update_system_settings",dict(settings=dict(adjust_index_to_environment=True,global_reference_surface=1)))
        await e.call("update_surfaces",dict(changes=[dict(surface=2,surface_type="CoordinateBreak",parameters={4:5},thickness=0,replace_solves=True),
            dict(surface=3,radius=50,thickness=10,tce=100,semi_diameter=3,replace_solves=True)]))
        await e.call("update_configurations",dict(request=dict(actions=[dict(action="add",copy_current=True)],operands=[
            dict(type="TEMP",cells=[dict(configuration=1,value=20),dict(configuration=2,value=30)]),
            dict(type="THIC",parameters={1:3},cells=[dict(configuration=1,value=10),dict(configuration=2,value=10)])])))
        row=(await e.call("get_configurations",dict(request={})))["rows"][-1]["operand"]
        await e.call("update_configurations",dict(request=dict(operands=[dict(operand=row,cells=[dict(configuration=2,solve=dict(mode="thermal_pickup",configuration=1))])])))
        c,s=math.cos(math.radians(5)),math.sin(math.radians(5));rotation=[[c,0,s],[0,1,0],[-s,0,c]]
        records=[]
        for configuration,temperature in ((1,20),(2,30)):
            await e.call("set_configuration",dict(configuration=configuration))
            scale=1+100e-6*(temperature-20)
            sag=lambda radius:radius*radius/(50+math.sqrt(50*50-radius*radius))
            # Air-space thermal pickup expands the mounting edge, including
            # its radial contact position; the front datum is curved.
            length=(10-sag(3))*scale+sag(3*scale)
            actual=(await e.call("get_surfaces",dict(start=3,count=1)))["surfaces"][0]["cells"]["thickness"]["value"]
            e.check("tilted mount local spacing mm",actual,length)
            geometry=await e.call("get_surface_geometry",dict(request=dict(surface=4)))
            assert geometry["global_reference_surface"]==1
            transform=geometry["global_transform"];assert geometry["global_transform_valid"]
            for i in range(3):
                for j in range(3):e.check("tilted mount signed matrix",transform["rotation"][i][j],rotation[i][j])
            for i,value in enumerate((s*length,0,c*length)):e.check("thermal global endpoint mm",transform["translation"][i],value)
            records.append(dict(configuration=configuration,temperature_c=temperature,length_mm=length,transform=transform))
        path=str(e.folder/"tilted_mount.zos")
        await e.call("save_lens_as",dict(path=path));await e.call("open_lens",dict(path=path))
        after=await e.call("get_surface_geometry",dict(request=dict(surface=4)))
        for i,value in enumerate(records[-1]["transform"]["translation"]):e.check("reloaded thermal endpoint mm",after["global_transform"]["translation"][i],value)
        (e.folder/"thermal_mount_reference.json").write_text(json.dumps(dict(cte_ppm_per_C=100,rotation_degrees_y=5,
            nominal_contact_radius_mm=3,front_radius_mm=50,rear_datum="plane",
            reference="manual 2.1.1.4.4.2: L=(L0-sag(r0))*scale+sag(r0*scale); global endpoint=Ry(5deg)*(0,0,L)",records=records,
            scope="tilted mounting interval and curved datum; no thermoelastic deformation of an optical element is inferred"),indent=2),encoding="utf-8")
    asyncio.run(execute("tilted_thermal_mount",work))
