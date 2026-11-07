"""The fixed eight noncircular/nonzero-aberration diffraction models."""
import asyncio
import json
import math
import pytest
from tests.support.native import execute
from zemax_mcp.evaluation import interpolate


def polynomial(kind,x,y):
    r2=x*x+y*y
    if kind=='spherical':return r2*r2,4*x*r2,4*y*r2,8*x*y
    if kind=='coma':return x*r2,3*x*x+y*y,2*x*y,2*y
    if kind=='astigmatism':return x*x-y*y,2*x,-2*y,0*x*y
    return r2,2*x,2*y,0*x*y


@pytest.mark.zemax
@pytest.mark.parametrize('shape',['rectangle','annulus'])
@pytest.mark.parametrize('kind',['spherical','coma','astigmatism','defocus'])
def test_finite_noncircular_phase_native(shape,kind):
    async def work(e):
        import numpy as np
        await e.model();lines=['65 65 0.25 0.25 0']
        for iy in range(65):
            for ix in range(65):
                phase,px,py,pxy=polynomial(kind,(ix-32)*.25/5,(32-iy)*.25/5)
                lines.append(' '.join(map(str,(2*math.pi*.2*phase,2*math.pi*.2*px/5,2*math.pi*.2*py/5,2*math.pi*.2*pxy/25))))
        file=e.folder/'phase.dat';file.write_text('\n'.join(lines),encoding='ascii')
        aperture=dict(type='RectangularAperture',x_half_width=4,y_half_width=3)if shape=='rectangle'else dict(type='CircularObscuration',maximum_radius=1.5)
        await e.call('update_surfaces',dict(changes=[dict(surface=1,surface_type='GridPhase',import_file=str(file),aperture=aperture,replace_solves=True),
            dict(surface=2,radius=-200,conic=-1,material='MIRROR',thickness=-100,semi_diameter=5,is_stop=True,replace_solves=True)]))
        await e.call('save_lens_as',dict(path=str(e.folder/'baseline.zos')))
        def mask(x,y):
            return ((abs(x)<=.8)&(abs(y)<=.6))if shape=='rectangle'else((x*x+y*y<=1)&(x*x+y*y>=.09))
        mtf=await e.finish(await e.call('run_analysis',dict(request=dict(kind='huygens_mtf',field=1,wavelength=1,
            sampling='S_256x256',image_sampling='S_512x512',maximum_frequency=50))))
        records=[]
        for series in mtf['series']:
            for column,label in enumerate(series['labels']):
                assert label in ('Tangential','Sagittal','子午','弧矢')
                for f in (10,25,50):
                    refs=[]
                    for n in (512,1024):
                        u=(np.arange(n)+.5)*2/n-1;x=u[None,:];y=u[:,None]
                        shift=f*.00055*100/5
                        sx,sy=(0,shift)if label in ('Tangential','子午')else(shift,0)
                        a=mask(x,y);b=mask(x-sx,y-sy)
                        phase=2*np.pi*.2*(polynomial(kind,x,y)[0]-polynomial(kind,x-sx,y-sy)[0])
                        refs.append(float(abs(np.exp(1j*phase)[a&b].sum())/a.sum()))
                    e.check('noncircular complex pupil MTF quadrature refinement',refs[0],refs[1],atol=.005,rtol=0)
                    actual=interpolate(series['x'],[v[column]for v in series['y']],f)
                    records.append(dict(label=label,frequency=f,expected=refs[1],actual=actual))
                    e.check('noncircular complex pupil MTF',actual,refs[1],atol=.02,rtol=0)
        psf=await e.finish(await e.call('run_analysis',dict(request=dict(kind='huygens_psf',field=1,wavelength=1,
            sampling='S_256x256',image_sampling='S_256x256',image_delta=.5,normalize=True))))
        g=psf['grids'][0];actual=np.asarray(g['values'],dtype=float)
        xs=(g['min_x']+np.arange(g['nx'])*g['dx'])/1000;ys=(g['min_y']+np.arange(g['ny'])*g['dy'])/1000
        refs=[];energies=[]
        for n in (256,512,1024):
            axis=(np.arange(n)+.5)*10/n-5;x=axis[None,:]/5;y=axis[:,None]/5;a=mask(x,y)
            pupil=np.where(a,np.exp(2j*np.pi*.2*polynomial(kind,x,y)[0]),0)
            kx=np.exp(-2j*np.pi*xs[:,None]*axis[None,:]/(.00055*100))
            ky=np.exp(-2j*np.pi*ys[:,None]*axis[None,:]/(.00055*100))
            intensity=abs(ky@pupil@kx.T)**2*(10/n)**4
            refs.append(intensity/intensity.max())
            total=(.00055*100)**2*a.sum()*(10/n)**2
            energies.append({r:float(intensity[xs[None,:]**2+ys[:,None]**2<=(r/1000)**2].sum()*g['dx']*g['dy']/1e6/total)for r in (10,20)})
        e.check('noncircular PSF reference refinement',float(np.max(abs(refs[-2]-refs[-1]))),0,atol=.005,rtol=0)
        e.check('noncircular signed PSF image',float(np.max(abs(actual-refs[-1]))),0,atol=.025,rtol=0)
        energy=await e.finish(await e.call('run_analysis',dict(request=dict(kind='diffraction_encircled_energy',field=1,wavelength=1,
            sampling='S_256x256',reference='ChiefRay',maximum_radius=30))))
        for series in energy['series']:
            if series['description'].strip().casefold()in('衍射极限','diffraction limit'):continue
            for r in (10,20):
                e.check('noncircular EE reference refinement',energies[-2][r],energies[-1][r],atol=.005,rtol=0)
                value=interpolate(series['x'],[v[0]for v in series['y']],r)
                e.check('noncircular Parseval encircled energy',value,energies[-1][r],atol=.025,rtol=0)
        (e.folder/'noncircular-phase-reference.json').write_text(json.dumps(dict(shape=shape,aberration=kind,
            waves=.2,mtf=records,energy_reference=energies,energy_normalization='Parseval full-plane energy, not finite image sum'),indent=2),encoding='utf-8')
    asyncio.run(execute(f'finite_noncircular_{shape}_{kind}',work))
