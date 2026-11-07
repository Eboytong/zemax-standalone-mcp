import asyncio
from itertools import product
import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('data_kind', ['deformation','temperature','direct_index'])
def test_native_star_controlled_constant_data_and_shutdown(data_kind):
    async def work(e):
        await e.model()
        await e.call('update_surfaces', {'changes':[{'surface':1,'material':'N-BK7','thickness':20}]})
        source=e.folder/('controlled_'+data_kind+'.txt')
        values=[]
        if data_kind=='deformation':
            for x,y in product([-1.,0.,1.],repeat=2): values.append([x,y,0.,0.,0.,.01])
        else:
            for x,y,z in product([-1.,0.,1.],[-1.,0.,1.],[0.,10.,20.]):
                values.append([x,y,z,21. if data_kind=='temperature' else 1.5])
        source.write_text('\n'.join(' '.join(map(str,row)) for row in values)+'\n',encoding='utf-8')
        try:
            imported=await e.finish(await e.call('run_star_operation',{'request':{
                'kind':'import_'+data_kind,'surface':1,'path':str(source),
                'coordinate_system':'local','length_unit':'Millimeters'}}))
            assert imported['actual']['imported']
            assert imported['actual']['total']==len(values)
            request=dict(kind='fit_'+data_kind,surface=1,apply='enable')
            if data_kind=='deformation': request['deformation_option']='DeformationWithRBMs'
            fitted=await e.finish(await e.call('run_star_operation',{'request':request}))
            assert fitted['actual']['enabled']
            query=dict(surface=1,data_kind=data_kind,include_points=True,count=2,
                       sample_points=[dict(x=0,y=0,z=0)])
            result=await e.call('get_star_data',{'request':query})
            assert len(result['rows'])==2 and result['next_start']==2
            point=result['fit_evaluations'][0]
            if data_kind=='deformation': e.check('constant dz',point['dz'],.01,atol=1e-8,rtol=1e-6)
            elif data_kind=='temperature': e.check('constant temperature',point['temperature'],21.,atol=1e-6,rtol=1e-6)
            else: e.check('constant index',point['refractive_index'],1.5,atol=1e-8,rtol=1e-7)
        finally: source.unlink(missing_ok=True)
    asyncio.run(execute('star_'+data_kind,work))
