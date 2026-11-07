"""ED-01 controlled physical references over real stdio."""
import asyncio,math,json
from pathlib import Path
import pytest
from support.native import execute

async def direct(e,points,target=2,start=0):
    return (await e.finish(await e.call('run_batch_ray_trace',{'request':{'input_mode':'Direct','start_surface':start,'target_surface':target,'rays':[dict(x=x,y=y,z=0,l=0,m=0,n=1) for x,y in points]}})))['rows']

async def roundtrip(e,label,page,surface=1):
    before=(await e.call('get_surfaces',{'start':surface,'count':1}))['surfaces'][0]
    config=(await e.call('get_system_settings'))['configuration']
    project=await e.call('get_project_settings')
    directory=Path(project['directory']) if project['is_project_directory'] else e.folder
    path=str(directory/(label+'.zos'))
    await e.call('save_lens_as',{'path':path})
    await e.call('open_lens',{'path':path})
    after=(await e.call('get_surfaces',{'start':surface,'count':1}))['surfaces'][0]
    assert before['properties'][page]==after['properties'][page]
    assert {k:v['solve'] for k,v in before['cells'].items()}=={k:v['solve'] for k,v in after['cells'].items()}
    assert (await e.call('get_system_settings'))['configuration']==config

@pytest.mark.zemax
def test_property_apertures_numeric():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',{'changes':[{'surface':0,'thickness':1},{'surface':1,'thickness':1,'semi_diameter':20,'replace_solves':True}]})
        cases=[
          ({'type':'CircularAperture','maximum_radius':2,'x_decenter':.5},[(.5,0),(3,0)], [True,False]),
          ({'type':'CircularObscuration','maximum_radius':2},[(0,0),(3,0)], [False,True]),
          ({'type':'RectangularAperture','x_half_width':2,'y_half_width':1,'y_decenter':.5},[(1,.5),(1,2)], [True,False]),
          ({'type':'RectangularObscuration','x_half_width':2,'y_half_width':1},[(0,0),(3,0)], [False,True]),
          ({'type':'Spider','width_of_arms':.2,'number_of_arms':4},[(0,0),(1,1)], [False,True]),
          ({'type':'UserAperture','aperture_file':'square.uda','uda_scale':.5,'x_decenter':1},[(1,1),(4,0)], [True,False]),
          ({'type':'UserObscuration','aperture_file':'square.uda','uda_scale':.5},[(1,1),(4,0)], [False,True])]
        for patch,points,expected in cases:
            await e.call('update_surfaces',{'changes':[{'surface':1,'aperture':patch}]})
            rows=await direct(e,points)
            for row,want in zip(rows,expected):
                assert row['error_code']==0,row
                e.check('aperture '+patch['type'],int(row['vignette_code']==0),int(want),atol=0,rtol=0)
        await roundtrip(e,'aperture-reload','aperture')
        await e.call('update_surfaces',{'changes':[{'surface':1,'aperture':{'type':'FloatingAperture'}}]})
        result=await e.call('update_surfaces',{'changes':[{'surface':1,'aperture':{'type':'None'}}]},okay=False)
        if 'error' in result:
            assert result['error']['code']=='PARTIAL_UPDATE'
            assert result['error']['details']['cause']['code']=='SETTING_REJECTED'
        else:assert result['surfaces'][0]['properties']['aperture']['type']=='None'
    asyncio.run(execute('property_aperture_numeric',work))

