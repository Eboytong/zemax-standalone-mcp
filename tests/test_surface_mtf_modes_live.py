import asyncio,json,math
from pathlib import Path
import pytest
from support.native import execute


def circular_mtf(v):
    return 0 if v>=1 else 2/math.pi*(math.acos(v)-v*math.sqrt(1-v*v))


@pytest.mark.zemax
@pytest.mark.parametrize('family,pupil,image,delta',[
    ('fft',128,256,10),('fft',256,256,10),('fft',512,256,10),
    ('huygens',256,256,10),('huygens',256,512,5),('huygens',512,512,5),
])
def test_surface_mtf_circular_pupil_and_complex_identity(family,pupil,image,delta):
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(aperture_value=1,fields=[dict(x=0,y=0),dict(x=0,y=1)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',is_stop=True,parameters={'1':100},thickness=100,semi_diameter=.5,replace_solves=True),dict(surface=2,semi_diameter=5,replace_solves=True)]))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces');records={}
        for mtf_type in ['MTF_Incoherent','Real_Incoherent','Imaginary_Incoherent','MTF_Coherent','Real_Coherent','Imaginary_Coherent']:
            q=dict(kind=family+'_surface_mtf',field=1,wavelength=1,sampling=f'S_{pupil}x{pupil}',mtf_type=mtf_type)
            if family=='huygens':q.update(image_sampling=f'S_{image}x{image}',image_delta=delta)
            records[mtf_type]=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
            (e.folder/'modes.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        g=records['MTF_Incoherent']['grids'][0];cx=g['zero_frequency_index']['x'];cy=g['zero_frequency_index']['y'];fc=1/(.00055*100)
        points=[]
        for fraction in [0,.15,.3,.5,.7,.85]:points.append((cx+round(fc*fraction/g['dx']),cy))
        points += [(cx+round(.3*fc/g['dx']),cy+round(.4*fc/g['dy'])),(cx-round(.3*fc/g['dx']),cy-round(.4*fc/g['dy']))]
        failures=[]
        def compare(*args,**kwargs):
            try:e.check(*args,**kwargs)
            except AssertionError:failures.append(e.checks[-1])
        for x,y in points:
            fx=g['min_x']+x*g['dx'];fy=g['min_y']+y*g['dy']
            compare('circular pupil incoherent '+family,g['values'][y][x],circular_mtf(math.hypot(fx,fy)/fc),atol=.005,rtol=0)
        for suffix in ['Incoherent','Coherent']:
            magnitude=records['MTF_'+suffix]['grids'][0]['values'];real=records['Real_'+suffix]['grids'][0]['values'];imag=records['Imaginary_'+suffix]['grids'][0]['values']
            for x,y in points:compare('complex identity '+family+suffix,magnitude[y][x],math.hypot(real[y][x],imag[y][x]),atol=1e-8,rtol=1e-7)
        (e.folder/'comparison-summary.json').write_text(json.dumps(dict(family=family,pupil=pupil,image=image,image_delta_um=delta,checks=e.checks,failures=failures),indent=2),encoding='utf-8')
        assert await e.call('get_system_settings')==baseline and await e.call('get_surfaces')==surfaces
        for result in records.values():assert (await e.call('get_task_status',dict(task_id=result['task']['task_id'])))['close_attempted']
        await e.call('disconnect')
        assert not failures,failures
    asyncio.run(execute(f'surface_mtf092_{family}_{pupil}_{image}_{delta}',work))
