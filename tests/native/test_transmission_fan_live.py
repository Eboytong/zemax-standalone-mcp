import asyncio
import json
import math
from pathlib import Path

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_polarization_transmission_fan_native_report():
    async def work(e):
        await e.call("open_lens", dict(path=str(Path.home() / "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
        result = await e.finish(await e.call("run_analysis", dict(request=dict(kind="polarization_transmission_fan"))))
        assert result["computation_method"] == "native_TransmissionFan_text"
        assert result["polarization"] == "unpolarized"
        assert result["wavelengths_um"] == pytest.approx([.48, .55, .65])
        assert len(result["series"]) == 18
        assert {s["fan"] for s in result["series"]} == {"sagittal", "tangential"}
        center = next(s for s in result["series"] if s["field_number"] == 1 and s["fan"] == "tangential" and s["wavelength_um"] == pytest.approx(.55))
        assert center["y"][0][0] == pytest.approx(.9606, abs=1e-4)
        assert center["x"][0] == pytest.approx(-1)
        assert center["x"][-1] == pytest.approx(1)
        assert any(a["kind"] == "native_text" for a in result["artifacts"])
    asyncio.run(execute("polarization_transmission_fan", work))


@pytest.mark.zemax
def test_transmission_fan_single_and_two_wavelength_fresnel_reference():
    async def work(e):
        await e.model()
        await e.call('insert_surfaces',dict(at=2))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,radius='Infinity',thickness=0,material='N-BK7',semi_diameter=10,replace_solves=True),
            dict(surface=2,radius='Infinity',thickness=1,material='',semi_diameter=10,replace_solves=True),
            dict(surface=3,semi_diameter=10,replace_solves=True)]))
        agf=(Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF').read_text(encoding='utf-8-sig').splitlines()
        start=next(i for i,line in enumerate(agf) if line.split()[:2]==['NM','N-BK7'])
        coefficients=next([float(x) for x in line.split()[1:7]] for line in agf[start+1:] if line.startswith('CD '))
        observations=[]
        for waves in [[.55],[.55,.65]]:
            await e.call('update_system_settings',dict(settings=dict(
                fields=[dict(x=0,y=0),dict(x=0,y=5)],
                wavelengths=[dict(wavelength_um=w) for w in waves])))
            baseline=await e.call('get_system_settings')
            surfaces=await e.call('get_surfaces')
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission_fan'))))
            assert result['wavelengths_um']==waves
            assert len(result['series'])==4*len(waves)
            assert result['polarization']=='unpolarized'
            for series in result['series']:
                wave=series['wavelength_um']
                n=math.sqrt(1+sum(coefficients[i]*wave**2/(wave**2-coefficients[i+1]) for i in (0,2,4)))
                theta=math.radians(series['field_deg'])
                cosine=math.cos(theta)
                transmitted_cosine=math.sqrt(1-(math.sin(theta)/n)**2)
                rs=((cosine-n*transmitted_cosine)/(cosine+n*transmitted_cosine))**2
                rp=((n*cosine-transmitted_cosine)/(n*cosine+transmitted_cosine))**2
                expected=((1-rs)**2+(1-rp)**2)/2
                assert len(series['x'])==201
                for pupil,y in zip(series['x'],series['y']):
                    e.check(f'Fresnel plate {wave}um field{series["field_deg"]} {series["fan"]} pupil{pupil}',
                            y[0],expected,atol=5.1e-5,rtol=0)
                observations.append(dict(wavelength_um=wave,field_deg=series['field_deg'],fan=series['fan'],
                    expected=expected,maximum_error=max(abs(y[0]-expected) for y in series['y'])))
            task_id=result['task']['task_id']
            page=await e.call('get_task_result',dict(task_id=task_id,start=3,count=2))
            assert page['rows']==result['rows'][3:5]
            status=await e.call('get_task_status',dict(task_id=task_id))
            assert status['state']=='succeeded' and status['close_attempted']
            await e.call('export_analysis_image',dict(request=dict(task_id=task_id,path=str(e.folder/f'fan-{len(waves)}.png'))))
            assert await e.call('get_system_settings')==baseline
            assert await e.call('get_surfaces')==surfaces
        (e.folder/'fresnel-reference.json').write_text(json.dumps(dict(catalog='SCHOTT.AGF',material='N-BK7',
            thickness=0,reference='Unpolarized product of two lossless Fresnel interface power transmissions',
            coefficients=coefficients,tolerance=5.1e-5,observations=observations),indent=2),encoding='utf-8')
        saved=e.folder/'plate.zos'
        await e.call('save_lens_as',dict(path=str(saved)))
        await e.call('open_lens',dict(path=str(saved)))
        repeated=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission_fan'))))
        assert repeated['series']==result['series']
    asyncio.run(execute('transmission_fan_fresnel',work))


@pytest.mark.zemax
def test_transmission_fan_formal_batch_equivalence_probe():
    from zemax_mcp.field_analyses import normalized_field
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        settings=await e.call('get_system_settings')
        native=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission_fan'))))
        assert native['computation_method']=='native_TransmissionFan_text'
        rays=[];expected=[]
        for series in native['series']:
            field=settings['fields'][series['field_number']-1]
            hx,hy=normalized_field(settings['fields'],field,settings['field_normalization'])
            wave=next(w['number'] for w in settings['wavelengths'] if abs(w['wavelength_um']-series['wavelength_um'])<1e-8)
            for i in [0,50,100,150,200]:
                pupil=series['x'][i]
                rays.append(dict(hx=hx,hy=hy,px=pupil if series['fan']=='sagittal' else 0,
                    py=pupil if series['fan']=='tangential' else 0,wavelength=wave))
                expected.append(series['y'][i][0])
        traces=[]
        for polarization in [dict(jx=1,jy=0),dict(jx=0,jy=1)]:
            result=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(rays=rays,polarization=polarization))))
            traces.append(result['rows'])
        for i,reference in enumerate(expected):
            assert traces[0][i]['error_code']==traces[1][i]['error_code']==0
            intensity=(traces[0][i]['intensity']+traces[1][i]['intensity'])/2
            e.check('native fan vs orthogonal batch average '+str(i),intensity,reference,atol=5.1e-5,rtol=0)
        adapted=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission_fan',method='ray_trace'))),timeout_seconds=180)
        assert adapted['computation_method']=='native_batch_polarized_ray_trace'
        for reference in native['series']:
            actual=next(s for s in adapted['series'] if (s['field_number'],s['fan'],s['wavelength_um'])==
                (reference['field_number'],reference['fan'],reference['wavelength_um']))
            assert actual['x']==pytest.approx(reference['x'],abs=1e-12)
            for i,(value,expected_value) in enumerate(zip(actual['y'],reference['y'])):
                if expected_value[0] is None:assert value[0] is None
                else:e.check('selectable/native full pupil '+str((reference['series'],i)),value[0],expected_value[0],atol=5.1e-5,rtol=0)
        selected=await e.finish(await e.call('run_analysis',dict(request=dict(kind='polarization_transmission_fan',field=2,wavelength=2,sampling=5))))
        assert selected['actual_settings']['field_numbers']==[2]
        assert selected['actual_settings']['wavelength_numbers']==[2]
        assert len(selected['series'])==2 and all(len(s['x'])==5 for s in selected['series'])
        task_id=selected['task']['task_id']
        page=await e.call('get_task_result',dict(task_id=task_id,start=3,count=2))
        assert page['rows']==selected['rows'][3:5]
        status=await e.call('get_task_status',dict(task_id=task_id))
        assert status['state']=='succeeded' and not status['context']['requires_reconnect']
        for child_id in selected['ray_trace_tasks']:
            child=await e.call('get_task_status',dict(task_id=child_id))
            assert child['state']=='succeeded' and not child.get('cleanup_warnings')
        await e.call('export_analysis_image',dict(request=dict(task_id=task_id,path=str(e.folder/'selected.png'))))
        assert await e.call('get_system_settings')==settings
    asyncio.run(execute('transmission_fan_batch_equivalence',work))


