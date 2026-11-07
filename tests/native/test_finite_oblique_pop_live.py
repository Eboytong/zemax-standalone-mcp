"""Actual tilted end planes; preserve AlongBeam/public projection boundaries."""
import asyncio
import json
import math
import pytest
from tests.support.native import execute
from tests.support.numeric_reference import write_polarized_zbf


@pytest.mark.zemax
@pytest.mark.parametrize('axis',['X','Y'])
@pytest.mark.parametrize('tilt',[0,-5,5,-15,15])
def test_finite_oblique_endplane_boundary_native(axis,tilt):
    async def work(e):
        import numpy as np
        await e.model()
        await e.call('update_system_settings',dict(settings=dict(global_reference_surface=1,polarization=dict(unpolarized=False,jx=1,jy=0))))
        await e.call('update_surfaces',dict(changes=[dict(surface=1,thickness=2,replace_solves=True),
            dict(surface=2,surface_type='CoordinateBreak',thickness=0,parameters={3 if axis=='X'else 4:tilt},replace_solves=True)]))
        transform=(await e.call('get_surface_geometry',dict(request=dict(surface=3))))['global_transform']
        a=math.radians(tilt);c,s=math.cos(a),math.sin(a)
        rotation=([[1,0,0],[0,c,-s],[0,s,c]]if axis=='X'else[[c,0,s],[0,1,0],[-s,0,c]])
        for i in range(3):
            for j in range(3):e.check('physical endplane rotation',transform['rotation'][i][j],rotation[i][j])
            e.check('physical endplane translation mm',transform['translation'][i],(0,0,2)[i])
        n=128;step=.00625;u=(np.arange(n)-n/2)*step;x=u[None,:];y=u[:,None]
        base=np.exp(-(x/.1)**2-(y/.1)**2)*np.exp(1j*12*(x*x+y*y));records=[]
        for polarization in ('linear','elliptical','spatial'):
            if polarization=='linear':ex,ey=base,np.zeros_like(base)
            elif polarization=='elliptical':ex,ey=base,1j*.5*base
            else:
                angle=.4+2*x;ex=base*np.cos(angle);ey=1j*base*np.sin(angle)
            source=e.folder/(polarization+'.zbf');write_polarized_zbf(source,n,n,step,step,ex.ravel(),ey.ravel())
            for offset in (0,.025):
                receiver=np.exp(-((x-offset)/.1)**2-(y/.1)**2)
                file=e.folder/f'receiver_{offset}.zbf';write_polarized_zbf(file,n,n,step,step,receiver.ravel(),(1j*.5*receiver).ravel())
                result=await e.finish(await e.call('run_pop',dict(request=dict(beam_type='File',beam_file=str(source),beam_parameters={},
                    fiber_type='File',fiber_file=str(file),fiber_parameters={},fiber_position='SurfaceVertex',
                    use_polarization=True,ignore_fiber_polarization=False,x_sampling='S_128x128',y_sampling='S_128x128',x_width=.8,y_width=.8))))
                assert result['task']['settings']['Project']=='AlongBeam'
                e.check('empty-space output power W',result['metrics']['integrated_power'],1,atol=.005)
                records.append(dict(polarization=polarization,receiver_offset_mm=offset,metrics=result['metrics'],
                    projection=result['task']['settings']['Project'],propagation_frame=result['propagation_frame'],
                    actual_settings=result['task']['settings']))
        await e.call('save_lens_as',dict(path=str(e.folder/'model.zos')))
        (e.folder/'oblique-boundary.json').write_text(json.dumps(dict(axis=axis,tilt_deg=tilt,physical_transform=transform,
            status='deferred_physical_projection',verified_scope='native transformed planes, three Jones fixtures, receiver placement and AlongBeam power',
            reason='existing request fixes Project=AlongBeam; saved grid is perpendicular to chief ray, not a physical end-surface irradiance map',
            required_reference='physical-plane vector/projection comparison remains unverified; no new public projection field added',
            manual_lines=[20239,20752,21138,21144,21356,21358],rows=records),indent=2),encoding='utf-8')
    asyncio.run(execute(f'finite_oblique_{axis}_{tilt}',work))
