"""Prepared native coating scans, Fresnel coefficients and layer persistence."""
import asyncio
import math
from pathlib import Path
import pytest
from support.native import execute
from zemax_mcp.coatings import IDS

@pytest.mark.zemax
@pytest.mark.parametrize('kind',list(IDS))
def test_coating_scan_native(kind):
    async def work(e):
        await e.model()
        q=dict(kind=kind,**({}if kind=='coating_listing'else dict(surface=1)))
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        assert result['artifacts']
        if kind!='coating_listing':
            assert result.get('series')
            await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,count=5))
            await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'coating.png'))))
    asyncio.run(execute('coating024_'+kind,work))

@pytest.mark.zemax
@pytest.mark.parametrize('metric',['reflection','transmission','absorption'])
def test_coating_bare_interface_fresnel(metric):
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.5875618)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,solves=dict(material=dict(mode='material_model',index_nd=1.5,abbe_vd=50)),replace_solves=True)]))
        result=await e.finish(await e.call('run_analysis',dict(request=dict(kind=metric+'_vs_angle',surface=1,minimum_angle=0,maximum_angle=60))))
        points={}
        # Native series 0 is the plotted scan; later series include coefficient tables.
        for x,y in zip(result['series'][0]['x'],result['series'][0]['y']):points[x]=y
        for angle,ys in list(points.items())[::max(1,len(points)//9)]:
            a=math.radians(angle);ca=math.cos(a);cb=math.sqrt(1-(math.sin(a)/1.5)**2)
            rs=((ca-1.5*cb)/(ca+1.5*cb))**2;rp=((1.5*ca-cb)/(1.5*ca+cb))**2
            wanted=[rs,rp,(rs+rp)/2]
            if metric=='transmission':wanted=[1-v for v in wanted]
            if metric=='absorption':wanted=[0,0,0]
            assert len(ys)in(2,3),dict(angle=angle,values=ys)
            expected=sorted(wanted if len(ys)==3 else wanted[:2])
            for i,(actual,reference)in enumerate(zip(sorted(ys),expected)):
                e.check(f'{metric} sorted channel {i} at {angle}',actual,reference,atol=1e-6,rtol=1e-5)
        await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,count=3))
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'fresnel.png'))))
    asyncio.run(execute('coating024_fresnel_'+metric,work))


