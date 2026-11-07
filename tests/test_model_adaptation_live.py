from zemax_mcp.models import COMMAND_MODELS
"""Native acceptance for the approved installed model adaptation stages."""
import asyncio
import json
import math
import pytest
from support.native import execute
from support.nsc import setup,update,detector


@pytest.mark.zemax
def test_model_capabilities_native():
    async def work(e):
        caps=await e.call('get_capabilities')
        assert caps['connected'] and len(caps['implemented_tools'])==len(COMMAND_MODELS)
        assert caps['parameter_ranges']['LDE']['last']==254 and caps['parameter_ranges']['NCE']['last']==250
        assert 'ExtendedPolynomial'in caps['validated_surface_model_scope']
        assert caps['detector_adapters']['DetectorSurface']['geometry']['option']=='include_geometry'
        (e.folder/'capabilities.json').write_text(json.dumps(caps,indent=2),encoding='utf-8')
    asyncio.run(execute('adaptation_capabilities',work))


@pytest.mark.zemax
def test_regular_pupil_primary_native():
    from pathlib import Path
    async def work(e):
        lens=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
        await e.call('open_lens',dict(path=str(lens)))
        await e.call('get_surfaces',dict(start=0,count=20))
        results=[]
        for field in (1,2,3):
            result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='wavefront',field=field,wavelength=2,
                sampling='S_32x32',remove_tilt=True,use_exit_pupil=True,include_pupil_mapping=True))),timeout_seconds=600)
            mapping=result['grids'][0]['pupil_mapping'];results.append(dict(field=field,mapping=mapping))
            assert mapping['status']=='verified_regular_display_mapping',mapping.get('error_status')
            assert sum(p['valid']for r in mapping['points']for p in r)>500
        (e.folder/'pupil-reference.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    asyncio.run(execute('adaptation_regular_pupil',work))


@pytest.mark.zemax
@pytest.mark.parametrize('model',['cooke','singlet'])
@pytest.mark.parametrize('wave',[.486,.55,.644])
@pytest.mark.parametrize('sampling',[32,64,128])
def test_regular_pupil_single_wavelength_matrix_native(model,wave,sampling):
    from pathlib import Path
    async def work(e):
        if model=='cooke':
            await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
            fields=[0,14,20]
        else:
            await e.model();await e.call('insert_surfaces',dict(at=2))
            await e.call('update_surfaces',dict(changes=[dict(surface=1,is_stop=True,radius=50,material='N-BK7',thickness=5,semi_diameter=10,replace_solves=True),
                dict(surface=2,radius=0,thickness=95,semi_diameter=10,replace_solves=True)]))
            fields=[0,5]
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'],fields=[dict(x=0,y=y)for y in fields],
            wavelengths=[dict(wavelength_um=wave)],primary_wavelength=1)))
        baseline=e.folder/'baseline.zos';await e.call('save_lens_as',dict(path=str(baseline)))
        await e.call('get_surfaces',dict(start=0,count=10))
        records=[]
        for field in range(1,len(fields)+1):
            for exit_shape in (False,True):
                for remove_tilt in (False,True):
                    q=dict(kind='wavefront',field=field,wavelength=1,sampling=f'S_{sampling}x{sampling}',
                        remove_tilt=remove_tilt,use_exit_pupil=exit_shape,include_pupil_mapping=True)
                    r=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=600)
                    m=r['grids'][0]['pupil_mapping'];expected='verified_regular_display_mapping'if exit_shape else'verified_entrance_guard_sample_formula'
                    if not exit_shape:assert 'coordinate-domain validity only'in m['validity_scope']
                    record=dict(request=q,status=m['status'],reason=m.get('error_status'),valid=sum(p['valid']for row in m['points']for p in row),
                        errors=[p.get('opd_error_waves',0)for row in m['points']for p in row if p['valid']],invalid_reference_points=m.get('invalid_reference_points',0))
                    records.append(record)
        (e.folder/'pupil-matrix-reference.json').write_text(json.dumps(dict(model=model,wavelength_um=wave,
            selected_is_primary=True,baseline=str(baseline),records=records),indent=2),encoding='utf-8')
        assert all(r['status']in('verified_regular_display_mapping','verified_entrance_guard_sample_formula')for r in records),[(r['request'],r['status'],r['reason'],r['invalid_reference_points'])for r in records if r['status']not in('verified_regular_display_mapping','verified_entrance_guard_sample_formula')]
    asyncio.run(execute(f'adaptation_pupil_{model}_{wave}_{sampling}',work))


