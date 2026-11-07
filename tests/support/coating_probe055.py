"""Capture coating phases on an owned constant-index single-layer fixture."""
import asyncio
import json
from pathlib import Path
import sys
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from support.native import execute

FILM='MATE MCP055_N138\n0.4 1.38 0\n0.8 1.38 0\nCOAT MCP055_FILM\nMCP055_N138 .25\n'


async def run():
    resource=Path.home()/'Documents/Zemax/Coatings'/('MCP055_'+uuid4().hex+'.DAT')
    resource.write_text(FILM,encoding='ascii')
    async def work(e):
        (e.folder/'fixture.DAT').write_text(FILM,encoding='ascii')
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],files=dict(coating_file=resource.name))))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',coating='MCP055_FILM',thickness=1,replace_solves=True)]))
        baseline=await e.call('get_system_settings')
        for metric in ['phase','retardance','diattenuation']:
            for axis in ['angle','wavelength']:
                request=dict(kind=metric+'_vs_'+axis,surface=1,
                    **(dict(minimum_angle=0,maximum_angle=70)if axis=='angle'else dict(angle=45,minimum_wavelength_um=.45,maximum_wavelength_um=.7)))
                result=await e.finish(await e.call('run_analysis',dict(request=request)))
                (e.folder/(request['kind']+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        assert await e.call('get_system_settings')==baseline
    try:await execute('coating_polarization_probe055',work)
    finally:resource.unlink()


if __name__=='__main__':asyncio.run(run())
