"""Formal Gradium profile provenance and capping boundary behavior via stdio."""
import asyncio,json
from pathlib import Path
import pytest
from support.native import execute

@pytest.mark.zemax
def test_gradium_profile_capping_boundary_diagnostic():
    async def work(e):
        record=dict(conditions=dict(profiles=['G14SFN','G14SFP'],offsets=[1.,-.2,5.6],thickness=.4,
            bounds=[0,5.8],wavelengths_um=[.58756,.55],
            pass_rule='Lower extension requires capping2/3; upper extension requires1/3; forbidden crossing has nonzero ray error',
            direction_absolute_tolerance=1e-10,reference_index_atol=1e-10,reference_index_rtol=1e-9),cases=[])
        def save():(e.folder/'extent.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        save();await e.model();await e.call('insert_surfaces',dict(at=2))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=0,thickness=1,material='',semi_diameter=1,replace_solves=True),
            dict(surface=3,radius=0,thickness=1,material='',semi_diameter=1,replace_solves=True)]))
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=.58756),dict(wavelength_um=.55)])))
        lines=(Path.home()/'Documents/Zemax/Glasscat/PROFILE.GRD').read_text().splitlines()
        for profile in record['conditions']['profiles']:
            index=next(i for i,line in enumerate(lines)if line.split()and line.split()[0]==profile)
            coefficients=[float(v)for v in lines[index+1:index+13]]
            for offset in [1.,-.2,5.6]:
                for capping in range(4):
                    await e.call('update_surfaces',dict(changes=[dict(surface=2,surface_type='Gradium',material=profile,
                        thickness=.4,radius=0,semi_diameter=1,parameters={1:.01,2:offset,8:capping},replace_solves=True)]))
                    surfaces=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
                    case=dict(profile=profile,offset=offset,capping=capping);record['cases'].append(case);save()
                    result=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(input_mode='Direct',start_surface=1,target_surface=3,
                        rays=[dict(x=0,y=0,z=0,l=0,m=0,n=1,wavelength=w)for w in [1,2]]))))
                    case['trace']=result
                    allowed=offset==1. or capping in ([2,3]if offset<0 else[1,3]);case['expected_pass']=allowed;save()
                    assert len(result['rows'])==2
                    case['boundary_rule_matches']=all((row['error_code']==0)==allowed for row in result['rows'])
                    if offset==1.:assert case['boundary_rule_matches'],case
                    if all(row['error_code']==0 for row in result['rows']):
                        for row in result['rows']:
                            for actual,expected in zip(row['direction'],[0,0,1]):e.check('axial cap direction',actual,expected,atol=1e-10,rtol=0)
                        q=dict(kind='grin_profile',surface=2,wavelength=1,show_index_vs='Z',minimum_z=0,maximum_z=.4,x_value=0,y_value=0)
                        curve=await e.finish(await e.call('run_analysis',dict(request=q)))
                        case['curve']=curve;save()
                        source=curve['task']['settings']['source_surface']
                        assert source['material']==profile and source['surface_type']=='Gradium'
                        assert source['gradium']['axial_offset']==offset and source['gradium']['capping']==capping
                        assert source['gradium']['profile_file']
                        case['reference_index_prediction']=sum(c*(offset/5.8)**i for i,c in enumerate(coefficients))
                        # RefN is the vertex display, not a replacement for the traced curve.
                        case['display_reference_index']=source['gradium']['reference_vertex_index']
                        status=await e.call('get_task_status',dict(task_id=curve['task']['task_id']))
                        assert status['state']=='succeeded'and status['close_attempted']and not status.get('cleanup_warnings')
                    assert await e.call('get_surfaces')==surfaces and await e.call('get_system_settings')==settings
                    assert await e.call('get_merit_function')==merit
                    case['preserved']=True;save()
        record['boundary_acceptance']=all(c['boundary_rule_matches']for c in record['cases'])
        record['diagnostic_scope']='Passing test confirms result ownership and input provenance; boundary_acceptance separately records documented capping agreement'
        save()
    async def guarded(e):
        try:await work(e)
        except BaseException:
            await e.call('disconnect',okay=False)
            raise
    asyncio.run(execute('gradium629_extent_diagnostic',guarded))
