"""Serial installed-editor stdio adoption, file roundtrip and model persistence."""
import asyncio
import pytest
from support.native import execute

@pytest.mark.zemax
def test_editor_extensions_stdio():
    async def work(e):
        await e.model()
        operands=[dict(type='TTHI',param1=1,param2=1,minimum=-.01,maximum=.01,comment='first'),
                  dict(type='TTHI',param1=1,param2=1,minimum=-.02,maximum=.02,comment='second')]
        await e.call('update_tolerances',dict(request=dict(mode='replace',operands=operands)))
        patched=await e.call('update_tolerances',dict(request=dict(mode='update',updates=[dict(operand=1,maximum=.03,ignore=True)])))
        assert patched['rows'][0]['comment']=='first'and patched['rows'][0]['ignore']
        e.check('TDE maximum adopted',patched['rows'][0]['maximum'],.03,atol=1e-12,rtol=1e-12)
        await e.call('update_tolerances',dict(request=dict(mode='insert',at=2,operands=[dict(type='TTHI',param1=1,param2=1,minimum=-.04,maximum=.04,comment='inserted')])))
        await e.call('copy_editor_rows',dict(request=dict(editor='TDE',start=1,count=1,at=4)))
        metadata=await e.call('get_editor_metadata',dict(request=dict(editor='TDE',operand=1,column_count=3)))
        assert metadata['columns']and metadata['available_operand_types']
        deleted=await e.call('update_tolerances',dict(request=dict(mode='delete',operand_numbers=[2,4])))
        assert [r['comment']for r in deleted['rows']]==['first','second']
        inserted=await e.call('insert_editor_rows',dict(request=dict(editor='TDE',at=3,operand_type='TTHI')))
        assert inserted['total_after']==3
        await e.call('update_tolerances',dict(request=dict(mode='delete',operand_numbers=[3])))
        path=str(e.folder/'editor.tol')
        await e.call('save_tolerance_file',dict(path=path))
        expected=(await e.call('get_tolerances',dict(request=dict(include_metadata=True))))['rows']
        await e.call('update_tolerances',dict(request=dict(mode='update',updates=[dict(operand=1,maximum=.2)])))
        loaded=await e.call('load_tolerance_file',dict(path=path))
        assert loaded['tolerances']['rows'][0]['maximum']==.03
        restored=(await e.call('get_tolerances',dict(request=dict(include_metadata=True))))['rows']
        assert expected==restored
        mfe=await e.call('get_merit_function')
        at=mfe['total']+1
        await e.call('insert_editor_rows',dict(request=dict(editor='MFE',at=at,operand_type='REAY')))
        await e.call('copy_editor_rows',dict(request=dict(editor='MFE',start=at,at=at+1)))
        await e.call('get_editor_metadata',dict(request=dict(editor='MFE',operand=at,column_count=5)))
        mce=await e.call('get_configurations',dict(request={}))
        at=mce['total']+1
        await e.call('insert_editor_rows',dict(request=dict(editor='MCE',at=at,operand_type='THIC')))
        await e.call('update_configurations',dict(request=dict(operands=[dict(operand=at,parameters={'1':1},cells=[dict(configuration=1,value=1)])])))
        copied=await e.call('copy_editor_rows',dict(request=dict(editor='MCE',start=at,at=at+1)))
        assert copied['copied']==1
        await e.call('get_editor_metadata',dict(request=dict(editor='MCE',operand=at)))
        # THIC changes the nominal thickness; capture the final model before saving.
        expected=(await e.call('get_tolerances',dict(request=dict(include_metadata=True))))['rows']
        assert all(row['nominal']==1 for row in expected)
        expected_mfe=await e.call('get_merit_function')
        expected_mce=await e.call('get_configurations',dict(request={}))
        saved=str(e.folder/'editors.zos')
        await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        result=await e.call('get_tolerances',dict(request=dict(include_metadata=True)))
        assert result['rows']==expected
        assert await e.call('get_merit_function')==expected_mfe
        assert await e.call('get_configurations',dict(request={}))==expected_mce
    asyncio.run(execute('editor_extensions019',work))
