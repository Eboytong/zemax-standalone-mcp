import asyncio
import json
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_mixed_group_object_editing_and_reload_native():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=3))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=5,replace_solves=True),
            dict(surface=2,surface_type='NonSequential',replace_solves=True),
            dict(surface=3,surface_type='CoordinateBreak',parameters={3:5},thickness=3,replace_solves=True),
            dict(surface=4,surface_type='NonSequential',replace_solves=True)]))
        original=(await e.call('get_capabilities'))['active_nsc_surface']
        records=[]
        for group in (2,4):
            await e.call('insert_nsc_objects',dict(request=dict(nsc_surface=group,at=1,count=2)))
            result=await e.call('update_nsc_objects',dict(request=dict(nsc_surface=group,changes=[
                dict(object=1,object_type='NullObject',x=group,y=-1,z=2,tilt_y=5,replace_solves=True),
                dict(object=2,object_type='Rectangle',ref_object=1,x=.5,y=.25,z=1,material='MIRROR',
                     data=dict(XHalfWidth=1,YHalfWidth=2),replace_solves=True)])))
            records.append(result)
            assert result['nsc_surface']==group and result['rows'][1]['ref_object']==1
            assert (await e.call('get_capabilities'))['active_nsc_surface']==original
            transform=result['rows'][0]['global_transform']
            for a,b in zip(transform['translation'],[group,-1,2]):e.check('NSC group-local placement mm',a,b)
            e.check('signed reference rotation',transform['rotation'][0][2],__import__('math').sin(__import__('math').radians(5)))
            copied=await e.call('copy_nsc_objects',dict(request=dict(nsc_surface=group,start=2,count=1,at=3)))
            assert copied['copied']==1
            deleted=await e.call('delete_nsc_objects',dict(request=dict(nsc_surface=group,at=3,count=1)))
            assert deleted['deleted']==1
        bad=await e.call('get_nsc_objects',dict(request=dict(nsc_surface=3)),okay=False)
        assert bad['error']['code']=='INVALID_NSC_GROUP'and not bad['error']['details']['partial_changes_possible']
        blocked=await e.call('run_nsc_ray_trace',dict(request={}),okay=False)
        assert blocked['error']['code']=='UNSUPPORTED_MODE'
        rejected=await e.call('update_nsc_objects',dict(request=dict(nsc_surface=4,changes=[
            dict(object=1,x=8,sources=dict(UnknownField=True)),dict(object=2,x=9)])),okay=False)
        assert not rejected['ok']and rejected['error']['details']['partial_changes_possible']
        assert rejected['context']['checkpoint']and not rejected['context']['requires_reconnect']
        partial=await e.call('get_nsc_objects',dict(request=dict(nsc_surface=4,start=1,count=2)))
        assert partial['rows'][0]['x']==8 and partial['rows'][1]['x']==.5
        assert (await e.call('get_capabilities'))['active_nsc_surface']==original
        await e.call('update_nsc_objects',dict(request=dict(nsc_surface=4,changes=[dict(object=1,x=4)])))
        path=e.folder/'mixed.zos';await e.call('save_lens_as',dict(path=str(path)))
        await e.call('open_lens',dict(path=str(path)))
        for group in (2,4):
            r=await e.call('get_nsc_objects',dict(request=dict(nsc_surface=group,start=1,count=2)))
            assert r['rows'][0]['x']==group and r['rows'][1]['material']=='MIRROR'and r['rows'][1]['ref_object']==1
        (e.folder/'mixed-object-reference.json').write_text(json.dumps(dict(model=str(path),groups=[2,4],
            original_editor_group=original,records=records,scope='object selection/read/write/insert/copy/delete, reference coordinates and reload; not mixed-mode tracing'),indent=2),encoding='utf-8')
    asyncio.run(execute('high_mixed_objects',work))
