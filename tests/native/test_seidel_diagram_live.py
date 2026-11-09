"""Manual-defined bar diagram from native unconverted Seidel coefficients."""
import asyncio
import math
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.finite_reference import sellmeier,glass_coefficients


@pytest.mark.zemax
def test_seidel_diagram_coefficients_ranges_reference_and_lifecycle():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        before=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces',dict(start=0,count=100))
        merit=await e.call('get_merit_function')
        source=await e.finish(await e.call('run_analysis',dict(request=dict(kind='seidel_coefficients'))))
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='seidel_diagram'))))
        assert result['computation_method']=='native_SeidelCoefficients_bar_chart'
        assert result['native_source']['state']=='succeeded' and result['native_source']['close_attempted']
        total=next(r for r in source['rows'] if r.get('row_label') in {'累计','Sum','Total'} and 'SPHA' in r.get('coefficients',{}))
        for key,value in result['rows'][-1]['coefficients'].items():
            e.check('Cooke unconverted sum '+key,value,total['coefficients'][key],atol=1e-5,rtol=0)
        requests=[dict(first_surface=2,last_surface=5,wavelength=2,ignore_chromatic=True,plot_scale=.5),
            dict(first_surface=4,last_surface=4,ignore_distortion=True),
            dict(ignore_chromatic=True,ignore_distortion=True,suppress_frame=True)]
        for patch in requests:
            q=dict(kind='seidel_diagram',**patch)
            selected=await e.finish(await e.call('run_analysis',dict(request=q)))
            reference=await e.finish(await e.call('run_analysis',dict(request=dict(kind='seidel_coefficients',wavelength=patch.get('wavelength',1)))))
            section=[r for r in reference['rows'] if 'SPHA' in r.get('coefficients',{})]
            for row in selected['rows'][:-1]:
                raw=next(r for r in section if r['row_label']==row['row_label'])
                for key,value in row['coefficients'].items():e.check('native bar '+str(row['surface'])+key,value,raw['coefficients'][key],atol=0,rtol=0)
            assert ('DIST' not in selected['coefficient_order'])==patch.get('ignore_distortion',False)
            assert ('CLA' not in selected['coefficient_order'])==patch.get('ignore_chromatic',False)
            page=await e.call('get_task_result',dict(task_id=selected['task']['task_id'],start=0,count=1))
            assert page['rows']==selected['rows'][:1]
            await e.call('export_analysis_image',dict(request=dict(task_id=selected['task']['task_id'],path=str(e.folder/f"seidel-{len(selected['rows'])}-{patch.get('wavelength',1)}.png"))))
        await e.call('save_lens_as',dict(path=str(e.folder/'seidel-baseline.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'seidel-baseline.zos')))
        again=await e.finish(await e.call('run_analysis',dict(request=dict(kind='seidel_diagram'))))
        assert again['series']==result['series']
        rejected=await e.call('run_analysis',dict(request=dict(kind='seidel_diagram',last_surface=100)),okay=False)
        assert rejected['error']['code']=='INDEX_OUT_OF_RANGE'
        task=await e.call('run_analysis',dict(request=dict(kind='seidel_diagram')))
        state=await e.call('cancel_task',dict(task_id=task['task_id']))
        while state['state'] not in {'cancelled','failed','succeeded'}:
            await asyncio.sleep(.02)
            state=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert state['state']=='cancelled'
        reused=await e.finish(await e.call('run_analysis',dict(request=dict(kind='seidel_diagram'))))
        assert reused['series']==result['series']
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces',dict(start=0,count=100))==surfaces
        assert await e.call('get_merit_function')==merit
        await e.call('new_system')
        await e.call('insert_surfaces',dict(at=1,count=2))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=4,wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,thickness=5,material='N-BK7',replace_solves=True),dict(surface=2,radius=-50,thickness=50,replace_solves=True)]))
        spherical=await e.finish(await e.call('run_analysis',dict(request=dict(kind='seidel_diagram',last_surface=2))))
        n=sellmeier(.55,glass_coefficients('N-BK7'))
        height=2.;slope=0.;index=1.;s1=0.
        for radius,next_index,distance in ((50.,n,5.),(-50.,1.,0.)):
            invariant=index*(slope+height/radius)
            after=(index*slope-height*(next_index-index)/radius)/next_index
            s1-=invariant**2*height*(after/next_index-slope/index)
            height+=distance*after;slope=after;index=next_index
        e.check('independent spherical Seidel S1',spherical['rows'][-1]['coefficients']['SPHA'],s1,atol=1e-6,rtol=0)
    asyncio.run(execute('seidel_diagram_coefficients',work))
