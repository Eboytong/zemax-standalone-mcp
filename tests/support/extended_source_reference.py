"""Analytic area fractions for a uniform square image."""
import numpy as np


def airy_energy(radius,wavelength_um,f_number):
    nodes,weights=np.polynomial.legendre.leggauss(128)
    theta=(nodes+1)*np.pi/2
    z=np.asarray(radius)*np.pi/(wavelength_um*f_number)
    j0=np.cos(z[:,None]*np.sin(theta))@weights/2
    j1=np.cos(theta-z[:,None]*np.sin(theta))@weights/2
    return 1-j0*j0-j1*j1


def square_energy(radius,kind,half_width=10):
    r=np.asarray(radius,dtype=float)
    if kind in {'X_Only','Y_Only'}:
        return np.clip(r/half_width,0,1)
    if kind=='Ensquared':
        return np.clip(r/half_width,0,1)**2
    if kind!='Encircled':
        raise ValueError(kind)
    r=np.maximum(r,0)
    result=np.minimum(np.pi*r*r/(4*half_width**2),1)
    middle=(r>half_width)&(r<half_width*np.sqrt(2))
    t=r[middle]
    result[middle]=(np.pi*t*t-4*(t*t*np.arccos(half_width/t)-half_width*np.sqrt(t*t-half_width**2)))/(4*half_width**2)
    result[r>=half_width*np.sqrt(2)]=1
    return result
