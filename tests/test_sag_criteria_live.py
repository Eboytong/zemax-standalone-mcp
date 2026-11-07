"""Formal SSAG criterion curves, independent sag derivatives and stdio lifecycle."""
import asyncio,json,math
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('sign',[1,-1])
def test_sag_table_criterion_curves(sign):
    async def work(e):
        conditions=dict(reference='z=sign*.0126*r² and analytic slope; native criterion radius cross-check against independently configured SurfaceSlopeCross report',
            row_atol=1e-8,row_rtol=1e-6,report_radius_atol=5e-6,
            manufacturing='physical vertex offset and manufacturing statistics unavailable for new curve paths')
        (e.folder/'conditions.json').write_text(json.dumps(conditions,indent=2),encoding='utf-8')
        await e.call('new_system')
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',radius=sign*40,
            conic=-1,parameters={'1':sign*.0001},semi_diameter=5,thickness=20,replace_solves=True)]))
        path=str(e.folder/'baseline.zos')
        await e.call('save_lens_as',dict(path=path));await e.call('open_lens',dict(path=path))
        baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings')
        merit=await e.call('get_merit_function');configs=await e.call('get_configurations',dict(request={}))
        results=[]
        for criterion,reverse,flag in [('MinimumRMS',False,1),('MinimumRMSWithOffset',False,2),('MinimumVolume',True,3)]:
            q=dict(kind='sag_table',surface=1,best_fit_sphere=criterion,reverse=reverse,samples=11)
            result=await e.finish(await e.call('run_analysis',dict(request=q)),timeout_seconds=180)
            results.append(result)
            (e.folder/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
            assert result['actual_settings']['criterion']==criterion
            assert result['actual_settings']['reverse']==reverse
            assert result['summary']['vertex_offset']==(0. if criterion=='MinimumRMS'else None)
            assert result['manufacturing_state']==('unavailable'if reverse else'not_applicable')
            assert all(x['arguments'][6]==flag for x in result['native_query_arguments'])
            if not reverse:
                native_fit=result['native_bfs_fit']
                assert native_fit['curve_radius_check']['passed'],native_fit
                e.check(criterion+' DSAG curve radius',native_fit['radius'],result['summary']['radius'],atol=5e-6,rtol=0)
                from support.sag_rms_reference import fit_paraboloid
                independent=fit_paraboloid(sign*.0126,5,criterion=='MinimumRMSWithOffset')
                e.check(criterion+' raw DSAG signed offset',native_fit['vertex_z_offset'],-independent['offset'],atol=1e-8,rtol=1e-6)
                assert 'unconfirmed'in native_fit['offset_interpretation']
            c=result['summary']['curvature']
            import numpy as np
            ys=np.linspace(0.,5.,1001)
            differences=sign*.0252*ys-c*ys/np.sqrt(1-(c*ys)**2)
            e.check(criterion+' maximum slope summary',result['summary']['maximum_slope_difference'],float(max(abs(differences))),atol=1e-6,rtol=1e-5)
            e.check(criterion+' RMS slope summary',result['summary']['rms_slope_difference'],float(np.sqrt(sum(ys*differences*differences)/sum(ys))),atol=1e-6,rtol=1e-5)
            assert result['statistics_sampling']['completed_nodes']==1001
            for row in result['rows']:
                y=row['y'];root=math.sqrt(1-(c*y)**2)
                expected=dict(sag=sign*.0126*y*y,slope=sign*.0252*y,bfs_sag=c*y*y/(1+root),bfs_slope=c*y/root)
                expected['deviation']=expected['sag']-expected['bfs_sag']
                expected['slope_difference']=expected['slope']-expected['bfs_slope']
                for key,value in expected.items():e.check(criterion+' '+key,row[key],value,atol=1e-8,rtol=1e-6)
                assert row['removal_depth']is None
            reference=await e.finish(await e.call('run_analysis',dict(request=dict(kind='surface_slope_cross',surface=1,
                remove_option='BestFitSphere',best_fit_sphere=criterion,reverse_direction=reverse if criterion=='MinimumVolume'else None,angle=90))))
            import re
            texts=[Path(a['path']).read_text(encoding='utf-16')for a in reference['artifacts']if a['kind']=='native_text']
            text='\n'.join(texts)
            match=re.search(r'(?:曲率半径|radius(?: of curvature)?)\s*=\s*([-+0-9.eE]+)',text,re.IGNORECASE)
            assert match,text[:1200]
            e.check(criterion+' independent native report radius',result['summary']['radius'],float(match[1]),atol=5e-6,rtol=0)
            tid=result['task']['task_id']
            page=await e.call('get_task_result',dict(task_id=tid,start=2,count=4))
            assert page['rows']==result['rows'][2:6]
            png=e.folder/(criterion+str(reverse)+'.png')
            await e.call('export_analysis_image',dict(request=dict(task_id=tid,path=str(png),item=1)))
            from PIL import Image
            with Image.open(png)as image:assert image.width>0 and image.height>0
            status=await e.call('get_task_status',dict(task_id=tid))
            assert status['state']=='succeeded' and not status.get('cleanup_warnings')
            assert (await e.call('get_task_status',dict(task_id=reference['task']['task_id'])))['close_attempted']
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit and await e.call('get_configurations',dict(request={}))==configs
        reloaded=str(e.folder/'after.zos')
        await e.call('save_lens_as',dict(path=reloaded));await e.call('open_lens',dict(path=reloaded))
        assert await e.call('get_surfaces')==baseline and await e.call('get_system_settings')==settings
        assert await e.call('get_merit_function')==merit and await e.call('get_configurations',dict(request={}))==configs
    async def guarded(e):
        try:await work(e)
        except BaseException:
            await e.call('disconnect',okay=False)
            raise
    asyncio.run(execute('sag587_criteria_'+str(sign),guarded))
