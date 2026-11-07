"""Nonzero-mean display identity, elliptical mask and serial task recovery."""
import asyncio
import json
import math
import time
from pathlib import Path

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_full_field_display_defocus_reference():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        q=dict(kind='full_field_aberration',field=1,wavelength=1,x_field_width=4,y_field_width=2,
               x_field_sampling=7,y_field_sampling=5,pupil_sampling='S_64x64',maximum_term=15,aberration_type='Defocus')
        records=[]
        for shape in ['Rectangular','Elliptical']:
            for display in ['Absolute','Relative','Average']:
                request=q|dict(field_shape=shape,display=display)
                result=await e.finish(await e.call('run_analysis',dict(request=request)))
                records.append(dict(request=request,result=result))
                (e.folder/'displays.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                status=await e.call('get_task_status',dict(task_id=result['task']['task_id']))
                assert status['state']=='succeeded' and status['close_attempted']
            selected=[r['result']['grids'][0] for r in records if r['request']['field_shape']==shape]
            absolute,relative,average=selected
            values=[v for row in absolute['values'] for v in row if v is not None]
            mean=sum(values)/len(values)
            assert abs(mean)>.1
            for iy,row in enumerate(absolute['values']):
                for ix,value in enumerate(row):
                    if value is None:
                        assert relative['values'][iy][ix] is None and average['values'][iy][ix] is None
                        continue
                    e.check(f'{shape} relative [{iy},{ix}]',relative['values'][iy][ix],value-mean,atol=1e-10,rtol=1e-8)
                    e.check(f'{shape} average [{iy},{ix}]',average['values'][iy][ix],mean,atol=1e-10,rtol=1e-8)
            if shape=='Elliptical':
                masked=0
                for iy,row in enumerate(absolute['values']):
                    for ix,value in enumerate(row):
                        x=absolute['min_x']+ix*absolute['dx'];y=absolute['min_y']+iy*absolute['dy']
                        outside=(x/4)**2+(y/2)**2>1+1e-12
                        assert (value is None)==outside,(x,y,value)
                        masked+=outside
                assert masked==absolute['invalid_count']==16
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
    asyncio.run(execute('full_field293_displays',work))


@pytest.mark.zemax
def test_full_field_selection_units_and_lifecycle():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        q=dict(kind='full_field_aberration',field=2,wavelength=2,x_field_width=2,y_field_width=1,
               x_field_sampling=7,y_field_sampling=5,pupil_sampling='S_64x64',maximum_term=15,aberration_type='Defocus')
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'selected.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        grid=result['grids'][0];native=result['task']['settings']['native']
        assert native['Field']==2 and native['Wavelength']==2
        e.check('reference field center X degrees',grid['min_x']+3*grid['dx'],0,atol=1e-10,rtol=0)
        e.check('reference field center Y degrees',grid['min_y']+2*grid['dy'],14,atol=1e-10,rtol=0)
        single=await e.finish(await e.call('run_analysis',dict(request=dict(kind='zernike_standard',field=2,wavelength=2,sampling='S_64x64',maximum_terms=15))))
        coefficient=next(r['value']for r in single['rows']if r['term']==4)
        e.check('reference field/wavelength Standard defocus',grid['values'][2][3],coefficient,atol=1e-8,rtol=1e-7)
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,x_start=1,y_start=1,width=4,height=3))
        assert page['grid']['values']==[row[1:5]for row in grid['values'][1:4]]
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'full-field.png'))))
        invalid=await e.call('run_analysis',dict(request=q|dict(field=999)),okay=False)
        assert invalid['error']['code']=='INDEX_OUT_OF_RANGE'
        task=await e.call('run_analysis',dict(request=q|dict(x_field_sampling=100,y_field_sampling=100,pupil_sampling='S_256x256')))
        assert task['state']=='running'
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+90
        while task['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.05);task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled' and task['close_attempted'],task
        await e.call('get_task_result',dict(task_id=task['task_id']))
        await e.finish(await e.call('run_analysis',dict(request=q)))
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        saved=str(e.folder/'reloaded.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        await e.finish(await e.call('run_analysis',dict(request=q)))
        # Finite conjugate with physical ObjectHeight field units in centimeters.
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(lens_units='Centimeters',field_type='ObjectHeight',
            aperture_value=.1,wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0),dict(x=.2,y=.1)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=10),
            dict(surface=1,surface_type='Paraxial',parameters={'1':5},thickness=10,semi_diameter=.05,is_stop=True,replace_solves=True)]))
        finite=await e.finish(await e.call('run_analysis',dict(request=q|dict(field=1,wavelength=1,x_field_width=.2,y_field_width=.1))))
        (e.folder/'finite.json').write_text(json.dumps(finite,ensure_ascii=False,indent=2),encoding='utf-8')
        g=finite['grids'][0]
        assert g['x_unit']==g['y_unit']=='Centimeters' and g['value_unit']=='waves'
        e.check('finite field left endpoint cm',g['min_x'],-.2,atol=1e-10,rtol=0)
        e.check('finite field bottom endpoint cm',g['min_y'],-.1,atol=1e-10,rtol=0)
        assert g['invalid_count']==0
    asyncio.run(execute('full_field294_lifecycle',work))