@pytest.mark.zemax
def test_transmission_fan_jones_reference_invalid_rays_cancel_and_reload():
    import time
    async def work(e):
        await e.model()
        await e.call('insert_surfaces',dict(at=2))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=1,radius='Infinity',thickness=0,material='N-BK7',semi_diameter=20,replace_solves=True),
            dict(surface=2,radius='Infinity',thickness=1,material='',semi_diameter=20,replace_solves=True),
            dict(surface=3,semi_diameter=20,replace_solves=True)]))
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=0,y=30)],
            wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.65)])))
        baseline=await e.call('get_system_settings')
        surfaces=await e.call('get_surfaces')
        agf=(Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF').read_text(encoding='utf-8-sig').splitlines()
        start=next(i for i,line in enumerate(agf) if line.split()[:2]==['NM','N-BK7'])
        coefficients=next([float(x) for x in line.split()[1:7]] for line in agf[start+1:] if line.startswith('CD '))
        wave=.65
        n=math.sqrt(1+sum(coefficients[i]*wave**2/(wave**2-coefficients[i+1]) for i in (0,2,4)))
        c=math.cos(math.radians(30));ct=math.sqrt(1-(.5/n)**2)
        ts=1-((c-n*ct)/(c+n*ct))**2
        tp=1-((n*c-ct)/(n*c+ct))**2
        for polarization in [dict(jx=1,jy=0),dict(jx=0,jy=1),dict(jx=1,jy=1,x_phase=30,y_phase=120),dict(jx=2,jy=0)]:
            q=dict(kind='polarization_transmission_fan',field=2,wavelength=2,sampling=5,polarization=polarization)
            result=await e.finish(await e.call('run_analysis',dict(request=q)))
            expected=(polarization['jx']**2*ts**2+polarization['jy']**2*tp**2)/(polarization['jx']**2+polarization['jy']**2)
            for series in result['series']:
                assert series['invalid_count']==0
                for value in series['y']:e.check('Jones Fresnel '+str(polarization),value[0],expected,atol=1e-8,rtol=1e-7)
            actual=result['actual_settings']
            assert actual['field_numbers']==[2] and actual['wavelength_numbers']==[2]
            assert actual['polarization_inputs'][0]['y_phase']==polarization.get('y_phase',0)
        saved=e.folder/'plate.zos'
        await e.call('save_lens_as',dict(path=str(saved)))
        await e.call('open_lens',dict(path=str(saved)))
        repeat=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert repeat['series']==result['series']
        task=await e.call('run_analysis',dict(request=dict(kind='polarization_transmission_fan',method='ray_trace',sampling=1001)))
        task=await e.call('cancel_task',dict(task_id=task['task_id']))
        deadline=time.monotonic()+30
        while task['state'] not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            task=await e.call('get_task_status',dict(task_id=task['task_id']))
        assert task['state']=='cancelled'
        await e.finish(await e.call('run_analysis',dict(request=q)))
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_surfaces')==surfaces
        await e.call('update_surfaces',dict(changes=[dict(surface=2,semi_diameter=1,replace_solves=True)]))
        clipped=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert sum(s['invalid_count'] for s in clipped['series'])>0
        assert any(r['invalid_count'] for r in clipped['rows'])
    asyncio.run(execute('transmission_fan_jones',work))
