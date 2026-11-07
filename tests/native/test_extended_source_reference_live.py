"""Controlled finite-conjugate image of a uniform square source."""
import asyncio
import json
import uuid
from pathlib import Path

import pytest
import numpy as np
from tests.support.native import execute
from tests.support.extended_source_reference import square_energy


@pytest.mark.zemax
def test_extended_source_square_outlets():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(
            energy_atol=.01,source_pixels=257,source_full_width_mm=.02,image_magnification=-1,
            reference='uniform square image with half-width10 micrometers; circle/slit/square integrals',
            cumulative_bin_reference='enclosure radius=max(0,native reported position-maximum_distance/99)',
            rays_requested=100000),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=2,field_type='ObjectHeight',
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=200),
            dict(surface=1,surface_type='Paraxial',parameters={'1':100},thickness=200,semi_diameter=1,is_stop=True,replace_solves=True)]))
        resources=await e.call('get_system_resources',dict(request=dict(kind='geometric_image_files')))
        source=Path(resources['directory'])/('mcp326_square_'+uuid.uuid4().hex+'.IMA')
        source.write_text('257\n'+('9'*257+'\n')*257,encoding='ascii')
        records=[]
        try:
            for kind in ['Encircled','X_Only','Y_Only','Ensquared','X_Distrib','Y_Distrib']:
                q=dict(kind='extended_source_encircled_energy',image_name=source.name,data_type=kind,
                       field_size=.02,rays_x1000=100,reference='ChiefRay',maximum_distance=20)
                result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
                records.append(dict(request=q,result=result))
                (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert status['state']=='succeeded' and status['close_attempted']
                series=result['series'][0];x=np.asarray(series['x']);y=np.asarray(series['y'])[:,0]
                if kind.endswith('Distrib'):
                    cumulative=(np.cumsum(y)-.5*y)/y.sum()
                    expected=np.clip((x+10)/20,0,1)
                    e.check(kind+' integrated distribution',float(abs(cumulative-expected).max()),0,atol=.01,rtol=0)
                    e.check(kind+' peak normalization',float(y.max()),1,atol=1e-12,rtol=0)
                else:
                    edges=series['native_binning']['enclosure_radius_um']
                    e.check(kind+' analytic square through native bin edge',float(abs(y-square_energy(edges,kind)).max()),0,atol=.01,rtol=0)
            for maximum in [16,40]:
                q=dict(kind='extended_source_encircled_energy',image_name=source.name,data_type='X_Only',
                       field_size=.02,rays_x1000=100,reference='ChiefRay',maximum_distance=maximum)
                result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
                records.append(dict(request=q,result=result))
                (e.folder/'outlets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                series=result['series'][0]
                y=np.asarray(series['y'])[:,0]
                edges=series['native_binning']['enclosure_radius_um']
                e.check(str(maximum)+'um native bin-width scaling',series['native_binning']['interval_um'],maximum/99,atol=1e-10,rtol=0)
                e.check(str(maximum)+'um square slit energy',float(abs(y-square_energy(edges,'X_Only')).max()),0,atol=.01,rtol=0)
        finally:
            source.unlink(missing_ok=True)
    asyncio.run(execute('extended_source326_square',work))
