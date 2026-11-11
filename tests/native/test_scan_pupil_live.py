import asyncio
import math

import pytest

from tests.support.native import execute


@pytest.mark.zemax
def test_scanner_4f_spacing_fold_aperture_stdio():
    async def work(e):
        await e.call('new_system');await e.call('insert_surfaces',dict(at=1,count=6))
        await e.call('update_system_settings',dict(settings=dict(aperture_value=5)))
        changes=[dict(surface=1,thickness=10,semi_diameter=10,replace_solves=True),
            dict(surface=2,surface_type='CoordinateBreak',replace_solves=True,thickness=0),
            dict(surface=3,is_stop=True,material='MIRROR',thickness=0,semi_diameter=10,replace_solves=True),
            dict(surface=4,surface_type='CoordinateBreak',replace_solves=True,thickness=-50),
            dict(surface=5,surface_type='Paraxial',replace_solves=True,parameters={1:50},thickness=-100,semi_diameter=10),
            dict(surface=6,surface_type='Paraxial',replace_solves=True,parameters={1:50},thickness=-50,semi_diameter=10),
            dict(surface=7,thickness=-10,semi_diameter=5,replace_solves=True)]
        await e.call('update_surfaces',dict(changes=changes))
        original=await e.call('get_surfaces');revision=(await e.call('get_status'))['model_revision']
        q=dict(kind='scan_pupil',start_surface=1,tilt_surface=2,mirror_surface=3,return_surface=4,pupil_surface=7,image_surface=8,
            angles_deg=[-1,0,1],ray_density=5,spacing=dict(surface=4,values=[-45,-50,-55]))
        r=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
        assert r['resources']['copy_closed'] and r['summary']['candidate_count']==3
        assert r['summary']['best_candidate']['spacing']==-50
        for c in r['conjugates']:
            for axis in c['axes']:
                e.check('4f pupil magnification',axis['magnification'],-1,atol=1e-8,rtol=1e-6)
                e.check('4f differential B',axis['b'],-(c['spacing']+50),atol=1e-8,rtol=1e-6)
        for c in r['cases']:
            e.check('reflection direction',c['reflection']['max_error'],0,atol=1e-7)
            e.check('relay output double angle',c['image_chief_angles_deg'][0],-2*c['angle_deg'],atol=1e-8,rtol=1e-6)
            expected=abs((c['spacing']+50)*math.tan(math.radians(2*c['angle_deg'])))
            e.check('4f off-conjugate walk',c['beam_walk'],expected,atol=1e-8,rtol=1e-6)
        assert await e.call('get_surfaces')==original
        assert (await e.call('get_status'))['model_revision']==revision
        await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/'scanner.png'))))
        page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],start=5,count=7));assert len(page['rows'])==7
        await e.call('save_lens_as',dict(path=str(e.folder/'baseline.zos')))
        await e.call('open_lens',dict(path=r['summary']['best_candidate']['saved_model']))
        replay=await e.finish(await e.call('run_analysis',dict(request=q|dict(spacing=None))),timeout_seconds=180)
        e.check('saved pupil conjugate',replay['conjugates'][0]['axes'][0]['b'],0,atol=1e-8)
        finer=await e.finish(await e.call('run_analysis',dict(request=q|dict(spacing=None,angles_deg=[0],probe_height=.0005,probe_slope=.000005))),timeout_seconds=180)
        for i in range(4):
            for j in range(4):e.check('differential step convergence',finer['conjugates'][0]['matrix'][i][j],replay['conjugates'][0]['matrix'][i][j],atol=1e-8,rtol=1e-6)
        xscan=await e.finish(await e.call('run_analysis',dict(request=q|dict(spacing=None,axis='X'))),timeout_seconds=180)
        for c in xscan['cases']:e.check('X scan double angle',c['image_chief_angles_deg'][1],2*c['angle_deg'],atol=1e-8,rtol=1e-6)
        # Folded scanner at 45 degrees, fixed downstream plane and off-axis beam.
        await e.call('open_lens',dict(path=str(e.folder/'baseline.zos')))
        await e.call('update_surfaces',dict(changes=[dict(surface=2,parameters={4:45}),dict(surface=4,parameters={4:45})]))
        folded=await e.finish(await e.call('run_analysis',dict(request=q|dict(spacing=None,beam_center_y=.1))),timeout_seconds=180)
        for c in folded['cases']:
            e.check('fold reflection',c['reflection']['max_error'],0,atol=1e-7)
            e.check('folded 4f walk',c['beam_walk'],0,atol=1e-8)
            e.check('folded output angle',c['image_chief_angles_deg'][0],-2*c['angle_deg'],atol=1e-8,rtol=1e-6)
        # Return to baseline, clip circular pupil with known equal-weight grid count.
        await e.call('open_lens',dict(path=str(e.folder/'baseline.zos')))
        await e.call('update_surfaces',dict(changes=[dict(surface=7,is_stop=True,aperture=dict(type='CircularAperture',maximum_radius=.6))]))
        clipped=await e.finish(await e.call('run_analysis',dict(request=q|dict(spacing=None,angles_deg=[0]))),timeout_seconds=180)
        c=clipped['cases'][0]['statistics']['pupil']
        assert clipped['pupil_identity']['is_system_stop']
        e.check('stop entrance preimage',clipped['conjugates'][0]['axes'][0]['signed_local_z_of_aperture_preimage'],0,atol=1e-8)
        e.check('known circle point throughput',c['throughput'],5/13,atol=1e-12)
        # Failure and actual cancel close copies and permit reuse.
        for request,terminal in [(q|dict(mirror_surface=3,pupil_surface=7,image_surface=99),'failed'),(q,'cancelled')]:
            current=await e.call('get_surfaces')
            t=await e.call('run_analysis',dict(request=request))
            if terminal=='cancelled':await e.call('cancel_task',dict(task_id=t['task_id']))
            for _ in range(1000):
                t=await e.call('get_task_status',dict(task_id=t['task_id']))
                if t['state'] in ('succeeded','failed','cancelled'):break
                await asyncio.sleep(.02)
            assert t['state']==terminal,t
            result=await e.call('get_task_result',dict(task_id=t['task_id']))
            assert not result['resources']['cleanup_errors']
            assert await e.call('get_surfaces')==current
        await e.finish(await e.call('run_analysis',dict(request=q|dict(spacing=None,angles_deg=[0]))),timeout_seconds=180)
    asyncio.run(execute('scan_pupil_native',work))

