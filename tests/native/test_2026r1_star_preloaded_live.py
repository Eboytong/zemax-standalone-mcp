"""Exercise STAR operations using FEA data prepared by the native API."""
import asyncio
import pytest
from tests.support.native import execute
from tests.support.star_2026r1_fixture import prepared_star_lens


@pytest.mark.zemax
@pytest.mark.parametrize('data_kind',['deformation','temperature','direct_index'])
def test_2026r1_star_fit_read_unload(data_kind):
    lens=prepared_star_lens(data_kind)
    async def work(e):
        await e.call('open_lens',dict(path=str(lens)))
        request=dict(kind='fit_'+data_kind,surface=1,apply='enable')
        if data_kind=='deformation':request['deformation_option']='DeformationWithRBMs'
        fitted=await e.finish(await e.call('run_star_operation',dict(request=request)))
        assert fitted['actual']['enabled']
        result=await e.call('get_star_data',dict(request=dict(surface=1,data_kind=data_kind,
            include_points=True,count=2,sample_points=[dict(x=0,y=0,z=0)])))
        assert len(result['rows'])==2 and result['next_start']==2
        sample=result['fit_evaluations'][0]
        key,expected={'deformation':('dz',.01),'temperature':('temperature',21.),
            'direct_index':('refractive_index',1.5)}[data_kind]
        unloaded=await e.finish(await e.call('run_star_operation',dict(request=dict(
            kind='unload_'+data_kind,surface=1))))
        assert not unloaded['after']['imported']
        e.check('constant '+key,sample[key],expected,atol=1e-6,rtol=1e-7)
    asyncio.run(execute('2026r1_star_fit_unload_'+data_kind,work))


@pytest.mark.zemax
@pytest.mark.parametrize('operation',['rigid_body','configure','remove_from_fea','add_coordinate_breaks'])
def test_2026r1_star_rigid_body_operations(operation):
    lens=prepared_star_lens('deformation',fitted=True)
    async def work(e):
        await e.call('open_lens',dict(path=str(lens)))
        if operation=='rigid_body':
            request=dict(kind='rigid_body',surface=1,enabled=True,reference_point=dict(x=0,y=0,z=0))
        else:
            await e.finish(await e.call('run_star_operation',dict(request=dict(
                kind='define_component',first_surface=1,last_surface=1))))
            request=dict(kind='component_rbm',surface=1,action=operation)
            if operation=='configure':request['adjust_index_data_with_rbm']=True
        result=await e.finish(await e.call('run_star_operation',dict(request=request)))
        if operation=='rigid_body':assert result['actual']['enabled']
        else:assert result['actual']['component']['in_component']
    asyncio.run(execute('2026r1_star_rbm_'+operation,work))
