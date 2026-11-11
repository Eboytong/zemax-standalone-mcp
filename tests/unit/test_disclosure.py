import asyncio
import json
from pathlib import Path

import pytest

from zemax_mcp.capability_index import build_index, describe, search
from zemax_mcp.disclosure import BOOTSTRAP, invoke, mode_value
from zemax_mcp.errors import ZemaxError
from zemax_mcp.models import COMMAND_MODELS, Capabilities
from zemax_mcp.schema_disclosure import reachable, restrict_analyses
from zemax_mcp.server import create_server


class Bridge:
    def __init__(self): self.calls = []
    async def request(self, command, arguments=None):
        self.calls.append((command, arguments))
        return dict(ok=True,data={'command':command,'arguments':arguments},error=None,warnings=[],context={},artifacts=[])
    async def close(self): pass


def test_schema_closure_including_discriminator_and_recursion():
    schema = {'$ref':'#/$defs/A','$defs':{
        'A':{'anyOf':[{'$ref':'#/$defs/B'},{'type':'null'}]},
        'B':{'discriminator':{'mapping':{'a':'#/$defs/A'}}}, 'Unused':{}}}
    assert set(reachable(schema)['$defs']) == {'A','B'}
    with pytest.raises(ZemaxError): reachable({'$ref':'#/$defs/missing'})


def test_all_exact_contracts_and_selected_nested_evaluations():
    entries = build_index()
    assert len([e for e in entries if e['category']=='tool']) == 107
    assert len([e for e in entries if e['category']=='analysis']) == 146
    for entry in entries:
        assert reachable(entry['request_schema']) == entry['request_schema']
    detail = describe(Capabilities(topic='detail',capability_id='analysis:wavefront'))
    assert len(json.dumps(detail,ensure_ascii=False,separators=(',',':')).encode()) <= 2000
    assert set(detail['request_schema']['$defs']) == {'WavefrontAnalysis'}
    candidate = describe(Capabilities(topic='detail',capability_id='action:manage_candidates:list'))
    assert 'CandidateList' in candidate['request_schema']['$defs']
    assert 'CandidateCreate' not in candidate['request_schema']['$defs']
    selected = describe(Capabilities(topic='detail',capability_id='tool:run_batch_evaluation',analysis_kinds=['wavefront']))
    defs = selected['request_schema']['$defs']
    assert 'WavefrontAnalysis' in defs and 'GlassTrials' not in defs
    with pytest.raises(ZemaxError): restrict_analyses(detail['request_schema'],['invalid'])


def test_frozen_sixty_queries():
    cases = json.loads((Path(__file__).parents[2]/'development/evidence/D023/tasks.json').read_text(encoding='utf-8'))
    assert len(cases)==60
    failures=[]
    for case in cases:
        found={e['capability_id'] for e in search(case['query'])['items']}
        if not (bool(found & set(case['expected'])) if case['expected'] else not found): failures.append(case['id'])
    assert len(failures)<=3,failures


def test_shared_handlers_preserve_wrappers_partial_updates_and_defaults():
    async def run():
        bridge=Bridge();server=create_server('compact',bridge)
        assert set(server.zemax_handlers)==set(COMMAND_MODELS)
        samples=[('tool:update_surfaces',{'changes':[{'surface':1,'thickness':3}]}),
            ('tool:update_system_settings',{'settings':{'title':'Demo'}}),
            ('tool:new_system',{}),('action:manage_candidates:list',{'request':{}}),
            ('analysis:wavefront',{'request':{'field':1}})]
        for capability,args in samples:
            result=await invoke(server.zemax_handlers,capability,args)
            assert result.ok,result
        assert bridge.calls[0]==('update_surfaces',{'changes':[{'surface':1,'thickness':3.0}]})
        assert bridge.calls[1]==('update_system_settings',{'title':'Demo'})
        assert bridge.calls[2]==('new_system',{'mode':'Sequential'})
        assert bridge.calls[3][1]['request']['action']=='list'
        assert bridge.calls[4][1]['request']['kind']=='wavefront'
        assert bridge.calls[4][1]['request']['sampling']=='S_64x64'
        before=len(bridge.calls)
        for capability,args,code,query in [
            ('tool:new_system',{},'READ_ONLY_REQUIRED',True),
            ('analysis:wavefront',{'request':{'kind':'spot'}},'CAPABILITY_MISMATCH',False),
            ('tool:update_surfaces',{'changes':[{'surface':1,'thickness':'bad'}]},'INVALID_ARGUMENT',False),
            ('tool:get_status',{'unknown':1},'INVALID_ARGUMENT',True),
            ('tool:missing',{},'UNKNOWN_CAPABILITY',False)]:
            response=await invoke(server.zemax_handlers,capability,args,query=query)
            assert not response.ok and response.error['code']==code,response
        assert len(bridge.calls)==before
    asyncio.run(run())


