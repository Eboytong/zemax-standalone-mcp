"""Shared HPC preferences success-acceptance flow.

Kept in ``tests/support`` (NOT in a native test module) so offline unit drivers can import
the SAME flow without importing ``tests/native/test_hpc_live.py``. It assumes the normalized
``tests.support.native.Evidence.call`` contract: success -> ``data`` dict;
failure -> ``{'ok': False, 'error': {...}}``.
"""


async def check_preferences_success(e):
    """Shared success-acceptance flow using the normalized Evidence.call contract:
    success -> data dict; failure -> {'ok':False,'error':...}. Returns
    ('success', actual) or ('skipped', reason). A partial/empty success dict, or any
    missing/invalid field, FAILS (does not skip). Offline drivers exercise this
    through the real Evidence.call normalization; see tests/unit/test_hpc_success_driver.py.
    """
    before=await e.call('get_status')
    response=await e.call('get_hpc_settings',{'request':{'mode':'preferences'}},okay=False)
    after=await e.call('get_status')
    # Runtime observation: get_status exposes task/reconnect state only; this delta
    # proves NO TASK was created, not that no SystemTool was (there is no public
    # per-SystemTool observer - see source-path review below).
    assert after['requires_reconnect'] is False
    assert set(after['task_index'])-set(before['task_index'])==set(),'HPC settings query must not create tasks'
    assert after.get('running_tasks')==before.get('running_tasks')==[]
    if response.get('ok') is False:
        assert response['error']['code']=='HPC_SETTINGS_UNAVAILABLE',response
        assert response['error']['details']['native_method']=='GetHPCSettingsFromPrefs'
        assert response['error']['details']['partial_changes_possible'] is False
        disconnect_response=await e.call('disconnect')
        assert disconnect_response['connected'] is False
        print('disconnect response:',disconnect_response,flush=True)
        return ('skipped','GetHPCSettingsFromPrefs returned no IHPCSettings; success path needs a non-null native object (error path covered by test_hpc_native_configuration_query).')
    actual=response
    # A non-null success must be a populated settings dict; missing fields fail here.
    assert actual is not None and isinstance(actual,dict) and bool(actual),'success response must be a non-empty settings dict'
    assert type(actual['is_configured']) is bool
    assert type(actual['node_count']) is int
    assert type(actual['max_node_count']) is int
    assert type(actual['threads_per_task']) is int
    assert type(actual['shutdown_time_ticks']) is int
    assert isinstance(actual['instance_type'],str) and actual['instance_type']
    assert actual['source']=='GetHPCSettingsFromPrefs'
    # ownership is a product-declared string recorded here; it is NOT the sole no-SystemTool
    # proof. No-SystemTool evidence is (a) the task-index delta above (no task created) and
    # (b) source-path review of src/zemax_mcp/hpc.py:83-88 (only Tools.GetHPCSettingsFromPrefs;
    # opens no tool factory; IHPCSettings has no Close). get_status has no per-SystemTool field.
    assert actual['ownership']=='IHPCSettings has no Close method; no SystemTool opened by this query'
    assert actual['is_configured'] in (True,False)
    disconnect_response=await e.call('disconnect')
    assert disconnect_response['connected'] is False
    print('disconnect response:',disconnect_response,flush=True)
    return ('success',actual)
