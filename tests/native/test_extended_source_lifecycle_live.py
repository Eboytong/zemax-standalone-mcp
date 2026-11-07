"""Rotation, angle-field selection and serial extended-energy lifecycle."""
import asyncio
import json
import time
import uuid
from pathlib import Path

import numpy as np
from PIL import Image
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_extended_source_rotation_and_lifecycle():
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=2,field_type='ObjectHeight',
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=200),
            dict(surface=1,surface_type='Paraxial',parameters={'1':100},thickness=200,semi_diameter=1,is_stop=True,replace_solves=True)]))
        resources=await e.call('get_system_resources',dict(request=dict(kind='geometric_image_files')))
        source=Path(resources['directory'])/('mcp332_stripe_'+uuid.uuid4().hex+'.IMA')
        source.write_text('257\n'+''.join(('9' if 96<=y<=160 else '0')*257+'\n' for y in range(257)),encoding='ascii')
        try:
            records=[]
            for rotation,kind in [(0,'X_Only'),(0,'Y_Only'),(90,'X_Only'),(90,'Y_Only')]:
                q=dict(kind='extended_source_encircled_energy',image_name=source.name,data_type=kind,
                       field_size=.02,rays_x1000=100,reference='ChiefRay',maximum_distance=20,rotation=rotation)
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                records.append(dict(request=q,result=result))
                (e.folder/'rotations.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            curves=[np.asarray(r['result']['series'][0]['y'])[:,0] for r in records]
            e.check('stripe rotation X0 equals Y90',float(abs(curves[0]-curves[3]).max()),0,atol=.01,rtol=0)
            e.check('stripe rotation Y0 equals X90',float(abs(curves[1]-curves[2]).max()),0,atol=.01,rtol=0)
            assert float(abs(curves[0]-curves[1]).max())>.5
            await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
            baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
            q=dict(kind='extended_source_encircled_energy',image_name=source.name,field=2,wavelength=2,
                   field_size=.2,rays_x1000=100,reference='Centroid',maximum_distance=100,
                   use_polarization=True,remove_vignetting_factors=False,use_dashes=True)
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            (e.folder/'selected.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            native=result['task']['settings']['native']
            assert native['Field']==2 and native['Wavelength']==2 and native['UsePolarization'] is True
            assert native['RemoveVignettingFactors'] is False and native['UseDashes'] is True
            assert result['extended_source_conditions']['field_size_unit']=='degrees'
            curve=result['series'][0]
            page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,start=3,count=7))
            assert page['series'][0]['x']==curve['x'][3:10] and page['series'][0]['y']==curve['y'][3:10]
            assert page['series'][0]['native_x']==curve['native_x'][3:10]
            assert page['series'][0]['native_binning']['enclosure_radius_um']==curve['native_binning']['enclosure_radius_um'][3:10]
            png=e.folder/'extended-energy.png'
            await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(png))))
            with Image.open(png) as bitmap:assert bitmap.width>0 and bitmap.height>0
            for reference in ['Vertex','ChiefRay']:
                await e.finish(await e.call('run_analysis',dict(request=q|dict(wavelength=0,reference=reference))))
            for patch,code in [(dict(field=999),'INDEX_OUT_OF_RANGE'),(dict(image_name='missing_mcp_source.IMA'),'INVALID_RESOURCE')]:
                error=await e.call('run_analysis',dict(request=q|patch),okay=False)
                assert error['error']['code']==code,error
            task=await e.call('run_analysis',dict(request=q|dict(rays_x1000=10000)))
            assert task['state']=='running'
            task=await e.call('cancel_task',dict(task_id=task['task_id']))
            deadline=time.monotonic()+90
            while task['state']not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.05);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']=='cancelled' and task['close_attempted'],task
            await e.call('get_task_result',dict(task_id=task['task_id']))
            await e.finish(await e.call('run_analysis',dict(request=q)))
            async def unchanged():
                assert await e.call('get_surfaces')==baseline
                assert await e.call('get_system_settings')==settings
                assert await e.call('get_merit_function')==merit
            await unchanged()
            saved=str(e.folder/'reloaded.zos')
            await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
            await unchanged()
            await e.finish(await e.call('run_analysis',dict(request=q)))
        finally:
            source.unlink(missing_ok=True)
    asyncio.run(execute('extended_source332_lifecycle',work))
