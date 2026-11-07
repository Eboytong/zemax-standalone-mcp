"""Point-source limit and native circular-pupil diffraction correction."""
import asyncio
import json
import uuid
from pathlib import Path

import numpy as np
import pytest
from tests.support.native import execute
from tests.support.extended_source_reference import airy_energy


@pytest.mark.zemax
def test_extended_source_point_and_diffraction_outlets():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(energy_atol=.01,
            reference='point limit versus independent standard geometric energy; Airy energy from angular Bessel quadrature',
            source_full_width_mm=1e-6),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=2,field_type='ObjectHeight',
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=200),
            dict(surface=1,surface_type='Paraxial',parameters={'1':100},thickness=200.1,semi_diameter=1,is_stop=True,replace_solves=True)]))
        resources=await e.call('get_system_resources',dict(request=dict(kind='geometric_image_files')))
        source=Path(resources['directory'])/('mcp329_point_'+uuid.uuid4().hex+'.IMA')
        lines=['0'*33 for _ in range(33)];lines[16]='0'*16+'9'+'0'*16
        source.write_text('33\n'+'\n'.join(lines)+'\n',encoding='ascii')
        records=[]
        try:
            q=dict(kind='extended_source_encircled_energy',image_name=source.name,field_size=1e-6,
                   rays_x1000=100,reference='ChiefRay',maximum_distance=2)
            extended=await e.finish(await e.call('run_analysis',dict(request=q)))
            standard=await e.finish(await e.call('run_analysis',dict(request=dict(kind='geometric_encircled_energy',
                sampling='S_1024x1024',reference='ChiefRay',maximum_radius=2,multiply_by_diffraction_limit=False))))
            records.append(dict(extended=extended,standard=standard))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            a=extended['series'][0];b=standard['series'][0]
            expected=np.interp(a['native_binning']['enclosure_radius_um'],b['x'],np.asarray(b['y'])[:,0])
            e.check('point limit standard geometric energy',float(abs(np.asarray(a['y'])[:,0]-expected).max()),0,atol=.01,rtol=0)
            automatic=await e.finish(await e.call('run_analysis',dict(request=q|dict(maximum_distance=0))))
            series=automatic['series'][0]
            expected=np.interp(series['native_binning']['enclosure_radius_um'],b['x'],np.asarray(b['y'])[:,0])
            records.append(dict(automatic=automatic))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            e.check('point limit automatic distance',float(abs(np.asarray(series['y'])[:,0]-expected).max()),0,atol=.01,rtol=0)
            await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=200,replace_solves=True)]))
            summary=await e.call('get_system_summary')
            raw=await e.finish(await e.call('run_analysis',dict(request=q|dict(maximum_distance=200))))
            corrected=await e.finish(await e.call('run_analysis',dict(request=q|dict(maximum_distance=200,multiply_by_diffraction_limit=True))))
            series=corrected['series'][0];x=np.asarray(series['x']);actual=np.asarray(series['y'])[:,0]
            geometric=np.asarray(raw['series'][0]['y'])[:,0]
            edges=np.asarray(series['native_binning']['enclosure_radius_um'])
            expected=geometric*airy_energy(edges,.55,summary['first_order']['real_working_f_number'])
            records.append(dict(raw=raw,corrected=corrected,summary=summary,expected=expected.tolist()))
            (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
            e.check('native diffraction correction Airy reference',float(abs(actual-expected).max()),0,atol=.01,rtol=0)
        finally:
            source.unlink(missing_ok=True)
    asyncio.run(execute('extended_source329_point',work))