@pytest.mark.zemax
def test_property_composite_numeric():
    async def work(e):
        await e.model()
        await e.call('insert_surfaces',{'at':2})
        await e.call('update_surfaces',{'changes':[{'surface':0,'thickness':1},{'surface':1,'surface_type':'EvenAspheric','radius':'Infinity','thickness':0,'parameters':{1:.001},'replace_solves':True},{'surface':2,'surface_type':'EvenAspheric','radius':'Infinity','thickness':10,'parameters':{1:.002},'material':'MIRROR','replace_solves':True}]})
        pts=[(.3,.4),(1,.5),(2,1)]
        before=await e.call('get_surface_geometry',{'request':{'surface':2,'points':[dict(x=x,y=y)for x,y in pts]}})
        await e.call('update_surfaces',{'changes':[{'surface':1,'composite':{'is_composite_surface':True}}]})
        after=await e.call('get_surface_geometry',{'request':{'surface':2,'points':[dict(x=x,y=y)for x,y in pts]}})
        for (x,y),a,b in zip(pts,before['rows'],after['rows']):
            e.check('base sag',a['sag'],.002*(x*x+y*y),atol=1e-8,rtol=1e-7)
            e.check('composite sag',b['sag'],.003*(x*x+y*y),atol=1e-8,rtol=1e-7)
        rows=await direct(e,pts,target=2)
        for (x,y),row in zip(pts,rows):
            assert row['error_code']==0,row
            # Incident +Z reflected about the analytic graph normal.
            nx,ny,nz=-.006*x,-.006*y,1
            norm=nx*nx+ny*ny+nz*nz
            expect=[-2*nx/norm,-2*ny/norm,1-2/norm]
            # Native sequential reflected cosines use the reversed propagation axis.
            sign=-1
            for got,want in zip(row['direction'],expect):e.check('composite reflected cosine',sign*got,want,atol=1e-7,rtol=0)
        await e.call('save_lens_as',{'path':str(e.folder/'composite.zos')})
        await e.call('open_lens',{'path':str(e.folder/'composite.zos')})
        rows=await e.call('get_surfaces',{'start':1,'count':1})
        assert rows['surfaces'][0]['properties']['composite']['is_composite_surface']
    asyncio.run(execute('property_composite_numeric',work))

@pytest.mark.zemax
def test_property_pop_numeric():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',{'changes':[{'surface':1,'thickness':100}]})
        grid_records=[]
        for auto,sampling,width in [(False,"S256",2),(False,"S512",3),(True,"S1024",2)]:
            patch={'resample_after_refraction':True,'auto_resample':auto}
            if not auto:patch.update(x_sampling=sampling,y_sampling=sampling,x_width=width,y_width=width)
            await e.call('update_surfaces',{'changes':[{'surface':1,'physical_optics':patch}]})
            result=await e.finish(await e.call('run_pop',{'request':{'end_surface':2,'beam_parameters':{0:.1,1:.1},'x_sampling':'S_'+sampling[1:]+'x'+sampling[1:],'y_sampling':'S_'+sampling[1:]+'x'+sampling[1:],'x_width':width,'y_width':width,'save_all_surfaces':True}}))
            g=result['grids'][0];mass=sum(v for row in g['values']for v in row if v is not None)
            mean=sum((g['min_x']+i*g['dx'])*v for row in g['values']for i,v in enumerate(row)if v is not None)/mass
            moment=sum((g['min_x']+i*g['dx']-mean)**2*v for row in g['values']for i,v in enumerate(row)if v is not None)/mass
            expected=.1*math.sqrt(1+(100/(math.pi*.1**2/.00055))**2)
            e.check('POP power auto='+str(auto),result['metrics']['integrated_power'],1,atol=5e-4,rtol=0)
            e.check('POP radius auto='+str(auto),2*math.sqrt(moment),expected,atol=0,rtol=5e-4)
            assert result['intermediate_beam_files']
            assert len(g['values'])==int(sampling[1:])
            assert len(g['values'][0])==int(sampling[1:])
            grid_records.append(dict(auto=auto,sampling=sampling,requested_width=width,rows=len(g['values']),columns=len(g['values'][0]),min_x=g['min_x'],dx=g['dx'],power=result['metrics']['integrated_power'],radius=2*math.sqrt(moment),expected_radius=expected))
        await roundtrip(e,'pop-reload','physical_optics')
        (e.folder/'grid-records.json').write_text(json.dumps(grid_records,indent=2),encoding='utf-8')
    asyncio.run(execute('property_pop_numeric',work))

