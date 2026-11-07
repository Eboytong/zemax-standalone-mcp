"""Observe cancellation while a multilayer coating analysis is active."""
import asyncio
import json
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('nsc',[False,True])
def test_multilayer_coating_cancellation(nsc):
    resource=Path.home()/'Documents/Zemax/Coatings'/('MCP160_nsc_cancel.DAT'if nsc else'MCP058_cancel.DAT')
    coating='MATE MCP058_H\n.55 2.1 0\nMATE MCP058_L\n.55 1.38 0\nCOAT MCP058_STACK\n'+''.join(f'MCP058_{"H" if i%2 else "L"} .25 0 0\n' for i in range(1000))
    resource.write_text(coating,encoding='ascii')
    async def work(e):
        (e.folder/resource.name).write_text(coating,encoding='ascii')
        if nsc:
            from support.nsc import setup,update
            await setup(e,1)
        else:await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],files=dict(coating_file=resource.name))))
        if nsc:await update(e,[dict(object=1,object_type='RectangularVolume',material='N-BK7',faces=[dict(face=1,coating='MCP058_STACK')])])
        else:await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',coating='MCP058_STACK',replace_solves=True)]))
        before=await e.call('get_system_settings');surfaces=await e.call('get_nsc_objects',dict(request={}))if nsc else await e.call('get_surfaces',dict(start=0,count=3))
        target=dict(surface=0,nsc_object=1,nsc_face=1)if nsc else dict(surface=1)
        task=await e.call('run_analysis',dict(request=dict(kind='phase_vs_wavelength',**target,angle=45,minimum_wavelength_um=.45,maximum_wavelength_um=.7)))
        active=task['state'] not in {'succeeded','failed','cancelled'}
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        for _ in range(1000):
            if task['state'] in {'succeeded','failed','cancelled'}:break
            await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']==('cancelled' if active else 'succeeded'),task
        assert task['close_attempted']
        (e.folder/'cancellation.json').write_text(json.dumps(dict(active_at_request=active,terminal=task['state'],closed=task['close_attempted'])),encoding='utf-8')
        await e.call('get_task_result',dict(task_id=task['task_id']))
        assert await e.call('get_system_settings')==before
        assert (await e.call('get_nsc_objects',dict(request={}))if nsc else await e.call('get_surfaces',dict(start=0,count=3)))==surfaces
        # A fresh analysis verifies the cancelled task released its native owner.
        if nsc:target['nsc_face']=0
        else:await e.call('update_surfaces',dict(changes=[dict(surface=1,coating='')]))
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='reflection_vs_angle',**target))))
    try:asyncio.run(execute('coating_cancel160_nsc'if nsc else'coating_cancel058',work))
    finally:resource.unlink(missing_ok=True)
