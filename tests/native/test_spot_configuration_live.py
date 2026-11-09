"""Current-configuration spot selection, stdio, reload and five-plane regression."""
import asyncio
import json
from pathlib import Path

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_spot_current_configuration_and_through_focus_over_stdio():
    async def work(e):
        sample=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens',dict(path=str(sample)))
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.48,weight=1),dict(wavelength_um=.65,weight=3)],primary_wavelength=1)))
        surfaces=await e.call('get_surfaces')
        thickness=next(s for s in surfaces['surfaces'] if s['surface']==6)['cells']['thickness']['value']
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],
            operands=[dict(type='THIC',parameters={1:6},cells=[dict(configuration=1,value=thickness),dict(configuration=2,value=thickness+.2)])])))
        records=[]
        for configuration,reference in ((1,13.593903200295003),(2,19.57687223704524)):
            await e.call('set_configuration',dict(configuration=configuration))
            spot=await e.finish(await e.call('run_spot_analysis',dict(reference='Centroid',field=3,wavelength=0)))
            assert spot['context']['configuration']==configuration
            assert spot['task']['settings']['configuration']==configuration
            assert spot['task']['settings']['native_configuration_selector']==1
            e.check('current configuration '+str(configuration),spot['metrics'][0]['rms_radius'],reference,atol=1e-6,rtol=1e-6)
            status=await e.call('get_task_status',dict(task_id=spot['task']['task_id']))
            assert status['close_attempted'] and not status.get('cleanup_warnings')
            records.append(spot)
        saved=e.folder/'configuration2.zos'
        await e.call('save_lens_as',dict(path=str(saved)))
        await e.call('open_lens',dict(path=str(saved)))
        reloaded=await e.finish(await e.call('run_spot_analysis',dict(reference='Centroid',field=3,wavelength=0)))
        assert reloaded['context']['configuration']==2
        e.check('reloaded configuration2',reloaded['metrics'][0]['rms_radius'],records[-1]['metrics'][0]['rms_radius'],atol=1e-6,rtol=1e-6)
        before=dict(settings=await e.call('get_system_settings'),surfaces=await e.call('get_surfaces'),
            merit=await e.call('get_merit_function'),configurations=await e.call('get_configurations',dict(request={})))
        through=await e.finish(await e.call('run_analysis',dict(request=dict(kind='through_focus_spot',field=3,wavelength=0))))
        center=next(row for row in through['rows'] if row['delta_focus_um']==0)
        e.check('configuration2 zero-focus RMS',center['rms_radius'],reloaded['metrics'][0]['rms_radius'],atol=1e-6,rtol=1e-6)
        assert through['restoration']['restored']
        original=await e.call('get_task_status',dict(task_id=through['native_analysis_task']))
        assert original['settings']['native']['Configuration']==1
        assert original['settings']['resolved_configuration']==2
        assert original['close_attempted'] and not original.get('cleanup_warnings')
        page=await e.call('get_task_result',dict(task_id=through['task']['task_id'],start=1,count=2))
        assert page['rows']==through['rows'][1:3]
        await e.call('export_analysis_image',dict(request=dict(task_id=through['task']['task_id'],path=str(e.folder/'configuration2-focus.png'))))
        actual=dict(settings=await e.call('get_system_settings'),surfaces=await e.call('get_surfaces'),
            merit=await e.call('get_merit_function'),configurations=await e.call('get_configurations',dict(request={})))
        assert actual==before
        (e.folder/'configuration-reference.json').write_text(json.dumps(dict(standard=records,reloaded=reloaded,through=through,model_restored=True),ensure_ascii=False,indent=2),encoding='utf-8')
    async def guarded(e):
        try:await work(e)
        except BaseException:
            await e.call('disconnect',okay=False)
            raise
    asyncio.run(execute('spot-current-configuration',guarded))