@pytest.mark.zemax
def test_property_mirror_layout():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',{'changes':[{'surface':0,'thickness':10},{'surface':1,'radius':-10,'conic':-1,'material':'MIRROR','thickness':-5}]})
        before=await direct(e,[(0,1)])
        for substrate in ['Flat','Curved']:
            await e.call('update_surfaces',{'changes':[{'surface':1,'drawing':{'mirror_substrate':substrate,'mirror_thickness':2,'draw_local_axis':True}}]})
            await e.finish(await e.call('run_layout_export',{'request':{'kind':'shaded_model','path':str(e.folder/(substrate+'.png')),'width':640,'height':480}}))
        await e.call('update_surfaces',{'changes':[{'surface':1,'drawing':{'do_not_draw_this_surface':True}}]})
        await e.finish(await e.call('run_layout_export',{'request':{'kind':'shaded_model','path':str(e.folder/'Hidden.png'),'width':640,'height':480}}))
        after=await direct(e,[(0,1)])
        assert before==after
        await roundtrip(e,"mirror-reload","drawing")
    asyncio.run(execute('property_mirror_layout',work))

@pytest.mark.zemax
def test_property_scatter_resources():
    async def work(e):
        import shutil
        await e.model()
        await e.call('update_project_settings',{'request':{'operation':'convert','directory':str(e.folder/'scatter-project')}})
        project=Path((await e.call('get_project_settings'))['directory'])
        for directory in ['ABg_Data','ScatterData']:(project/directory).mkdir(parents=True,exist_ok=True)
        source=Path.home()/'Documents/Zemax'
        shutil.copyfile(source/'ABg_Data/ABG_DATA.DAT',project/'ABg_Data/ABG_DATA.DAT')
        (project/'ABg_Data/ED01.ABGF').write_text('1\nABG-EXAMPLE 1\n',encoding='ascii')
        shutil.copyfile(source/'ScatterData/BrownVinyl.bsdf',project/'ScatterData/BrownVinyl.bsdf')
        observations=[]
        for kind in ['ABgFile','BSDF','ISScatterCatalog','User']:
            result=await e.call('get_system_resources',{'request':{'kind':'scattering_files','scattering_type':kind}},okay=False)
            observations.append(dict(type=kind,result=result))
            if kind=='ABgFile':
                assert 'ED01.ABGF' in result['items']
                await e.call('update_surfaces',{'changes':[{'surface':1,'scattering':{'type':'ABgFile','file_name':'ED01.ABGF'}}]})
                rows=await direct(e,[(0,0)])
                assert rows[0]['error_code']==0
            elif kind=='BSDF':
                # Known local native list points at ABg resources; a genuine BSDF is rejected.
                rejected=await e.call('update_surfaces',{'changes':[{'surface':1,'scattering':{'type':'BSDF','file_name':'BrownVinyl.bsdf','scatter_fraction':1}}]},okay=False)
                assert rejected['error']['code']=='UNSUPPORTED_SETTING'
                assert result['error']['details']['capability']=='sequential_bsdf_resource_selection'
            elif kind=='User':
                assert result['error']['code']=='UNSUPPORTED_SETTING'
                assert 'UILDEScatterData' in result['error']['details']['native_error']
        await roundtrip(e,'scatter-reload','scattering')
        (e.folder/'resource-discovery.json').write_text(json.dumps(observations,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('property_scatter_resources',work))

@pytest.mark.zemax
def test_property_scatter_preflight_state():
    async def work(e):
        await e.model()
        before=await e.call('get_surfaces')
        revision=e.calls[-1]['response']['context']['model_revision']
        r=await e.call('update_surfaces',{'changes':[{'surface':1,'scattering':{'type':'Gaussian','scatter_fraction':.3,'sigma':1}},{'surface':9999,'comment':'invalid preflight'}]},okay=False)
        assert r['error']['code']=='INDEX_OUT_OF_RANGE'
        after=await e.call('get_surfaces')
        assert before==after
        assert e.calls[-1]['response']['context']['model_revision']==revision
    asyncio.run(execute('property_preflight_state',work))