@pytest.mark.zemax
def test_surface_facet_geometry_native():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type='SourceRay',x=.2,y=.3,data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type='DetectorSurface',z=5,material='ABSORB',data=dict(Radius=0,MaxAperture=2,MinAperture=0,NumberAZones=8,NumberRZones=4))])
        await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(random_seed=42))))
        result=await detector(e,2,include_geometry=True,count=1000)
        assert len(result['rows'])==56
        assert sum(r['geometry']['facet_flux']for r in result['rows'])==pytest.approx(1)
        (e.folder/'facet-reference.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    asyncio.run(execute('adaptation_facets',work))


@pytest.mark.zemax
@pytest.mark.parametrize('shape',['plane','curved','annular'])
@pytest.mark.parametrize('fast',[False,True])
def test_surface_facet_controlled_hits_native(shape,fast):
    async def work(e):
        await setup(e,2)
        await e.call('update_system_settings',dict(settings=dict(analysis_units='WattsPerMMSq')))
        radius=10 if shape=='curved'else 0
        await update(e,[dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type='DetectorSurface',x=1,y=-2,z=5,tilt_x=7,tilt_y=-11,material='ABSORB',
                data=dict(Radius=radius,MaxAperture=2,MinAperture=.5 if shape=='annular'else 0,NumberAZones=8,NumberRZones=4),
                type_settings=dict(FastRayTrace=fast))])
        objects=await e.call('get_nsc_objects',dict(request=dict(start=2,count=1)))
        transform=objects['rows'][0]['global_transform'];rot=transform['rotation'];translation=transform['translation']
        def global_point(p):return [sum(rot[i][j]*p[j]for j in range(3))+translation[i]for i in range(3)]
        direction=[rot[i][2]for i in range(3)]
        local=await detector(e,2,include_geometry=True,count=1000)
        glob=await detector(e,2,include_geometry=True,geometry_frame='global',count=1000)
        for a,b in zip(local['rows'],glob['rows'],strict=True):
            e.check('transformed facet area mm2',b['geometry']['area'],a['geometry']['area'])
            for va,vb in zip(a['geometry']['vertices'],b['geometry']['vertices'],strict=True):
                for actual,expected in zip(vb,global_point(va)):e.check('facet global vertex mm',actual,expected)
                expected=0 if not radius else radius-math.sqrt(radius*radius-va[0]**2-va[1]**2)
                e.check('spherical facet vertex sag mm',va[2],expected)
        records=[]
        for index in (0,len(local['rows'])//2,len(local['rows'])-1):
            centroid=local['rows'][index]['geometry']['centroid'];origin=global_point([centroid[0],centroid[1],centroid[2]-3])
            await update(e,[dict(object=1,x=origin[0],y=origin[1],z=origin[2],
                data=dict(XCosine=direction[0],YCosine=direction[1],ZCosine=direction[2]))])
            await e.finish(await e.call('run_nsc_ray_trace',dict(request=dict(random_seed=42))))
            flux=await detector(e,2,include_geometry=True,count=1000)
            e.check('centroid-directed ray facet W',flux['rows'][index]['value'],1)
            e.check('centroid-directed ray total W',flux['total_flux'],1)
            density=await detector(e,2,kind='irradiance',include_geometry=True,start=index,count=1)
            e.check('facet irradiance W/mm2',density['rows'][0]['value'],1/local['rows'][index]['geometry']['area'])
            records.append(dict(face=index,pixel=flux['rows'][index]['pixel'],flux=flux['rows'][index]['value']))
        page=await detector(e,2,include_geometry=True,start=1,count=2)
        assert len(page['rows'])==2 and page['next_start']==3
        path=e.folder/'faceted.zos';await e.call('save_lens_as',dict(path=str(path)));await e.call('open_lens',dict(path=str(path)))
        reloaded=await detector(e,2,include_geometry=True,count=1000)
        assert len(reloaded['rows'])==len(local['rows'])
        (e.folder/'facet-controlled-reference.json').write_text(json.dumps(dict(shape=shape,fast=fast,hits=records,transform=transform),indent=2),encoding='utf-8')
    asyncio.run(execute(f'adaptation_facets_{shape}_{fast}',work))


@pytest.mark.zemax
@pytest.mark.parametrize('kind',['ExtendedAsphere','ExtendedOddAsphere'])
def test_extended_surface_high_parameters_native(kind):
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type=kind,radius=50,
            parameters={13:240,14:1,21:.02,254:.1},replace_solves=True)]))
        rows=(await e.call('get_surfaces',dict(start=1,count=1,parameter_start=21,parameter_count=234)))['surfaces']
        assert rows[0]['cells']['parameter_254']['value']==.1
        for x in (.3,1.):
            geometry=await e.call('get_surface_geometry',dict(request=dict(surface=1,points=[dict(x=x,y=0)])))
            exponent=14 if kind=='ExtendedAsphere'else 7
            last=480 if kind=='ExtendedAsphere'else 240
            expected=50-math.sqrt(2500-x*x)+.02*x**exponent+.1*x**last
            e.check(kind+' high coefficient sag mm',geometry['rows'][0]['sag'],expected)
        await e.call('set_variables',dict(variables=[dict(surface=1,cell='parameter_254',variable=True)]))
        await e.call('save_lens_as',dict(path=str(e.folder/'extended.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'extended.zos')))
        variables=await e.call('get_variables')
        assert any(v['cell']=='parameter_254'for v in variables['variables'])
    asyncio.run(execute('adaptation_'+kind,work))


@pytest.mark.zemax
def test_nce_extended_parameter_native():
    async def work(e):
        await setup(e,1)
        await update(e,[dict(object=1,object_type='ExtendedPolynomialSurface',parameters={1:2,2:50,6:2,7:242,21:.002,249:.001})])
        row=(await e.call('get_nsc_objects',dict(request=dict(start=1,count=1,parameter_start=21,parameter_count=230))))['rows'][0]
        e.check('NCE high coefficient readback',row['parameter_cells']['249']['value'],.001)
        before=(await e.call('get_system_summary'))
        bad=await e.call('update_nsc_objects',dict(request=dict(changes=[dict(object=1,parameters={250:.1})])),okay=False)
        assert not bad['ok'] and bad['error']['code']=='CELL_NOT_WRITABLE'
        await e.call('set_variables',dict(variables=[dict(object=1,cell='Par249')]))
        saved=e.folder/'nce-high.zos';await e.call('save_lens_as',dict(path=str(saved)));await e.call('open_lens',dict(path=str(saved)))
        rows=(await e.call('get_nsc_objects',dict(request=dict(start=1,count=1,parameter_start=249,parameter_count=2))))['rows']
        assert rows[0]['parameter_cells']['249']['solve']=='Variable'
        e.check('NCE reloaded high coefficient',rows[0]['parameter_cells']['249']['value'],.001)
    asyncio.run(execute('adaptation_nce_parameters',work))
