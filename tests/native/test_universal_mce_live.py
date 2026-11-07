"""General numeric MCE rows, native parameter identity and mixed-axis references."""
import asyncio,math
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_universal_numeric_mce_axes():
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=1))
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=1,y=2)],wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.65)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='CoordinateBreak',thickness=2,replace_solves=True),dict(surface=2,surface_type='EvenAspheric',thickness=4,replace_solves=True)]))
        specs=[('THIC',{'1':1},2),('TEMP',{},20),('PRES',{},1),('WAVE',{'1':0},.55),('PRAM',{'1':1,'2':1},.1),('CONN',{'1':2},0),('XFIE',{'1':1},1),('YFIE',{'1':1},2),('TCEX',{'1':2},0)]
        await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)],
            operands=[dict(type=kind,parameters=params,cells=[dict(configuration=c,value=value)for c in [1,2]])for kind,params,value in specs])))
        rows=(await e.call('get_configurations',dict(request={})))['rows'][-len(specs):]
        numbers={kind:r['operand']for(kind,_,_),r in zip(specs,rows)}
        await e.call('set_configuration',dict(configuration=2))
        rejected=await e.call('update_merit_function',dict(mode='replace',operands=[dict(type='TTHI',parameters={'2':1,'3':1})]),okay=False)
        assert rejected['error']['code']=='INVALID_ARGUMENT'
        merit=await e.call('update_merit_function',dict(mode='replace',operands=[dict(type='CONF',parameters={'2':2}),dict(type='TTHI',parameters={'2':1,'3':1},target=0,weight=1),dict(type='PMVA',parameters={'2':1,'3':1},target=0,weight=1)]))
        assert [row['type']for row in merit['operands']]==['CONF','TTHI','PMVA']
        assert merit['operands'][0]['parameters']['2']['value']==2
        saved=str(e.folder/'baseline.zos');await e.call('save_lens_as',dict(path=saved));await e.call('open_lens',dict(path=saved))
        before=[await e.call(name)for name in ['get_surfaces','get_system_settings']];configs=await e.call('get_configurations',dict(request={}))
        for operand,params in [('REAY',[1,99,0,0,0,.5]),('MTFS',[2,1,99,30,0,0]),('TTHI',[999,999])]:
            q=dict(kind='universal_plot_1d',surface=1,start=2,stop=4,samples=3,target=dict(mode='operand',operand=operand,parameters=params))
            rejected=await e.call('run_analysis',dict(request=q),okay=False)
            assert rejected['error']['code']=='INDEX_OUT_OF_RANGE'
        q=dict(kind='universal_plot_2d',x=dict(category='System',parameter='Temperature',start=10,stop=30,samples=5),
            y=dict(category='Configuration',parameter='ConfigurationValue',mce_operand='TEMP',configuration=2,operand_row=numbers['TEMP'],start=10,stop=30,samples=3),target=dict(mode='merit'))
        rejected=await e.call('run_analysis',dict(request=q),okay=False)
        assert rejected['error']['code']=='INVALID_ARGUMENT'
        for kind,low,high,unit,operand,params in [
            ('THIC',2,4,'Millimeters','TTHI',[1,1]),('TEMP',10,30,'Celsius','TTHI',[1,1]),
            ('PRES',.8,1.2,'atmospheres','TTHI',[1,1]),('WAVE',.45,.65,'micrometers','TTHI',[1,1]),
            ('PRAM',.1,.3,'Millimeters','PMVA',[1,1]),('CONN',-1,1,'dimensionless','COVA',[2]),
            ('XFIE',-1,1,'degrees','TTHI',[1,1]),('YFIE',-2,2,'degrees','TTHI',[1,1]),('TCEX',10,30,'ppm/Celsius','TCVA',[2])]:
            q=dict(kind='universal_plot_1d',category='Configuration',parameter='ConfigurationValue',mce_operand=kind,configuration=2,operand_row=numbers[kind],start=low,stop=high,samples=3,
                target=dict(mode='operand',operand=operand,parameters=params))
            result=await e.finish(await e.call('run_analysis',dict(request=q)));curve=result['series'][0]
            assert curve['x_unit']==unit
            for x,y in zip(curve['x'],curve['y']):e.check('Numeric MCE '+kind,y[0],x if kind in {'THIC','PRAM','CONN','TCEX'}else 2)
        q=dict(kind='universal_plot_2d',x=dict(category='Configuration',parameter='ConfigurationValue',mce_operand='THIC',configuration=2,operand_row=numbers['THIC'],start=2,stop=6,samples=5),
            y=dict(category='Configuration',parameter='ConfigurationValue',mce_operand='PRAM',configuration=2,operand_row=numbers['PRAM'],start=.1,stop=.3,samples=3),target=dict(mode='merit'))
        result=await e.finish(await e.call('run_analysis',dict(request=q)));grid=result['grids'][0]
        assert(grid['nx'],grid['ny'])==(5,3)
        for y,row in zip(grid['y'],grid['values']):
            for x,value in zip(grid['x'],row):e.check('Numeric MCE two-axis merit',value,math.sqrt((x*x+y*y)/2))
        task=result['task']['task_id'];state=await e.call('get_task_status',dict(task_id=task))
        assert state['close_attempted']and not state.get('cleanup_warnings')
        assert state['settings']['target']['merit_configurations']==[dict(line=1,configuration=2)]
        await e.call('get_task_result',dict(task_id=task,grid=0,x_start=1,y_start=1,width=2,height=2))
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'mce.png'))))
        assert [await e.call(name)for name in ['get_surfaces','get_system_settings']]==before
        assert await e.call('get_configurations',dict(request={}))==configs
    asyncio.run(execute('universal253_mce',work))
