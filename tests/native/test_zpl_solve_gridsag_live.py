"""Owned constant-return ZPL solves on the previously inactive GridSag cells."""
import asyncio
import json
import uuid
from pathlib import Path

import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_zpl_solve_gridsag_parameters_9_10():
    async def work(e):
        await e.call('new_system')
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='GridSag',replace_solves=True)]))
        grid=e.folder/'macro-grid.dat'
        grid.write_text('33 33 1 1 0\n'+'\n'.join(
            f'{.0001*(x-16)**2+.0002*(y-16)**2} {.0002*(x-16)} {.0004*(y-16)} 0'
            for y in range(33) for x in range(33)),encoding='ascii')
        await e.call('update_surfaces',dict(changes=[dict(surface=1,import_file=str(grid),replace_solves=True)]))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,parameters={'13':4},replace_solves=True)]))
        resource=await e.call('get_system_resources',dict(request=dict(kind='extension_files',extension_role='zpl')))
        files=[];records=[]
        try:
            for value in [.125,.25]:
                name='M'+uuid.uuid4().hex[:12] if value==.125 else '宏'*25+uuid.uuid4().hex[:6]
                path=Path(resource['directory'])/(name+'.ZPL')
                path.write_text('SOLVERETURN '+str(value)+'\n',encoding='ascii')
                files.append((path,value))
            baseline=await e.call('get_surfaces');settings=await e.call('get_system_settings');merit=await e.call('get_merit_function')
            for cell in ['parameter_9','parameter_10']:
                available=await e.call('get_system_resources',dict(request=dict(kind='solve_macros',surface=1,cell=cell)))
                for path,value in files:
                    assert path.stem in available['items'],available
                    response=await e.call('update_surfaces',dict(changes=[dict(surface=1,
                        solves={cell:dict(mode='zpl_macro',macro=path.stem)},replace_solves=True)]))
                    actual=response['surfaces'][0]['cells'][cell]
                    assert actual['solve']['type']=='ZPLMacro' and actual['solve']['macro']==path.stem
                    e.check(cell+' macro result '+str(value),actual['value'],value,atol=1e-10,rtol=0)
                    saved=str(e.folder/(cell+'_'+str(value)+'.zos'))
                    await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
                    reloaded=(await e.call('get_surfaces',dict(start=1,count=1)))['surfaces'][0]['cells'][cell]
                    assert reloaded['solve']==actual['solve']
                    e.check(cell+' reloaded macro result '+str(value),reloaded['value'],value,atol=1e-10,rtol=0)
                    records.append(dict(cell=cell,request_macro=path.stem,expected=value,actual=actual,reloaded=reloaded))
                    (e.folder/'macros.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
                missing=await e.call('update_surfaces',dict(changes=[dict(surface=1,
                    solves={cell:dict(mode='zpl_macro',macro='MCP339_missing')},replace_solves=True)]),okay=False)
                assert missing['error']['code']=='INVALID_RESOURCE',missing
                status=await e.call('get_status')
                arguments=dict(changes=[dict(surface=1,
                    solves={cell:dict(mode='zpl_macro',macro='A'*32)},replace_solves=True)])
                too_long=await e.client.call_tool('update_surfaces',arguments)
                (e.folder/(cell+'_name-rejection.json')).write_text(json.dumps(dict(
                    arguments=arguments,result=too_long.model_dump(mode='json')),ensure_ascii=False,indent=2),encoding='utf-8')
                assert too_long.is_error
                after=await e.call('get_status')
                assert after['model_revision']==status['model_revision'] and after['checkpoint']==status['checkpoint']
                await e.call('update_surfaces',dict(changes=[dict(surface=1,solves={cell:dict(mode='fixed')},replace_solves=True)]))
                number=cell.removeprefix('parameter_')
                old=baseline['surfaces'][1]['cells'][cell]['value']
                await e.call('update_surfaces',dict(changes=[dict(surface=1,parameters={number:old},replace_solves=True)]))
            assert await e.call('get_surfaces')==baseline
            assert await e.call('get_system_settings')==settings
            assert await e.call('get_merit_function')==merit
        finally:
            for path,_ in files:path.unlink(missing_ok=True)
    asyncio.run(execute('zpl339_gridsag',work))
