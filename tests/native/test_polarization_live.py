"""Native CFG adoption, pupil fields and independent batch-pol reference."""
import asyncio
import cmath
import math
from pathlib import Path
import pytest
from tests.support.native import execute

@pytest.mark.zemax
@pytest.mark.parametrize('sampling,jx,jy,phase,field,wave',[(3,1,0,0,1,1),(5,0,1,0,1,1),(7,1,1,90,2,2),(9,1,1,45,3,1),(7,1,1,450,4,2),(101,1,0,0,4,2)])
def test_polarization_pupil_map_native(sampling,jx,jy,phase,field,wave):
    async def work(e):
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(fields=[dict(x=0,y=0),dict(x=0,y=5),dict(x=3,y=4),dict(x=0,y=-5)],wavelengths=[dict(wavelength_um=.55),dict(wavelength_um=.65)])))
        await e.call('update_surfaces',dict(changes=[dict(surface=0,thickness=10),dict(surface=1,radius='Infinity',thickness=1,material='N-BK7',semi_diameter=5,replace_solves=True)]))
        if field==4:
            await e.call('update_configurations',dict(request=dict(actions=[dict(action='add',copy_current=True)])))
            await e.call('set_configuration',dict(configuration=2))
        before=await e.call('get_system_settings');surfaces=await e.call('get_surfaces',dict(start=0,count=3))
        q=dict(kind='polarization_pupil_map',surface=1,field=field,wavelength=wave,sampling=sampling,jx=jx,jy=jy,y_phase=phase)
        result=await e.finish(await e.call('run_analysis',dict(request=q)))
        actual=result['actual_settings'];assert actual['sampling']==sampling and actual['surface']==1
        half=(sampling-1)//2
        expected={(round(x/half,3),round(y/half,3))for x in range(-half,half+1)for y in range(-half,half+1)if x*x+y*y<=half*half}
        assert {(r['px'],r['py'])for r in result['rows']}==expected
        rays=[dict(px=round(r['px']*half)/half,py=round(r['py']*half)/half,hx=.6 if field==3 else 0,hy={1:0,2:1,3:.8,4:-1}[field],wavelength=wave)for r in result['rows']]
        traced=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(target_surface=1,rays=rays,polarization=dict(jx=jx,jy=jy,y_phase=phase)))))
        assert len(traced['rows'])==len(result['rows'])
        for row,ray in zip(result['rows'],traced['rows']):
            assert ray['error_code']==0
            electric=ray['electric_field'];ex=complex(electric['ex_real'],electric['ex_imag']);ey=complex(electric['ey_real'],electric['ey_imag'])
            for label,actual,reference in [('Ex',row['ex'],abs(ex)),('Ey',row['ey'],abs(ey)),('intensity XY',row['intensity'],abs(ex)**2+abs(ey)**2)]:
                e.check(label+' at '+str((row['px'],row['py'])),actual,reference,atol=1e-8,rtol=1e-7)
            if abs(ex)>1e-8 and abs(ey)>1e-8:
                relative=math.degrees(cmath.phase(ex)-cmath.phase(ey))
                difference=(row['relative_phase_deg']-relative+180)%360-180
                e.check('relative phase degrees',difference,0,atol=1e-6,rtol=0)
        if field==1:
            agf=(Path.home()/'Documents/Zemax/Glasscat/SCHOTT.AGF').read_text(encoding='utf-8-sig').splitlines()
            start=next(i for i,line in enumerate(agf)if line.split()[:2]==['NM','N-BK7'])
            coefficients=next([float(v)for v in line.split()[1:7]]for line in agf[start+1:]if line.startswith('CD '))
            squared=.55**2
            index=math.sqrt(1+sum(coefficients[i]*squared/(squared-coefficients[i+1])for i in [0,2,4]))
            center=next(r for r in result['rows']if r['px']==r['py']==0)
            e.check('normal-incidence center versus independent Sellmeier/Fresnel',center['intensity'],1-((1-index)/(1+index))**2,atol=1e-8,rtol=1e-7)
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces',dict(start=0,count=3))==surfaces
        if sampling==101:
            return
        task=result['task']['task_id']
        page=await e.call('get_task_result',dict(task_id=task,start=1,count=2));assert page['rows']==result['rows'][1:3]
        await e.call('export_analysis_image',dict(request=dict(task_id=task,path=str(e.folder/'pupil.png'))))
        if field==4 and sampling<101:
            report=await e.call('export_evaluation_report',dict(task_ids=[task],title='Polarization pupil acceptance',include_charts=True,formats=['markdown']))
            assert any(a['kind']=='plot'and Path(a['path']).is_file()for a in report['artifacts'])
        assert await e.call('get_system_settings')==before
        assert await e.call('get_surfaces',dict(start=0,count=3))==surfaces
    asyncio.run(execute('polarization_pupil054_'+str(sampling),work))