def test_mode_is_startup_fixed_and_invalid_mode_rejected(monkeypatch):
    monkeypatch.setenv('ZEMAX_TOOL_MODE','compact')
    assert mode_value()=='compact'
    assert mode_value('full')=='full'
    with pytest.raises(ValueError):mode_value('dynamic')


@pytest.mark.parametrize('code',['SYSTEM_BUSY','REQUEST_TIMEOUT'])
def test_compact_preserves_busy_timeout_context_and_request_receipt(code):
    async def run():
        class FailingBridge(Bridge):
            async def request(self,command,arguments=None):
                return dict(ok=False,data=None,error=dict(code=code,message='original',details={'request_id':'request-123','execution_state':'unknown'}),
                    warnings=['observe existing request'],context={'model_revision':7},artifacts=[])
        server=create_server('compact',FailingBridge())
        response=await invoke(server.zemax_handlers,'analysis:wavefront',{'request':{}})
        assert response.error['code']==code
        assert response.error['details']=={'request_id':'request-123','execution_state':'unknown'}
        assert response.context=={'model_revision':7}
        assert response.warnings==['observe existing request']
    asyncio.run(run())


def test_every_registered_capability_routes_to_the_original_handler():
    async def run():
        seen=[]
        class Recording:
            def __init__(self,name,schema):self.name=name;self.schema=schema
            async def invoke(self,arguments):
                seen.append((self.name,arguments))
                return 'same response'
        original=create_server('full',Bridge()).zemax_handlers
        handlers={name:Recording(name,original[name].schema) for name in COMMAND_MODELS}
        for entry in build_index():
            result=await invoke(handlers,entry['capability_id'],{})
            assert result=='same response'
            name,args=seen[-1]
            assert name==entry['tool_name']
            if entry.get('selector'):
                key,value=entry['selector']
                assert args=={'request':{key:value}}
            else:assert args=={}
        assert len(seen)==260
    asyncio.run(run())


def test_read_only_registry_is_explicit_and_all_errors_precede_dispatch():
    from zemax_mcp.disclosure import READ_ONLY
    assert READ_ONLY<=COMMAND_MODELS.keys()
    async def run():
        bridge=Bridge();server=create_server('compact',bridge)
        for name in COMMAND_MODELS:
            result=await invoke(server.zemax_handlers,'tool:'+name,{'__unknown__':True})
            assert not result.ok and result.error['code']=='INVALID_ARGUMENT',name
        result=await invoke(server.zemax_handlers,'analysis:wavefront',{'request':5})
        assert not result.ok and result.error['code']=='INVALID_ARGUMENT'
        assert bridge.calls==[]
    asyncio.run(run())


def test_real_stdio_compact_directory_discovery_error_and_reuse(tmp_path):
    import os,sys
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
    async def run():
        root=Path(__file__).parents[2]
        params=StdioServerParameters(command=sys.executable,args=['-B','-m','zemax_mcp'],cwd=str(root),
            env=os.environ|{'PYTHONPATH':str(root/'src'),'ZEMAX_TOOL_MODE':'compact','ZEMAX_OUTPUT_DIR':str(tmp_path)})
        async with Client(params) as client:
            tools=(await client.list_tools()).tools
            assert {t.name for t in tools}==BOOTSTRAP|{'query_capability','execute_capability'}
            assert len(json.dumps([t.model_dump(mode='json',by_alias=True,exclude_none=True) for t in tools],ensure_ascii=False,separators=(',',':')).encode())<=20000
            bad=(await client.call_tool('query_capability',{'capability_id':'tool:new_system','arguments':{}})).structured_content
            assert bad['error']['code']=='READ_ONLY_REQUIRED'
            discovery=(await client.call_tool('search_capabilities',{'query':'OPD wavefront'})).structured_content
            assert discovery['ok']
            detail=(await client.call_tool('get_capabilities',{'topic':'detail','capability_id':'analysis:wavefront'})).structured_content
            assert detail['ok'] and 'WavefrontAnalysis' in detail['data']['request_schema']['$defs']
            status=(await client.call_tool('query_capability',{'capability_id':'tool:get_status','arguments':{}})).structured_content
            assert status['ok'] and not status['data']['connected']
            assert [t.name for t in (await client.list_tools()).tools]==[t.name for t in tools]
    asyncio.run(run())
