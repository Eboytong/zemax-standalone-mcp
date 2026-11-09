import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.hpc import check_preferences_success


@pytest.mark.zemax
def test_hpc_native_configuration_query():
    async def work(e):
        response=await e.call('get_hpc_settings',{'request':{'mode':'preferences'}},okay=False)
        # Evidence.call normalized contract: success -> data dict; failure -> {'ok':False,'error':...}.
        if response.get('ok') is False:
            assert response['error']['code']=='HPC_SETTINGS_UNAVAILABLE'
            assert response['error']['details']['native_method']=='GetHPCSettingsFromPrefs'
            assert response['error']['details']['partial_changes_possible'] is False
        else:
            actual=response
            assert type(actual['is_configured']) is bool
            assert type(actual['node_count']) is int
            assert actual['source']=='GetHPCSettingsFromPrefs'
            assert actual['ownership']=='IHPCSettings has no Close method; no SystemTool opened by this query'
    asyncio.run(execute('hpc_settings',work))


@pytest.mark.zemax
def test_hpc_native_preferences_success_readback():
    """Independent success acceptance for get_hpc_settings (preferences).

    Error path (GetHPCSettingsFromPrefs -> null -> HPC_SETTINGS_UNAVAILABLE) is
    covered by test_hpc_native_configuration_query above and is NOT counted as a
    completed query here: on null this case skips with the concrete reason. Only a
    real non-null IHPCSettings asserts the six typed fields and source.
    """
    async def work(e):
        outcome,payload=await check_preferences_success(e)
        if outcome=='skipped':pytest.skip(payload)
    asyncio.run(execute('hpc_settings_success',work))


@pytest.mark.zemax
@pytest.mark.parametrize('kind',['nsc','tolerance','global','hammer'])
def test_hpc_minimal_native_job_result_and_close(kind):
    async def work(e):
        response=await e.call('get_hpc_settings',{'request':{'mode':'preferences'}},okay=False)
        # Evidence.call normalized contract: success -> data dict; failure -> {'ok':False,'error':...}.
        if response.get('ok') is False:
            assert response['error']['code']=='HPC_SETTINGS_UNAVAILABLE',response
            await e.call('disconnect')
            pytest.skip('GetHPCSettingsFromPrefs returned no IHPCSettings; configure HPC preferences before submitting a native job.')
        actual=response
        if not actual['is_configured']:
            await e.call('disconnect')
            pytest.skip('Native IHPCSettings reports IsHPCConfigured=false; configure nodes and feature access.')
        hpc=dict(mode='preferences')
        if kind=='nsc':
            from tests.support.nsc import setup,update
            await setup(e,2)
            await update(e,[dict(object=1,object_type='SourceRay',data={'NumberOfAnalysisRays':10,'ZCosine':1}),
                            dict(object=2,object_type='DetectorRectangle',z=10,data={'NumberXPixels':8,'NumberYPixels':8})])
            result=await e.finish(await e.call('run_nsc_ray_trace',{'request':dict(hpc=hpc,random_seed=42)}),timeout_seconds=600)
            assert result['hpc']['is_configured']
            detector=await e.call('get_detector_data',{'request':{'detector':2}})
            e.check('HPC direct-ray detector power',detector['total_flux'],1.,atol=1e-8,rtol=1e-7)
        else:
            lens=Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos'
            await e.call('open_lens',{'path':str(lens)})
            if kind=='tolerance':
                await e.call('update_tolerances',{'request':dict(mode='replace',operands=[
                    dict(type='SEED',param1=42),dict(type='TTHI',param1=1,minimum=-.001,maximum=.001)])})
                result=await e.finish(await e.call('run_tolerance_analysis',{'request':dict(mode='monte_carlo',samples=4,hpc=hpc)}),timeout_seconds=600)
                assert result['summary']['actual']['hpc']['is_configured']
            else:
                await e.call('set_variables',{'variables':[dict(surface=6,cell='thickness',variable=True,replace_solve=True)]})
                await e.call('update_merit_function',{'mode':'rms_spot_wizard'})
                tool='run_global_optimization' if kind=='global' else 'run_hammer_optimization'
                result=await e.finish(await e.call(tool,{'request':dict(runtime_seconds=2,hpc=hpc)}),timeout_seconds=600)
                assert result['summary']['optimization']['task']['settings']['hpc']['is_configured']
                assert result['summary']['independent_validation_completed']
    asyncio.run(execute('hpc_'+kind,work))
