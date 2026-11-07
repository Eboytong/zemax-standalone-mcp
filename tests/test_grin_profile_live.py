"""Native GRIN profiles against the independent Gradient1 polynomial."""
import asyncio
import math
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize('axis',['X','Y','Z'])
def test_grin_profile_polynomial_native(axis):
    async def work(e):
        await e.model()
        await e.call('insert_surfaces',dict(at=2,count=1))
        await e.call('update_surfaces',dict(changes=[
            dict(surface=0,thickness=10),
            dict(surface=1,surface_type='Gradient1',radius='Infinity',thickness=4,
                parameters={1:.005,2:1.5,3:-.02,4:.001},semi_diameter=1,replace_solves=True),
            dict(surface=2,radius='Infinity',thickness=5,semi_diameter=1,replace_solves=True)]))
        path=e.folder/'gradient1.zos'
        await e.call('save_lens_as',dict(path=str(path)))
        request=dict(kind='grin_profile',surface=1,wavelength=1,show_index_vs=axis,
            **{'minimum_'+axis.lower():0 if axis=='Z' else -.8,'maximum_'+axis.lower():4 if axis=='Z' else .8},
            **{key+'_value':value for key,value in [('x',.2),('y',.3),('z',1)] if key.upper()!=axis})
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=str(path)))
            baseline=await e.call('get_system_settings')
            surfaces=await e.call('get_surfaces',dict(start=0,count=5))
            cells=surfaces['surfaces'][1]['cells']
            assert cells['parameter_3']['header']=='Nr2' and cells['parameter_4']['header']=='Nr1'
            result=await e.finish(await e.call('run_analysis',dict(request=request)))
            assert result['series'],result
            curve=result['series'][0]
            assert curve['x_unit']=='Millimeters' and curve['y_unit']=='dimensionless'
            assert len(curve['x'])>=5
            for coordinate,values in zip(curve['x'],curve['y'],strict=True):
                x,y=(coordinate,.3)if axis=='X'else(.2,coordinate)if axis=='Y'else(.2,.3)
                r2=x*x+y*y
                expected=1.5-.02*r2+.001*math.sqrt(r2)
                assert len(values)==1,values
                e.check(f'Gradient1 {axis} index at {coordinate} reload={reload}',values[0],expected,atol=1e-8,rtol=1e-7)
            assert await e.call('get_system_settings')==baseline
            assert await e.call('get_surfaces',dict(start=0,count=5))==surfaces
            task=result['task']['task_id']
            page=await e.call('get_task_result',dict(task_id=task,series=0,start=1,count=3))
            assert page
            await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/f'{axis}_{reload}.png'))))
    asyncio.run(execute('grin_profile054_'+axis,work))
