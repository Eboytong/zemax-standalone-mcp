"""Independent ray-equation references for the planned radial GRIN fixtures."""
import asyncio
import json
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.finite_reference import radial_grin_ray


@pytest.mark.zemax
@pytest.mark.parametrize('kind',['Gradient1','Gradient9'])
@pytest.mark.parametrize('wavelength',[.486,.55,.644])
def test_finite_radial_grin_native(kind,wavelength):
    async def work(e):
        await e.model();await e.call('insert_surfaces',dict(at=2,count=2))
        await e.call('update_system_settings',dict(settings=dict(wavelengths=[dict(wavelength_um=wavelength)])))
        n0,quadratic=1.5,-.083;material='';source=None
        if kind=='Gradient9':
            source=Path.home()/'Documents/Zemax/Glasscat/GRADIENT_9.DAT'
            lines=source.read_text(encoding='utf-8-sig').splitlines();index=lines.index('SLS-1.0')
            B,C,K0,K1,K2=map(float,lines[index+1:index+6])
            n0=B+C/wavelength**2
            quadratic=-n0*(K0+K1/wavelength**2+K2/wavelength**4)**2/2
            material='SLS-1.0'
        parameters={1:.005,**({2:n0,3:quadratic,4:0}if kind=='Gradient1'else{2:0,3:0})}
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=1,semi_diameter=1,replace_solves=True),
            dict(surface=2,surface_type=kind,radius='Infinity',thickness=4,material=material,parameters=parameters,semi_diameter=1,replace_solves=True),
            dict(surface=3,radius='Infinity',thickness=5,material='',semi_diameter=1,replace_solves=True)]))
        baseline=e.folder/'baseline.zos';await e.call('save_lens_as',dict(path=str(baseline)))
        points=[(0,0),(.05,0),(-.05,0),(.1,.05),(0,-.1)];records=[]
        for reload in (False,True):
            if reload:await e.call('open_lens',dict(path=str(baseline)))
            result=await e.finish(await e.call('run_batch_ray_trace',dict(request=dict(input_mode='Direct',start_surface=1,target_surface=3,
                rays=[dict(x=x,y=y,z=0,l=0,m=0,n=1)for x,y in points]))))
            for (x,y),row in zip(points,result['rows'],strict=True):
                assert row['error_code']==row['vignette_code']==0,row
                expected=radial_grin_ray(x,y,4,n0,quadratic,1024)
                coarse=radial_grin_ray(x,y,4,n0,quadratic,512)
                for a,b in zip(expected,coarse):
                    for v,w in zip(a,b):e.check('independent GRIN RK4 refinement',v,w,atol=1e-10,rtol=0)
                for i in range(3):
                    e.check('GRIN exit position mm',row['position'][i],expected[0][i])
                    e.check('GRIN exit direction',row['direction'][i],expected[1][i])
                records.append(dict(reloaded=reload,input=[x,y],expected=expected,actual=row))
        (e.folder/'grin-reference.json').write_text(json.dumps(dict(surface_type=kind,wavelength_um=wavelength,
            n0=n0,radial_quadratic=quadratic,source=str(source)if source else'2.3.1.2.34 manual Gradient1',
            formula='Hamiltonian ray equations for n=n0+a*(x*x+y*y), tangential optical momentum continuous at planar exit',records=records),indent=2),encoding='utf-8')
    asyncio.run(execute(f'finite_grin_{kind}_{wavelength}',work))