@pytest.mark.zemax
@pytest.mark.parametrize('metric',['reflection','transmission','absorption'])
def test_coating_wavelength_sellmeier_fresnel(metric):
    # Formula 2 in the installed AGF: interleaved Sellmeier B/C coefficients.
    agf=Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF'
    lines=agf.read_text(encoding='utf-8-sig').splitlines()
    start=next(i for i,line in enumerate(lines) if line.split()[:2]==['NM','N-BK7'])
    assert lines[start].split()[2]=='2'
    coefficients=next([float(v) for v in line.split()[1:7]] for line in lines[start+1:] if line.startswith('CD '))
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(material_catalogs=['SCHOTT'])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,material='N-BK7',replace_solves=True)]))
        q=dict(kind=metric+'_vs_wavelength',surface=1,angle=45,minimum_wavelength_um=.45,maximum_wavelength_um=.7)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        curve=result['series'][0]
        for wavelength,ys in list(zip(curve['x'],curve['y']))[::max(1,len(curve['x'])//9)]:
            squared=wavelength*wavelength
            index=math.sqrt(1+sum(coefficients[i]*squared/(squared-coefficients[i+1]) for i in [0,2,4]))
            ca=math.sqrt(.5);cb=math.sqrt(1-.5/(index*index))
            rs=((ca-index*cb)/(ca+index*cb))**2;rp=((index*ca-cb)/(index*ca+cb))**2
            expected=[rs,rp,(rs+rp)/2]
            if metric=='transmission':expected=[1-v for v in expected]
            if metric=='absorption':expected=[0,0,0]
            assert len(ys)==3
            for actual,want in zip(sorted(ys),sorted(expected)):
                e.check(metric+' Sellmeier Fresnel at '+str(wavelength),actual,want,atol=1e-6,rtol=1e-5)
        await e.call('get_task_result',dict(task_id=result['task']['task_id'],series=0,count=5))
        await e.call('export_analysis_image',dict(request=dict(task_id=result['task']['task_id'],path=str(e.folder/'spectrum.png'))))
    asyncio.run(execute('coating_spectrum053_'+metric,work))

@pytest.mark.zemax
def test_coating_layer_adoption_reload():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        choices=(await e.call('get_system_resources',dict(request=dict(kind='coatings',surface=1))))['items']
        selected=None
        for name in choices:
            await e.call('update_surfaces',dict(changes=[dict(surface=1,coating=name)]))
            revision=e.calls[-1]['response']['context']['model_revision']
            data=await e.call('get_coating_layers',dict(request=dict(surface=1)))
            assert e.calls[-1]['response']['context']['model_revision']==revision
            again=await e.call('get_coating_layers',dict(request=dict(surface=1)))
            assert again==data
            if data['total']>=2:
                selected=data;break
        if selected is None:pytest.skip('available coating list has no editable multilayer fixture; supply native coating file')
        result=await e.call('update_coating_layers',dict(request=dict(surface=1,use_layer_multiplier_and_offsets=True,layers=[dict(layer=1,thickness_multiplier=.9,index_offset=.01,extinction_offset=.001,thickness_status=dict(mode='Variable'),index_status=dict(mode='Variable'),extinction_status=dict(mode='Variable'))])))
        e.check('layer multiplier',result['after'][0]['thickness_multiplier'],.9,atol=1e-12,rtol=1e-12)
        path=str(e.folder/'layers.zos');await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        reloaded=await e.call('get_coating_layers',dict(request=dict(surface=1,count=1)))
        for key in ['thickness_status','index_status','extinction_status']:
            assert reloaded['rows'][0][key]['mode']=='Variable'
        e.check('reloaded index offset',reloaded['rows'][0]['index_offset'],.01,atol=1e-12,rtol=1e-12)
        e.check('reloaded extinction offset',reloaded['rows'][0]['extinction_offset'],.001,atol=1e-12,rtol=1e-12)
        e.check('reloaded multiplier',reloaded['rows'][0]['thickness_multiplier'],.9,atol=1e-12,rtol=1e-12)
        await e.call('update_coating_layers',dict(request=dict(surface=1,layers=[dict(layer=2,thickness_status=dict(mode='Pickup',layer=1),index_status=dict(mode='Pickup',layer=1),extinction_status=dict(mode='Pickup',layer=1))])))
        await e.call('save_lens_as',dict(path=str(e.folder/'pickup.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'pickup.zos')))
        pickup=await e.call('get_coating_layers',dict(request=dict(surface=1,start=2,count=1)))
        for key in ['thickness_status','index_status','extinction_status']:
            assert pickup['rows'][0][key]==dict(mode='Pickup',pickup_from=1)
        await e.call('update_coating_layers',dict(request=dict(surface=1,use_layer_multiplier_and_offsets=False)))
        disabled=await e.call('get_coating_layers',dict(request=dict(surface=1,count=2)))
        assert disabled['use_layer_multiplier_and_offsets'] is False
        assert disabled['rows'][0]['thickness_multiplier']==.9
        assert disabled['rows'][1]['thickness_status']['mode']=='Pickup'
        fixed=dict(layer=2,thickness_multiplier=.8,index_offset=.02,extinction_offset=.002,
            thickness_status=dict(mode='Fixed'),index_status=dict(mode='Fixed'),extinction_status=dict(mode='Fixed'))
        await e.call('update_coating_layers',dict(request=dict(surface=1,use_layer_multiplier_and_offsets=True,layers=[fixed])))
        await e.call('save_lens_as',dict(path=str(e.folder/'fixed.zos')))
        await e.call('open_lens',dict(path=str(e.folder/'fixed.zos')))
        final=await e.call('get_coating_layers',dict(request=dict(surface=1,start=2,count=1)))
        for key in ['thickness_status','index_status','extinction_status']:
            assert final['rows'][0][key]['mode']=='Fixed'
        for key in ['thickness_multiplier','index_offset','extinction_offset']:
            e.check('fixed '+key,final['rows'][0][key],fixed[key],atol=1e-12,rtol=1e-12)
    asyncio.run(execute('coating024_layers',work))
