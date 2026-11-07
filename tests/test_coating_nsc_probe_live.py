"""Controlled mixed-mode plate and formal face discovery for coating scans."""
import asyncio
import pytest
from support.native import execute


async def mixed_plate(e):
    await e.model()
    await e.call('insert_surfaces',dict(at=2,count=3))
    await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'])))
    await e.call('update_surfaces',dict(changes=[dict(surface=2,material='N-BK7',thickness=5,semi_diameter=5,replace_solves=True),dict(surface=3,thickness=0,semi_diameter=5,replace_solves=True),dict(surface=4,thickness=10)]))
    converted=await e.finish(await e.call('run_nsc_conversion',dict(request=dict(first_surface=1,last_surface=4))))
    surface=converted['after']['nsc_groups'][0]
    objects=await e.call('get_nsc_objects',dict(request=dict(nsc_surface=surface,start=1,count=20)))
    return surface,objects


@pytest.mark.zemax
def test_mixed_plate_coating_face_discovery():
    async def work(e):
        await mixed_plate(e)
    asyncio.run(execute('coating_nsc060_probe',work))
