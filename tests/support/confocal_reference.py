"""Independent Fresnel pupil quadrature; no native or production metric calls."""
import math

import numpy as np


def pupil_image(grid,z,branch,wavelength_um=.55,quadrature=192,focal_length=50.,radius=1.):
    u=((np.arange(quadrature)+.5)*2/quadrature-1)*radius
    xx=u[None,:];yy=u[:,None];mask=xx*xx+yy*yy<=radius**2
    x=(grid['min_x']+np.arange(grid['nx'])*grid['dx'])/1000
    y=(grid['min_y']+np.arange(grid['ny'])*grid['dy'])/1000
    wave=wavelength_um/1000
    v=focal_length+z if branch==0 else 2*focal_length
    s=math.inf if branch==0 else 2*focal_length-z
    phase=math.pi/wave*(1/v+(0 if math.isinf(s) else 1/s)-1/focal_length)*(xx*xx+yy*yy)
    pupil=np.where(mask,np.exp(1j*phase),0)
    kx=np.exp(-2j*math.pi*x[:,None]*u[None,:]/(wave*v))
    ky=np.exp(-2j*math.pi*y[:,None]*u[None,:]/(wave*v))
    return np.abs(ky@pupil@kx.T)**2


def metrics(grid,intensity,diameters):
    dx,dy=grid['dx'],grid['dy'];total=float(intensity.sum()*dx*dy)
    x=grid['min_x']+np.arange(grid['nx'])*dx;y=grid['min_y']+np.arange(grid['ny'])*dy
    cx=int(round(-grid['min_x']/dx));cy=int(round(-grid['min_y']/dy))
    result=dict(axis=float(intensity[cy,cx])/total,fractions=[])
    for diameter in diameters:
        weights=np.zeros_like(intensity)
        # Independent midpoint area quadrature of the circular pinhole.
        for sy in range(8):
            for sx in range(8):
                px=x+(sx+.5)/8*dx-dx/2;py=y+(sy+.5)/8*dy-dy/2
                weights+=(py[:,None]**2+px[None,:]**2<=(diameter/2)**2)/64
        result['fractions'].append(float((intensity*weights).sum()*dx*dy)/total)
    return result


def response(result,diameters,quadrature=192,wavelengths=(.55,.55)):
    components=[]
    for case in result['cases']:
        pair=[]
        for j,branch in enumerate(case['paths']):
            grid=result['grids'][branch['grid']]
            intensity=pupil_image(grid,case['offset_mm'],j,wavelengths[j],quadrature)
            pair.append(metrics(grid,intensity,diameters if j else []))
        z=case['offset_mm'];s=100-z
        collection=(1-s/math.sqrt(s*s+1))/2
        components.append([pair[0]['axis']*fraction*collection for fraction in pair[1]['fractions']])
    zero=next(i for i,c in enumerate(result['cases']) if c['offset_mm']==0)
    return [[row[j]/components[zero][j] for row in components] for j in range(len(diameters))]


def fwhm(x,y):
    peak=max(y);center=y.index(peak);crossings=[]
    for indices in [range(center-1,-1,-1),range(center,len(x)-1)]:
        for i in indices:
            if (y[i]-peak/2)*(y[i+1]-peak/2)<=0:
                crossings.append(x[i]+(x[i+1]-x[i])*(peak/2-y[i])/(y[i+1]-y[i]));break
    return crossings[-1]-crossings[0] if len(crossings)==2 else None
