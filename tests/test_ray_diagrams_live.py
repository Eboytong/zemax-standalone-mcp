"""Native worksheet cross-checks and independently specified elementary optics."""
import asyncio,json,math,re
from pathlib import Path
import pytest
from support.native import execute

@pytest.mark.zemax
def test_ray_diagrams_cooke_native_text_reference():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(yybar_atol=5e-9,angle_atol=1e-6,
            image_height_atol=1e-5,reference='Same-wave Cooke native YYbarDiagram/IncidentAnglevsImageHeight text captured by probe379; decimal precision preserved.'),indent=2),encoding='utf-8')
        baseline=json.loads((Path(__file__).resolve().parents[1]/'verification/development/CV-02/probe379-primary-ray-operands/probe.json').read_text(encoding='utf-8'))
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        yy=await e.finish(await e.call('run_analysis',dict(request=dict(kind='yybar_diagram',wavelength=2))))
        raw=[]
        for line in baseline['analyses'][0]['text'].splitlines():
            m=re.fullmatch(r'\s*(\d+)\s+([-+\d.Ee]+)\s+([-+\d.Ee]+)\s*',line)
            if m:raw.append((int(m[1]),float(m[2]),float(m[3])))
        assert len(yy['rows'])==len(raw)==7
        for row,(surface,chief,marginal)in zip(yy['rows'],raw):
            assert row['surface']==surface
            e.check('native text Y-bar',row['chief_y'],chief,atol=5e-9,rtol=0)
            e.check('native text Y',row['marginal_y'],marginal,atol=5e-9,rtol=0)
        incident=await e.finish(await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height',wavelength=2))))
        text=[]
        for line in baseline['analyses'][1]['text'].splitlines():
            parts=line.split()
            if len(parts)!=4:continue
            try:text.append(list(map(float,parts)))
            except ValueError:pass
        assert len(incident['rows'])==len(text)==21
        for row,reference in zip(incident['rows'],text):
            e.check('native image height',row['image_height'],reference[0],atol=1e-5,rtol=0)
            for key,value in zip(['lower_angle_deg','chief_angle_deg','upper_angle_deg'],reference[1:]):
                e.check('native '+key,row[key],value,atol=1e-6,rtol=0)
        (e.folder/'outlets.json').write_text(json.dumps(dict(yybar=yy,incident=incident),ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('ray380_cooke',work))

@pytest.mark.zemax
def test_yybar_thin_lens_and_plane_incidence():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(atol=1e-8,rtol=1e-7,
            reference='Paraxial thin lens y_out=y_in+100*(u_in-y_in/100), u_in=tan(field); free planar incidence equals field angle for all pupil rays.'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0),dict(x=0,y=20)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',parameters={'1':100},
            thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=100,replace_solves=True)]))
        yy=await e.finish(await e.call('run_analysis',dict(request=dict(kind='yybar_diagram'))))
        for row in yy['rows']:
            e.check('thin lens chief',row['chief_y'],0 if row['surface']==1 else 100*math.tan(math.radians(20)),atol=1e-8,rtol=1e-7)
            e.check('thin lens marginal',row['marginal_y'],5 if row['surface']==1 else 0,atol=1e-8,rtol=1e-7)
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Standard',thickness=100,semi_diameter=100,replace_solves=True)]))
        inc=await e.finish(await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height',field_density=11))))
        assert inc['trace_conditions_met']
        for row in inc['rows']:
            angle=row['field_y']
            e.check('free image height',row['image_height'],100*math.tan(math.radians(angle)),atol=1e-8,rtol=1e-7)
            for key in ['lower_angle_deg','chief_angle_deg','upper_angle_deg']:e.check('free '+key,row[key],angle,atol=1e-8,rtol=1e-7)
    asyncio.run(execute('ray381_controlled',work))


@pytest.mark.zemax
def test_ray_diagrams_selection_lifecycle_and_square_export():
    import time
    from PIL import Image
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        caps=await e.call('get_capabilities')
        for name in ('yybar_diagram','incident_angle_vs_image_height'):
            assert caps['analyses'][name]['verification'].startswith('accepted;')
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        configs=await e.call('get_configurations',dict(request={}))
        for q in [dict(kind='yybar_diagram',first_surface=2,last_surface=6,wavelength=3,plot_scale=25),
                  dict(kind='incident_angle_vs_image_height',wavelength=3,field_density=11)]:
            r=await e.finish(await e.call('run_analysis',dict(request=q)));tid=r['task']['task_id']
            assert r['actual_settings']['wavelength_um']==.65
            page=await e.call('get_task_result',dict(task_id=tid,start=1,count=2))
            assert page['rows']==r['rows'][1:3]
            page=await e.call('get_task_result',dict(task_id=tid,series=0,start=1,count=2))
            assert page['series'][0]['x']==r['series'][0]['x'][1:3]
            if q['kind']=='yybar_diagram':
                assert page['series'][0]['point_labels']==['3','4']
                assert r['series'][0]['axis_limits']==[-25,25]
                assert {row['surface']for row in r['rows']}==set(range(2,7))
            png=e.folder/(q['kind']+'.png')
            exported=await e.call('export_analysis_image',dict(request=dict(task_id=tid,path=str(png),item=0,width=800,height=800)))
            with Image.open(png)as image:assert image.size==(800,800)
            if q['kind']=='yybar_diagram':assert exported['plotting_settings']['aspect']=='equal'
            bad=await e.call('run_analysis',dict(request=q|dict(wavelength=999)),okay=False)
            assert bad['error']['code']=='INDEX_OUT_OF_RANGE'
            cancel=q|dict(first_surface=1,last_surface=7)if q['kind']=='yybar_diagram'else q|dict(field_density=1001)
            task=await e.call('run_analysis',dict(request=cancel))
            status=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert status['state']=='running',status
            task=await e.call('cancel_task',dict(task_id=task['task_id']))
            deadline=time.monotonic()+30
            while task['state']not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);task=await e.call('get_task_status',dict(task_id=task['task_id']))
            assert task['state']=='cancelled',task
            await e.call('get_task_result',dict(task_id=task['task_id']))
            again=await e.finish(await e.call('run_analysis',dict(request=q)))
            assert again['rows']==r['rows']
        async def unchanged():
            assert await e.call('get_surfaces')==baseline
            assert await e.call('get_system_settings')==settings
            assert await e.call('get_merit_function')==merit
            assert await e.call('get_configurations',dict(request={}))==configs
        await unchanged()
        path=str(e.folder/'reloaded.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path));await unchanged()
        for q in [dict(kind='yybar_diagram'),dict(kind='incident_angle_vs_image_height')]:
            await e.finish(await e.call('run_analysis',dict(request=q)))
    asyncio.run(execute('ray384_lifecycle',work))

@pytest.mark.zemax
def test_incidence_clipping_and_all_blocked_failure():
    async def work(e):
        await e.call('new_system');await e.call('insert_surfaces',dict(at=1))
        caps=await e.call('get_capabilities')
        assert 'acceptance400-ray-diagrams.json'in caps['analyses']['incident_angle_vs_image_height']['verification']
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,fields=[dict(x=0,y=0),dict(x=0,y=20)],wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=50,semi_diameter=5,is_stop=True,replace_solves=True),
            dict(surface=2,thickness=50,semi_diameter=5,aperture=dict(type='CircularAperture',maximum_radius=.5),replace_solves=True)]))
        r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height',field_density=11))))
        (e.folder/'clipping.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        assert r['summary']['vignetted']>0 and not r['trace_conditions_met']
        assert r['rows'][0]['chief_angle_deg']==0 and r['rows'][0]['lower_angle_deg']is None and r['rows'][0]['upper_angle_deg']is None
        assert r['series'][0]['invalid_count']>0
        await e.call('update_surfaces',dict(changes=[dict(surface=3,aperture=dict(type='CircularObscuration',maximum_radius=100))]))
        t=await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height',field_density=11)))
        while t['state']not in {'succeeded','failed','cancelled'}:
            await asyncio.sleep(.02);t=await e.call('get_task_status',dict(task_id=t['task_id']))
        assert t['state']=='failed'
        failed=await e.call('get_task_result',dict(task_id=t['task_id']))
        assert failed['error']['code']=='NO_VALID_RAYS'
        await e.call('update_surfaces',dict(changes=[dict(surface=3,radius=100,aperture=dict(type='None'))]))
        err=await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height')),okay=False)
        assert err['error']['code']=='PRECONDITION_FAILED'
    asyncio.run(execute('ray385_clipped',work))


@pytest.mark.zemax
@pytest.mark.parametrize('model',['mirror','image_glass','image_power','image_power_glass'])
def test_image_incidence_reflection_sign_and_before_refraction(model):
    async def work(e):
        path=Path(__file__).resolve().parents[1]/'verification/development/CV-02'/dict(mirror='probe386-mirror',image_glass='probe387-image-glass',image_power='probe392-image-power',image_power_glass='probe393-image-power-glass')[model]/'probe.json'
        native=json.loads(path.read_text(encoding='utf-8'))
        (e.folder/'conditions.json').write_text(json.dumps(dict(angle_atol=1e-6,image_height_atol=1e-5,
            reference='Matched native worksheet; mirror chief angle=-field, glass image incidence=field before Snell refraction'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,
            fields=[dict(x=0,y=0),dict(x=0,y=2 if model=='mirror'else 10)],wavelengths=[dict(wavelength_um=.55)])))
        if model=='mirror':changes=[dict(surface=1,radius=-200,conic=-1,material='MIRROR',thickness=-100,semi_diameter=10,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=20,replace_solves=True)]
        else:changes=[dict(surface=1,thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=100,replace_solves=True)|(dict(material='N-BK7')if model=='image_glass'else dict(surface_type='Paraxial',parameters={'1':10},material='N-BK7'if model=='image_power_glass'else''))]
        await e.call('update_surfaces',dict(changes=changes))
        before=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        if model=='mirror':
            yy=await e.finish(await e.call('run_analysis',dict(request=dict(kind='yybar_diagram'))))
            rows=[]
            for line in native['analyses'][0]['text'].splitlines():
                m=re.fullmatch(r'\s*(\d+)\s+([-+\d.Ee]+)\s+([-+\d.Ee]+)\s*',line)
                if m:rows.append((int(m[1]),float(m[2]),float(m[3])))
            for row,(surface,chief,marginal)in zip(yy['rows'],rows):
                e.check('mirror native Y-bar',row['chief_y'],chief,atol=5e-9,rtol=0)
                e.check('mirror native Y',row['marginal_y'],marginal,atol=5e-9,rtol=0)
        r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height'))))
        (e.folder/'outlets.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        raw=[]
        for line in native['analyses'][1]['text'].splitlines():
            parts=line.split()
            if len(parts)!=4:continue
            try:raw.append(list(map(float,parts)))
            except ValueError:pass
        assert len(raw)==len(r['rows'])==21
        for row,want in zip(r['rows'],raw):
            e.check('native reference image height',row['image_height'],want[0],atol=1e-5,rtol=0)
            for key,value in zip(['lower_angle_deg','chief_angle_deg','upper_angle_deg'],want[1:]):e.check('native '+key,row[key],value,atol=1e-6,rtol=0)
            if model!='image_power':e.check('signed physical chief angle',row['chief_angle_deg'],row['field_y']*(-1 if model=='mirror'else 1),atol=1e-8,rtol=1e-7)
        if model in ('image_glass','image_power_glass'):assert r['incoming_trace_copy']['closed'] and r['incoming_trace_copy']['copy_image_material']==''
        assert await e.call('get_surfaces')==before
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
    asyncio.run(execute('ray388_'+model,work))


@pytest.mark.zemax
def test_ray_diagrams_configuration_units_and_field_normalization():
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(atol=1e-8,rtol=1e-7,
            reference='Thin lens transfer at100/200cm; rectangular and radial fields with X40/Y20; positive Y incidence scan covers0..20degrees'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(lens_units='Centimeters',aperture_value=10,
            wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=40,y=0),dict(x=0,y=20)],field_normalization='Rectangular')))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Paraxial',parameters={'1':100},
            thickness=100,semi_diameter=500,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=500,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],
            operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=100),dict(configuration=2,value=200)])])))
        for config,thickness in [(1,100),(2,200)]:
            await e.call('set_configuration',dict(configuration=config))
            r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='yybar_diagram',first_surface=1,last_surface=2))))
            assert r['unit']=='Centimeters' and r['actual_settings']['configuration']==config
            e.check('configuration chief',r['rows'][1]['chief_y'],thickness*math.tan(math.radians(20)),atol=1e-8,rtol=1e-7)
            e.check('configuration marginal',r['rows'][1]['marginal_y'],5*(1-thickness/100),atol=1e-8,rtol=1e-7)
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='Standard',replace_solves=True)]))
        for normalization in ['Rectangular','Radial']:
            await e.call('update_system_settings',dict(settings=dict(field_normalization=normalization)))
            r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height',field_density=5))))
            assert r['actual_settings']['configuration']==2 and r['image_height_unit']=='Centimeters'
            assert r['actual_settings']['field_range']==[0,40 if normalization=='Radial'else 20]
            for row in r['rows']:
                e.check('field normalization height',row['image_height'],200*math.tan(math.radians(row['field_y'])),atol=1e-8,rtol=1e-7)
                e.check('field normalization angle',row['chief_angle_deg'],row['field_y'],atol=1e-8,rtol=1e-7)
    asyncio.run(execute('ray389_configuration',work))

