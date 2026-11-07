import asyncio
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_field_diagnostics_stdio():
    async def work(e):
        sample=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens',dict(path=str(sample)))
        results={}
        for kind in ('relative_illumination','fft_mtf_vs_field'):
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind=kind,**({'sampling':'S_256x256'} if kind=='fft_mtf_vs_field' else {})))))
            assert result.get('series'),result
            assert result['computation_method']=='native_analysis'
            results[kind]=result
        # Compare the on-axis field curve against the independently requested MTF.
        single=await e.finish(await e.call('run_fft_mtf',dict(field=1,wavelength=1,sampling='S_256x256',maximum_frequency=50)))
        from zemax_mcp.evaluation import interpolate
        field=results['fft_mtf_vs_field']
        e.check('RI maximum',max(row[0] for s in results['relative_illumination']['series'] for row in s['y']),1,atol=1e-6)
        assert single['series'] and field['series']
        for curve in field['series']:
            for column in range(2):
                expected=interpolate(single['series'][0]['x'],[r[column] for r in single['series'][0]['y']],curve['frequency'])
                e.check('on axis MTF '+str(curve['frequency']),curve['y'][0][column],expected,atol=.005)
        finer=await e.finish(await e.call('run_analysis',dict(request=dict(kind='relative_illumination',ray_density=20))))
        for a,b in zip(results['relative_illumination']['series'][0]['y'],finer['series'][0]['y']):
            e.check('RI sampling convergence',a[0],b[0],atol=.02)
        await e.model()
        footprint=await e.finish(await e.call('run_analysis',dict(request=dict(kind='footprint',surface=1))))
        assert footprint['scatter'][0]['points']
        for row in footprint['rows']:
            if row['visible']:
                e.check('plane X',row['position'][0],5*row['input']['px'])
                e.check('plane Y',row['position'][1],5*row['input']['py'])
        await e.call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(type='CircularAperture',maximum_radius=2.5))]))
        vignette=await e.finish(await e.call('run_analysis',dict(request=dict(kind='vignetting',ray_density=40,field_density=2))))
        for y in vignette['series'][0]['y']:e.check('quarter pupil area',y[0],.25,atol=.01)
        assert vignette['restoration']['restored']
        await e.call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(type='CircularAperture',maximum_radius=5))]))
        await e.call('insert_surfaces',dict(at=2))
        await e.call('update_surfaces',dict(changes=[dict(surface=2,semi_diameter=5,replace_solves=True,aperture=dict(type='CircularAperture',maximum_radius=2.5))]))
        for delete in (False,True):
            data=await e.finish(await e.call('run_analysis',dict(request=dict(kind='footprint',surface=1,delete_vignetted=delete))))
            fraction=sum(r['visible'] for r in data['rows'])/len(data['rows'])
            e.check('subsequent clip '+str(delete),fraction,.25 if delete else 1.,atol=.03)
        await e.call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(type='CircularAperture',maximum_radius=2.5))]))
        prior=await e.finish(await e.call('run_analysis',dict(request=dict(kind='footprint',surface=2,delete_vignetted=False))))
        e.check('prior clip',sum(r['visible'] for r in prior['rows'])/len(prior['rows']),.25,atol=.03)
        await e.call('update_surfaces',dict(changes=[dict(surface=1,aperture=dict(type='CircularAperture',maximum_radius=5)),dict(surface=2,tilt_decenter=dict(before_decenter_x=1))]))
        shifted=await e.finish(await e.call('run_analysis',dict(request=dict(kind='footprint',surface=2,delete_vignetted=False))))
        for row in shifted['rows']:
            if row['visible']:e.check('decenter local X',row['position'][0],5*row['input']['px']-1)
        out=e.folder/'footprint.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=footprint['task']['task_id'],path=str(out))))
    asyncio.run(execute('field_diagnostics',work))
