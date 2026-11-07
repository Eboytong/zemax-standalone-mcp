import asyncio
from pathlib import Path
import pytest
from tests.support.native import execute
from zemax_mcp.evaluation import interpolate

@pytest.mark.zemax
def test_mtf_extensions_stdio():
    async def work(e):
        await e.call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        for family in ('geometric','huygens'):
            curve=await e.finish(await e.call('run_analysis',dict(request=dict(kind=family+'_mtf_vs_field',frequencies=[50,10,30],sampling='S_256x256',field_density=3))))
            request=dict(kind=family+'_mtf',sampling='S_256x256')
            if family=='huygens':request['image_sampling']='S_256x256'
            single=await e.finish(await e.call('run_analysis',dict(request=request)))
            for s in curve['series']:
                for j in range(2):
                    expected=interpolate(single['series'][0]['x'],[r[j] for r in single['series'][0]['y']],s['frequency'])
                    e.check(family+' on axis',s['y'][0][j],expected,atol=.005)
        for family in ('fft','geometric'):
            outputs={}
            for data_type in ('Average','Tangential','Sagittal'):
                request=dict(kind=family+'_mtf_map',x_field_width=6,y_field_width=4,x_pixels=7,y_pixels=5,reference_field=2,data_type=data_type,sampling='S_256x256')
                r=await e.finish(await e.call('run_analysis',dict(request=request)))
                g=r['grids'][0];assert len(g['values'])==5 and len(g['values'][0])==7
                outputs[data_type]=g['values']
                page=await e.call('get_task_result',dict(task_id=r['task']['task_id'],grid=0,x_start=2,y_start=1,width=3,height=2))
                assert page['grid']['values']==[row[2:5] for row in g['values'][1:3]]
                await e.call('export_analysis_image',dict(request=dict(task_id=r['task']['task_id'],path=str(e.folder/(family+data_type+'.png')))))
            for iy,ix in ((2,3),(0,0)):
                field_x=g['min_x']+ix*g['dx'];field_y=g['min_y']+iy*g['dy']
                await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=0,y=14),dict(x=0,y=20),dict(x=field_x,y=field_y)])))
                if family=='fft':
                    single=await e.finish(await e.call('run_fft_mtf',dict(field=4,wavelength=1,sampling='S_256x256')))
                else:
                    single=await e.finish(await e.call('run_analysis',dict(request=dict(kind='geometric_mtf',field=4,sampling='S_256x256',multiply_by_diffraction_limit=True))))
                expected=sum(interpolate(single['series'][0]['x'],[row[c] for row in single['series'][0]['y']],50) for c in (0,1))/2
                e.check('map physical point',outputs['Average'][iy][ix],expected,atol=.005)
            for y in range(5):
                for x in range(7):e.check('map mean',outputs['Average'][y][x],(outputs['Tangential'][y][x]+outputs['Sagittal'][y][x])/2,atol=1e-7)
        extra=await e.finish(await e.call('run_analysis',dict(request=dict(kind='geometric_mtf_map',x_field_width=1,y_field_width=2,x_pixels=3,y_pixels=3,wavelength=0,reference_field=0,use_polarization=True,remove_vignetting_factors=False))))
        assert extra['task']['settings']['native']['Wavelength']==0
        assert extra['task']['settings']['native']['UsePolarization'] is True
    asyncio.run(execute('mtf_extensions',work))
