"""Controlled radius/comment changes through the real stdio entry point."""
import asyncio,json
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_file_comparator_reference():
    async def work(e):
        await e.model()
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=50,comment='COMPARATOR_BASE',replace_solves=True)]))
        file1=str(e.folder/'original.zos')
        await e.call('save_lens_as',dict(path=file1))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,radius=60,comment='COMPARATOR_CHANGED',replace_solves=True)]))
        file2=str(e.folder/'changed.zos')
        await e.call('save_lens_as',dict(path=file2))
        baseline=await e.call('get_surfaces',dict(request={}))
        records=[]
        for same,config in [(False,None),(True,None),(False,1)]:
            req=dict(kind='file_comparator',file1=file1,file2=file1 if same else file2)
            if config is not None:req.update(file1_configuration=config,file2_configuration=config)
            t=await e.call('run_analysis',dict(request=req))
            result=await e.finish(t)
            text='\n'.join(row['text']for row in result['rows'])
            records.append(dict(same=same,config=config,task_id=t['task_id'],text=text))
            if not same:
                assert 'COMPARATOR_BASE' in text and 'COMPARATOR_CHANGED' in text,text
                assert '50.000' in text and '60.000' in text,text
            else:
                assert 'COMPARATOR_BASE' not in text and '<c Blue>' not in text
            page=await e.call('get_task_result',dict(task_id=t['task_id'],start=2,count=3))
            assert page['rows']==result['rows'][2:5]
            status=await e.call('get_task_status',dict(task_id=t['task_id']))
            assert status['close_attempted'] and status['state']=='succeeded'
            assert await e.call('get_surfaces',dict(request={}))==baseline
        (e.folder/'comparison-reference.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
    asyncio.run(execute('comparator067',work))


@pytest.mark.zemax
def test_file_comparator_configurations_and_selection():
    async def work(e):
        await e.model()
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],
            operands=[dict(type='CRVT',parameters={1:1},cells=[dict(configuration=1,value=.02),dict(configuration=2,value=.01)])])))
        source=str(e.folder/'configs.zos')
        await e.call('save_lens_as',dict(path=source))
        await e.call('open_lens',dict(path=source))
        baseline=await e.call('get_configurations',dict(request={}))
        surfaces=await e.call('get_surfaces',dict(request={}))
        from zemax_mcp.comparator import FLAGS
        flags={k:False for k in FLAGS}
        flags.update(include_surface_data=True,show_differences_only=True)
        req=dict(kind='file_comparator',file1=source,file2=source,file1_configuration=1,file2_configuration=2,**flags)
        result=await e.finish(await e.call('run_analysis',dict(request=req)))
        text='\n'.join(r['text']for r in result['rows'])
        assert '<c Blue>50' in text and '<c Red>100' in text,text
        actual=result['task']['settings']['native']
        assert actual['File1Config']==1 and actual['File2Config']==2
        assert actual['IncludeSurfaceData'] and not actual['IncludeSurfaceDetail']
        assert await e.call('get_configurations',dict(request={}))==baseline
        assert await e.call('get_surfaces',dict(request={}))==surfaces
        invalid=await e.call('run_analysis',dict(request={**req,'file2_configuration':99}),okay=False)
        (e.folder/'invalid-config.json').write_text(json.dumps(invalid,ensure_ascii=False,indent=2),encoding='utf-8')
        if 'task_id' in invalid:
            import time
            deadline=time.monotonic()+30
            while invalid['state']not in {'succeeded','failed','cancelled'}:
                assert time.monotonic()<deadline
                await asyncio.sleep(.02);invalid=await e.call('get_task_status',dict(task_id=invalid['task_id']))
            assert invalid['state']=='failed',invalid
            assert invalid['close_attempted']
        else:
            assert not invalid['ok']
        assert await e.call('get_configurations',dict(request={}))==baseline
        await e.finish(await e.call('run_analysis',dict(request=req)))
    asyncio.run(execute('comparator067_config',work))

