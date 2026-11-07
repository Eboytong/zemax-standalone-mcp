"""NSC component scan selection and independent bare-interface Fresnel values."""
import asyncio,json,math
import pytest
from tests.support.native import execute
from tests.support.finite_reference import glass_coefficients,sellmeier


def fresnel(angle,n1,n2):
    s=math.sin(math.radians(angle));c=math.cos(math.radians(angle));st=n1*s/n2
    if st>=1:return 1,1
    ct=math.sqrt(1-st*st)
    return ((n1*c-n2*ct)/(n1*c+n2*ct))**2,((n2*c-n1*ct)/(n2*c+n1*ct))**2

@pytest.mark.zemax
def test_native_nsc_coating_object_face_scans():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=3))
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],adjust_index_to_environment=False)))
        await e.call('update_surfaces',dict(changes=[dict(surface=2,surface_type='NonSequential',replace_solves=True),dict(surface=4,surface_type='NonSequential',replace_solves=True)]))
        for group in [2,4]:
            await e.call('insert_nsc_objects',dict(request=dict(nsc_surface=group,at=1,count=1)))
            await e.call('update_nsc_objects',dict(request=dict(nsc_surface=group,changes=[dict(object=i,object_type='RectangularVolume',material=m,x=i*10,data=dict(X1HalfWidth=2,Y1HalfWidth=2,X2HalfWidth=2,Y2HalfWidth=2,ZLength=3),replace_solves=True)for i,m in [(1,'N-BK7'if group==2 else'MIRROR'),(2,'N-F2')]])))
        baseline=await e.call('get_system_settings');surfaces=await e.call('get_surfaces');active=(await e.call('get_capabilities'))['active_nsc_surface'];records=[]
        for obj,material in [(1,'N-BK7'),(2,'N-F2')]:
            for face in [0,1,2]:
                for reverse in [False,True]:
                    q=dict(kind='reflection_vs_angle',surface=2,nsc_object=obj,nsc_face=face,minimum_angle=0,maximum_angle=60,wavelength=1,reverse_direction=reverse)
                    result=await e.finish(await e.call('run_analysis',dict(request=q)))
                    records.append(result);(e.folder/'scans.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
                    curve=result['series'][0];n=sellmeier(.55,glass_coefficients(material))
                    for index in [0,len(curve['x'])//2,len(curve['x'])-1]:
                        expected=fresnel(curve['x'][index],n if reverse else 1,1 if reverse else n)
                        for col,value in enumerate([*expected,sum(expected)/2]):e.check('bare NSC reflection',curve['y'][index][col],value,atol=1e-8,rtol=1e-7)
                    assert result['task']['settings']['evaluation_conditions']['material']==material
                    assert (await e.call('get_capabilities'))['active_nsc_surface']==active
        assert await e.call('get_system_settings')==baseline and await e.call('get_surfaces')==surfaces
        await e.call('update_nsc_objects',dict(request=dict(nsc_surface=2,changes=[dict(object=1,faces=[dict(face=1,coating='SPLIT')])])) )
        face_state=await e.call('get_nsc_objects',dict(request=dict(nsc_surface=2)))
        for face in [0,1,2]:
            for metric in ['reflection','transmission','absorption']:
                q=dict(kind=metric+'_vs_angle',surface=2,nsc_object=1,nsc_face=face,minimum_angle=0,maximum_angle=60,wavelength=1)
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                records.append(result);(e.folder/'scans.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
                curve=result['series'][0]
                for index in [0,len(curve['x'])-1]:
                    bare=fresnel(curve['x'][index],1,sellmeier(.55,glass_coefficients('N-BK7')))
                    if face==1:expected=[.5,.5]if metric!='absorption'else[0,0]
                    else:expected=bare if metric=='reflection'else[1-v for v in bare]if metric=='transmission'else[0,0]
                    for col,value in enumerate([*expected,sum(expected)/2]):e.check('NSC selected coating face',curve['y'][index][col],value,atol=1e-8,rtol=1e-7)
                assert (await e.call('get_capabilities'))['active_nsc_surface']==active
        for obj,material in [(1,'N-BK7'),(2,'N-F2')]:
            for reverse in [False,True]:
                q=dict(kind='reflection_vs_wavelength',surface=2,nsc_object=obj,nsc_face=0,minimum_wavelength_um=.45,maximum_wavelength_um=.65,angle=30,reverse_direction=reverse)
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                records.append(result);(e.folder/'scans.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
                curve=result['series'][0]
                for index in [0,len(curve['x'])//2,len(curve['x'])-1]:
                    n=sellmeier(curve['x'][index],glass_coefficients(material));expected=fresnel(30,n if reverse else 1,1 if reverse else n)
                    for col,value in enumerate([*expected,sum(expected)/2]):e.check('NSC wavelength material',curve['y'][index][col],value,atol=1e-8,rtol=1e-7)
        assert await e.call('get_system_settings')==baseline
        assert await e.call('get_nsc_objects',dict(request=dict(nsc_surface=2)))==face_state
    asyncio.run(execute('coating154_nsc_reference',work))


@pytest.mark.zemax
def test_native_pure_nsc_coating_scans():
    from tests.support.nsc import setup,update
    async def work(e):
        await setup(e,2)
        await e.call('update_system_settings',dict(settings=dict(adjust_index_to_environment=False)))
        await update(e,[dict(object=i,object_type='RectangularVolume',x=i*10,material=m,data=dict(X1HalfWidth=2,Y1HalfWidth=2,X2HalfWidth=2,Y2HalfWidth=2,ZLength=3))for i,m in [(1,'N-BK7'),(2,'N-F2')]])
        baseline=await e.call('get_nsc_objects',dict(request={}));settings=await e.call('get_system_settings');records=[]
        for obj,material in [(1,'N-BK7'),(2,'N-F2')]:
            for axis in ['angle','wavelength']:
                for reverse in [False,True]:
                    q=dict(kind='reflection_vs_'+axis,surface=0,nsc_object=obj,nsc_face=0,reverse_direction=reverse)
                    q.update(dict(minimum_angle=0,maximum_angle=60,wavelength=1)if axis=='angle'else dict(angle=30,minimum_wavelength_um=.45,maximum_wavelength_um=.65))
                    result=await e.finish(await e.call('run_analysis',dict(request=q)))
                    records.append(result);(e.folder/'scans.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
                    curve=result['series'][0]
                    for index in [0,len(curve['x'])//2,len(curve['x'])-1]:
                        wavelength=.55 if axis=='angle'else curve['x'][index]
                        angle=curve['x'][index]if axis=='angle'else 30
                        n=sellmeier(wavelength,glass_coefficients(material));expected=fresnel(angle,n if reverse else 1,1 if reverse else n)
                        for col,value in enumerate([*expected,sum(expected)/2]):e.check('pure NSC Fresnel',curve['y'][index][col],value,atol=1e-8,rtol=1e-7)
                    assert result['coating_target']['scope']=='pure_nsc'
        assert await e.call('get_nsc_objects',dict(request={}))==baseline and await e.call('get_system_settings')==settings
    asyncio.run(execute('coating158_pure_reference',work))


@pytest.mark.zemax
def test_native_nsc_film_all_metrics():
    from pathlib import Path
    from tests.support.nsc import setup,update
    from tests.support.thin_film import single_layer,bk7_index
    resource=Path.home()/'Documents/Zemax/Coatings/MCP159_nsc.DAT'
    coating='MATE MCP159_N138\n0.4 1.38 0\n0.8 1.38 0\nCOAT MCP159_FILM\nMCP159_N138 .1 1 0\n'
    resource.write_text(coating,encoding='ascii')
    async def work(e):
        await setup(e,1)
        await e.call('update_system_settings',dict(settings=dict(adjust_index_to_environment=False,files=dict(coating_file=resource.name))))
        await update(e,[dict(object=1,object_type='RectangularVolume',material='N-BK7',data=dict(X1HalfWidth=2,Y1HalfWidth=2,X2HalfWidth=2,Y2HalfWidth=2,ZLength=3),faces=[dict(face=1,coating='MCP159_FILM')])])
        before=await e.call('get_nsc_objects',dict(request={}));settings=await e.call('get_system_settings')
        for invalid in [dict(nsc_object=2,nsc_face=1),dict(nsc_object=1,nsc_face=3)]:
            error=await e.call('run_analysis',dict(request=dict(kind='reflection_vs_angle',surface=0,**invalid)),okay=False)
            assert not error['ok'] and error['error']['code']=='INDEX_OUT_OF_RANGE',error
        path=str(e.folder/'nsc_film.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        before=await e.call('get_nsc_objects',dict(request={}));settings=await e.call('get_system_settings')
        assert before['rows'][0]['faces'][1]['fields']['Coating']=='MCP159_FILM'
        records=[]
        for metric in ['phase','retardance','diattenuation','reflection','transmission','absorption']:
            for axis in ['angle','wavelength']:
                q=dict(kind=metric+'_vs_'+axis,surface=0,nsc_object=1,nsc_face=1)
                q.update(dict(wavelength=1,minimum_angle=5,maximum_angle=60)if axis=='angle'else dict(angle=45,minimum_wavelength_um=.45,maximum_wavelength_um=.7))
                result=await e.finish(await e.call('run_analysis',dict(request=q)))
                records.append(result);(e.folder/'scans.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
                curve=result['series'][0]
                for i in range(0,len(curve['x']),max(1,len(curve['x'])//9)):
                    x=curve['x'][i];angle=x if axis=='angle'else 45;wave=.55 if axis=='angle'else x
                    reference=single_layer(angle,wave,bk7_index(wave))[metric]
                    for channel,(actual,expected) in enumerate(zip(curve['y'][i],reference)):
                        delta=(actual-expected+180)%360-180 if metric in ['phase','retardance']else actual-expected
                        e.check(f'NSC film {metric}/{axis} {x} channel {channel}',delta,0,atol=1e-4 if metric in ['phase','retardance']else 1e-6,rtol=0)
                task=result['task']['task_id'];terminal=await e.call('get_task_status',dict(task_id=task))
                assert terminal['close_attempted'] is True
                await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=3))
                await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/f'{metric}_{axis}.png'))))
        assert await e.call('get_nsc_objects',dict(request={}))==before and await e.call('get_system_settings')==settings
    try:asyncio.run(execute('coating160_nsc_film',work))
    finally:resource.unlink(missing_ok=True)
