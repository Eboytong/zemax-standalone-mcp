from zemax_mcp.config import PROJECT_ROOT
import asyncio,math
import pytest
from tests.support.native import execute

@pytest.mark.zemax
def test_biocular_two_plane_reference():
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=100,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=100),dict(configuration=2,value=120)])])))
        surfaces=await e.call('get_surfaces');configs=await e.call('get_configurations',dict(request={}));merit=await e.call('get_merit_function')
        for axis in ['X','Y']:
            r=await e.finish(await e.call('run_analysis',dict(request=dict(kind='biocular_dipvergence_convergence',scan_axis=axis,minimum=10,maximum=-10,points=5,offsets=[0,-99]))))
            assert len(r['rows'])==5
            for row in r['rows']:
                angle=math.radians(row['scan_value']);expected=1000*(math.atan(100/120*math.tan(angle))-angle)
                e.check('independent matched chief angle',row['raw_convergence_mrad']if axis=='X'else row['dipvergence_mrad'],expected,atol=.001,rtol=0)
                e.check('orthogonal component',row['dipvergence_mrad']if axis=='X'else row['raw_convergence_mrad'],0,atol=.001,rtol=0)
        assert await e.call('get_surfaces')==surfaces and await e.call('get_configurations',dict(request={}))==configs
        assert await e.call('get_merit_function')==merit
    asyncio.run(execute('biocular406_planes',work))


@pytest.mark.zemax
def test_biocular_offsets_cosines_native_text_and_lifecycle():
    import json,re,time
    from pathlib import Path
    from PIL import Image
    async def work(e):
        (e.folder/'conditions.json').write_text(json.dumps(dict(atol_mrad=.001,reference='Native worksheet and independent2D direction-cosine plane matching; tolerances set before run'),indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=100,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=100),dict(configuration=2,value=120)])])))
        await e.call('set_configuration',dict(configuration=2))
        surfaces=await e.call('get_surfaces');settings=await e.call('get_system_settings');configs=await e.call('get_configurations',dict(request={}));merit=await e.call('get_merit_function')
        q=dict(kind='biocular_dipvergence_convergence',minimum=5,maximum=-5,offsets=[-5,-3,-1,1,3,5],points=21)
        r=await e.finish(await e.call('run_analysis',dict(request=q)))
        (e.folder/'six-offsets.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
        raw=json.loads((PROJECT_ROOT/'development/evidence/CV-02/probe405-biocular-operands/probe.json').read_text(encoding='utf-8'))['analyses'][0]['text']
        expected=[]
        for line in raw.splitlines():
            m=re.fullmatch(r'\s*([-+\d.Ee]+)\s+([-+\d.Ee]+)\s+([-+\d.Ee]+)\s*',line)
            if m:expected.append(list(map(float,m.groups())))
        assert len(r['rows'])==len(expected)==126 and len(r['series'])==6
        for row,(scan,dip,conv)in zip(r['rows'],expected):
            assert row['scan_value']==scan
            e.check('native worksheet dip',row['dipvergence_mrad'],dip,atol=.001,rtol=0)
            e.check('native worksheet convergence',row['raw_convergence_mrad'],conv,atol=.001,rtol=0)
        cosine=await e.finish(await e.call('run_analysis',dict(request=dict(kind=q['kind'],scan_axis='X',use_angles=False,minimum=.1,maximum=-.1,points=5,offsets=[0,.02],convergence_offset_mrad=1.25))))
        for row in cosine['rows']:
            x,y=row['x'],row['y'];n=math.sqrt(1-x*x-y*y)
            for value,actual in [(x,row['raw_convergence_mrad']),(y,row['dipvergence_mrad'])]:
                expected=1000*(math.atan(100/120*value/n)-math.atan(value/n))
                e.check('cosine plane matching',actual,expected,atol=.001,rtol=0)
            e.check('compensation',row['convergence_mrad'],row['raw_convergence_mrad']-1.25,atol=1e-12,rtol=0)
        same=await e.finish(await e.call('run_analysis',dict(request=dict(kind=q['kind'],left_configuration=2,right_configuration=2,minimum=0,maximum=0,points=2))))
        for row in same['rows']:
            e.check('same eye convergence',row['raw_convergence_mrad'],0,atol=.001,rtol=0)
        page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],series=2,start=2,count=3))
        assert page['series'][0]['y']==r['series'][2]['y'][2:5]
        page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=20,count=4))
        assert page['rows']==r['rows'][20:24]
        png=e.folder/'biocular.png'
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(png),item=0)))
        with Image.open(png)as image:assert image.width>0
        bad=await e.call('run_analysis',dict(request=q|dict(right_configuration=999)),okay=False)
        assert bad['error']['code']=='INDEX_OUT_OF_RANGE'
        t=await e.call('run_analysis',dict(request=q|dict(points=1001)))
        t=await e.call('cancel_task',dict(task_id=t['task_id']))
        deadline=time.monotonic()+30
        while t['state']not in {'succeeded','failed','cancelled'}:
            assert time.monotonic()<deadline
            await asyncio.sleep(.02);t=await e.call('get_task_status',dict(task_id=t['task_id']))
        assert t['state']=='cancelled'
        await e.finish(await e.call('run_analysis',dict(request=q|dict(points=3))))
        async def unchanged():
            assert await e.call('get_surfaces')==surfaces
            assert await e.call('get_system_settings')==settings
            assert await e.call('get_configurations',dict(request={}))==configs
            assert await e.call('get_merit_function')==merit
        await unchanged()
        saved=str(e.folder/'reloaded.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved));await unchanged()
    asyncio.run(execute('biocular408_full',work))


@pytest.mark.zemax
def test_biocular_eye_swap_and_clipped_zero_rejection():
    async def work(e):
        await e.call('new_system')
        await e.call('update_system_settings',dict(settings=dict(aperture_value=10,wavelengths=[dict(wavelength_um=.55)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=100,is_stop=True,replace_solves=True),dict(surface=2,semi_diameter=100,replace_solves=True)]))
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],operands=[dict(type='THIC',parameters={'1':1},cells=[dict(configuration=1,value=100),dict(configuration=2,value=120)])])))
        q=dict(kind='biocular_dipvergence_convergence',left_configuration=2,right_configuration=1,scan_axis='X',minimum=-10,maximum=10,points=3)
        swapped=await e.finish(await e.call('run_analysis',dict(request=q)))
        for row in swapped['rows']:
            angle=math.radians(row['scan_value']);value=1000*(math.atan(120/100*math.tan(angle))-angle)
            e.check('swapped independent eyes',row['raw_convergence_mrad'],value,atol=.001,rtol=0)
        assert all(c['closed']for c in swapped['validation_copies'])
        await e.call('update_surfaces',dict(changes=[dict(surface=2,aperture=dict(type='CircularAperture',maximum_radius=.01))]))
        before=await e.call('get_surfaces')
        t=await e.call('run_analysis',dict(request=q|dict(minimum=10,maximum=10,points=2)))
        while t['state']not in {'succeeded','failed','cancelled'}:
            await asyncio.sleep(.02);t=await e.call('get_task_status',dict(task_id=t['task_id']))
        r=await e.call('get_task_result',dict(task_id=t['task_id']))
        assert t['state']=='failed' and r['error']['code']=='NO_VALID_BIOCULAR_POINTS'
        assert all(row['raw_convergence_mrad']==0 and row['convergence_mrad']is None and row['state']=='invalid' for row in r['rows'])
        assert all(c['closed']for c in r['validation_copies'])
        assert await e.call('get_surfaces')==before
    asyncio.run(execute('biocular412_clipped',work))