@pytest.mark.zemax
def test_image_glass_copy_cancel_and_failure_preserve_source():
    import time
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,fields=[dict(x=0,y=0),dict(x=0,y=10)],wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,material='N-BK7',semi_diameter=100,replace_solves=True)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        t=await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height',field_density=1001)))
        t=await e.call('get_task_status',dict(task_id=t['task_id']))
        assert t['state']=='running'
        t=await e.call('cancel_task',dict(task_id=t['task_id']))
        deadline=time.monotonic()+30
        while t['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);t=await e.call('get_task_status',dict(task_id=t['task_id']))
        assert t['state']=='cancelled'
        result=await e.call('get_task_result',dict(task_id=t['task_id']))
        assert result['incoming_trace_copy']['closed']
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height',field_density=5))))
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings and await e.call('get_merit_function')==merit
        await e.call('update_surfaces',dict(changes=[dict(surface=2,aperture=dict(type='CircularObscuration',maximum_radius=1000))]))
        blocked=await e.call('get_surfaces')
        t=await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height',field_density=5)))
        while t['state']not in {'succeeded','failed','cancelled'}:
            await asyncio.sleep(.02);t=await e.call('get_task_status',dict(task_id=t['task_id']))
        result=await e.call('get_task_result',dict(task_id=t['task_id']))
        assert t['state']=='failed' and result['error']['code']=='NO_VALID_RAYS'
        assert result['incoming_trace_copy']['closed']
        assert await e.call('get_surfaces')==blocked
    asyncio.run(execute('ray390_copy_lifecycle',work))


@pytest.mark.zemax
@pytest.mark.parametrize('model',['fields_mixed','fields_negative','finite_object'])
def test_ray_diagram_field_range_and_finite_object_reference(model):
    async def work(e):
        folders=dict(fields_mixed='probe395-fields-mixed',fields_negative='probe397-fields-negative',finite_object='probe398-finite-object')
        native=json.loads((Path(__file__).resolve().parents[1]/'verification/development/CV-02'/folders[model]/'probe.json').read_text(encoding='utf-8'))
        await e.call('new_system')
        fields=[dict(x=40,y=0),dict(x=0,y=20)]if model=='fields_mixed'else[dict(x=0,y=0),dict(x=0,y=-20 if model=='fields_negative'else 20)]
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,fields=fields,wavelengths=[dict(wavelength_um=.55)],field_type='ObjectHeight'if model=='finite_object'else'Angle')))
        changes=[dict(surface=1,thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=100,replace_solves=True)]
        if model=='finite_object':changes.insert(0,dict(surface=0,thickness=100,replace_solves=True))
        await e.call('update_surfaces',dict(changes=changes))
        r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height'))))
        (e.folder/'incident.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        text=[]
        for line in native['analyses'][1]['text'].splitlines():
            parts=line.split()
            if len(parts)!=4:continue
            try:text.append(list(map(float,parts)))
            except ValueError:pass
        for row,reference in zip(r['rows'],text):
            e.check('field range native image height',row['image_height'],reference[0],atol=1e-5,rtol=0)
            for key,value in zip(['lower_angle_deg','chief_angle_deg','upper_angle_deg'],reference[1:]):e.check('field range '+key,row[key],value,atol=1e-6,rtol=0)
            if model=='finite_object':
                e.check('finite object height',row['image_height'],-row['field_y'],atol=1e-8,rtol=1e-7)
                for key,pupil in [('lower_angle_deg',-5),('chief_angle_deg',0),('upper_angle_deg',5)]:
                    e.check('finite object physical '+key,row[key],math.degrees(math.atan((pupil-row['field_y'])/100)),atol=1e-8,rtol=1e-7)
        if model=='finite_object':
            yy=await e.finish(await e.call('run_analysis',dict(request=dict(kind='yybar_diagram',first_surface=0))))
            assert len(yy['rows'])==3
            for row,chief,marginal in zip(yy['rows'],[20,0,-20],[0,5,10]):
                e.check('finite Y-bar',row['chief_y'],chief,atol=1e-8,rtol=1e-7)
                e.check('finite Y',row['marginal_y'],marginal,atol=1e-8,rtol=1e-7)
    asyncio.run(execute('ray399_'+model,work))


@pytest.mark.zemax
def test_nonplanar_material_image_is_rejected_and_copy_closed():
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0),dict(x=0,y=10)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),
            dict(surface=2,surface_type='EvenAspheric',radius='Infinity',parameters={'1':.001},material='N-BK7',semi_diameter=100,replace_solves=True)]))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
        t=await e.call('run_analysis',dict(request=dict(kind='incident_angle_vs_image_height',field_density=5)))
        while t['state']not in {'succeeded','failed','cancelled'}:
            await asyncio.sleep(.02);t=await e.call('get_task_status',dict(task_id=t['task_id']))
        result=await e.call('get_task_result',dict(task_id=t['task_id']))
        assert t['state']=='failed' and result['error']['code']=='PRECONDITION_FAILED'
        assert result['incoming_trace_copy']['closed']
        assert await e.call('get_surfaces')==baseline
        assert await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit
        await e.finish(await e.call('run_analysis',dict(request=dict(kind='yybar_diagram'))))
    asyncio.run(execute('ray402_nonplanar',work))
