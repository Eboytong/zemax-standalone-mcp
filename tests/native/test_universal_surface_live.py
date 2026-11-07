"""Native conic/numbered parameters and non-square coordinate-break grid."""
import asyncio
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_universal_conic_and_surface_parameters():
    async def work(e):
        await e.model()
        for kind in ['EvenAspheric','CoordinateBreak']:
            await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type=kind,thickness=2,replace_solves=True)]))
            saved=str(e.folder/(kind+'.zos'));await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
            before=await e.call('get_surfaces');settings=await e.call('get_system_settings')
            scans=[('SurfaceParameter',1,'PMVA','Millimeters'if kind=='CoordinateBreak'else None),('SurfaceParameter',3 if kind=='CoordinateBreak'else 2,'PMVA','degrees'if kind=='CoordinateBreak'else None)]
            if kind=='EvenAspheric':scans[0:0]=[('Conic',None,'COVA','dimensionless'),('TCE',None,'TCVA','ppm/Celsius')]
            for parameter,number,operand,unit in scans:
                q=dict(kind='universal_plot_1d',surface=1,parameter=parameter,start=.001,stop=.003,samples=3,
                    target=dict(mode='operand',operand=operand,parameters=[1]+([number]if number is not None else[])))
                if number is not None:q['parameter_number']=number
                r=await e.finish(await e.call('run_analysis',dict(request=q)));curve=r['series'][0]
                assert curve['x_unit']==curve['y_unit']==unit
                for x,y in zip(curve['x'],curve['y']):e.check('Surface property value '+kind+' '+parameter+' '+str(number),y[0],x)
            q=dict(kind='universal_plot_2d',x=dict(surface=1,parameter='SurfaceParameter',parameter_number=1,start=.001,stop=.005,samples=5),
                y=dict(surface=1,parameter='SurfaceParameter',parameter_number=3 if kind=='CoordinateBreak'else 2,start=.002,stop=.004,samples=3),target=dict(mode='operand',operand='PMVA',parameters=[1,1]))
            r=await e.finish(await e.call('run_analysis',dict(request=q)));g=r['grids'][0]
            assert(g['nx'],g['ny'])==(5,3)
            for row in g['values']:
                for x,v in zip(g['x'],row):e.check('Surface parameter grid '+kind,v,x)
            task=r['task']['task_id'];state=await e.call('get_task_status',dict(task_id=task))
            assert state['close_attempted']and not state.get('cleanup_warnings')
            await e.call('get_task_result',dict(task_id=task,grid=0,x_start=1,y_start=1,width=2,height=2))
            await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/(kind+'.png')))))
            assert await e.call('get_surfaces')==before and await e.call('get_system_settings')==settings
    asyncio.run(execute('universal247_surface',work))
