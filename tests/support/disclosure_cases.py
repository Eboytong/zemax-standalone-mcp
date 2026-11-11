"""Frozen deterministic native cases, shared by both MCP disclosure modes."""
from pathlib import Path


async def sequential(e):
    await e.call('new_system')
    await e.call('insert_surfaces',{'at':1,'count':2})
    await e.call('update_system_settings',{'settings':{'aperture_value':5,'material_catalogs':['SCHOTT'],'wavelengths':[{'wavelength_um':.55}]}})
    await e.call('update_surfaces',{'changes':[
        dict(surface=1,radius=50,thickness=3,material='N-BK7',semi_diameter=5,is_stop=True,replace_solves=True),
        dict(surface=2,radius=-50,thickness=48,semi_diameter=5,replace_solves=True)]})


async def cooke(e):
    await e.call('open_lens',{'path':str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')})


async def nsc(e):
    await e.call('new_system',{'mode':'NonSequential'})
    await e.call('insert_nsc_objects',{'request':{'at':1}})
    await e.call('update_nsc_objects',{'request':{'changes':[
        dict(object=1,object_type='SourceRay',data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1),replace_solves=True),
        dict(object=2,object_type='DetectorRectangle',z=10,data=dict(XHalfWidth=2.5,YHalfWidth=3,NumberXPixels=5,NumberYPixels=3),replace_solves=True)]}})
    await e.finish(await e.call('run_nsc_ray_trace',{'request':{'random_seed':42}}))


async def run_case(e, case):
    if case in {'nsc_trace','nsc_viewer'}:
        await nsc(e)
        data=await e.call('get_detector_data',{'request':{'detector':2,'kind':'flux','width':5,'height':3}})
        e.check('1 W detector',sum(map(sum,data['values'])),1,atol=1e-8,rtol=1e-7)
        if case=='nsc_viewer':
            result=await e.finish(await e.call('run_analysis',{'request':{'kind':'detector_viewer','detector':2}}))
            assert result['grids'][0]['nx']==5 and result['grids'][0]['ny']==3
        return
    if case=='pop_gaussian':
        await e.model()
        result=await e.finish(await e.call('run_pop',{'request':{'end_surface':2,'fiber_type':'GaussianWaist'}}))
        e.check('same field receiver',result['metrics']['receiver_efficiency'],1,atol=1e-8,rtol=1e-7)
        beam=next(a['path'] for a in result['artifacts'] if a['kind']=='beam')
        await e.call('get_beam_file',{'request':{'path':beam,'count':2}})
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,width=4,height=3))
        assert len(page['grid']['values'])==3
        return
    if case in {'sequential_mtf','sequential_wavefront','tolerancing','optimization'}:
        await cooke(e)
    else:
        await sequential(e)
    if case=='sequential_model':
        before=await e.call('get_surfaces')
        path=str(e.folder/'model.zos')
        await e.call('save_lens_as',{'path':path})
        await e.call('open_lens',{'path':path})
        assert await e.call('get_surfaces')==before
    elif case=='sequential_rays':
        result=await e.finish(await e.call('run_batch_ray_trace',{'request':{'rays':[{'px':v} for v in [0,.1,-.1]]}}))
        assert len(result['rows'])==3
        page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],start=1,count=1))
        assert len(page['rows'])==1
    elif case in {'sequential_mtf','sequential_wavefront'}:
        if case=='sequential_mtf':
            result=await e.finish(await e.call('run_fft_mtf',dict(sampling='S_64x64',maximum_frequency=50)))
            assert result['series']
        else:
            result=await e.finish(await e.call('run_analysis',{'request':{'kind':'wavefront','sampling':'S_64x64'}}))
            assert result['grids']
            page=await e.call('get_task_result',dict(task_id=result['task']['task_id'],grid=0,width=4,height=3))
            assert len(page['grid']['values'])==3
        await e.call('export_analysis_image',{'request':{'task_id':result['task']['task_id'],'path':str(e.folder/'analysis.png')}})
        assert (e.folder/'analysis.png').stat().st_size>0
    elif case=='optimization':
        await e.call('update_merit_function',{'mode':'rms_spot_wizard','reference':'Centroid','rings':3})
        await e.call('set_variables',{'variables':[dict(surface=6,cell='thickness',variable=True,replace_solve=True)]})
        before=await e.call('evaluate_merit_function')
        await e.finish(await e.call('run_local_optimization',{'cycles':'Fixed_1_Cycle'}))
        after=await e.call('evaluate_merit_function')
        assert after['merit_function']<=before['merit_function']*1.001+1e-10
    elif case=='tolerancing':
        await e.call('update_tolerances',{'request':dict(mode='replace',operands=[dict(type='TTHI',param1=1,param2=0,minimum=-.01,maximum=.01)])})
        result=await e.finish(await e.call('run_tolerance_analysis',{'request':dict(mode='sensitivity',sampling=1,compensation='None')}),timeout_seconds=240)
        assert result['summary']
    elif case=='energy_loss':
        result=await e.finish(await e.call('run_analysis',{'request':dict(kind='sequential_energy_budget',input_power_w=1,
            rays=[dict(hx=0,hy=0,px=0,py=0)],first_surface=1,last_surface=3)}))
        assert 0<result['summary']['final_throughput']<1
        assert result['resources']['closed_child_tasks']==6
    elif case=='candidate':
        before=await e.call('get_surfaces')
        design=await e.call('manage_candidates',{'request':dict(action='create',label='mode comparison',evaluation=dict(spot=dict(reference='Centroid')))})
        await e.call('update_surfaces',{'changes':[dict(surface=1,radius=55)]})
        await e.call('manage_candidates',{'request':dict(action='restore',design_id=design['design_id'],candidate_id=design['candidate']['candidate_id'])})
        assert await e.call('get_surfaces')==before
    elif case=='glass':
        await e.call('update_surfaces',{'changes':[dict(surface=0,thickness=500,replace_solves=True),dict(surface=1,surface_type='EvenAspheric',replace_solves=True)]})
        before=await e.call('get_surfaces')
        result=await e.finish(await e.call('run_analysis',{'request':dict(kind='glass_trials',include_contributions=False,
            reference_wavelength=1,field=1,groups=[dict(first_surface=1,last_surface=2)],catalogs=['SCHOTT'],
            variables=[dict(surface=2,cell='thickness',minimum=20,maximum=100)],objectives=[dict(metric='rms_spot')],
            max_relative_cost=.000001,cycles='Fixed_1_Cycle')}),timeout_seconds=240)
        assert result['summary']['succeeded']==1 and result['resources']['all_copies_closed']
        assert await e.call('get_surfaces')==before
    else:
        raise AssertionError(case)
