"""Explicit first fifteen orthonormal Standard Zernike polynomial columns."""
import numpy as np


def standard15(x,y):
    x,y=np.broadcast_arrays(np.asarray(x),np.asarray(y))
    r2=x*x+y*y
    return np.stack([
        np.ones_like(x),2*x,2*y,np.sqrt(3)*(2*r2-1),
        np.sqrt(6)*2*x*y,np.sqrt(6)*(x*x-y*y),
        np.sqrt(8)*(3*r2-2)*y,np.sqrt(8)*(3*r2-2)*x,
        np.sqrt(8)*(3*x*x*y-y**3),np.sqrt(8)*(x**3-3*x*y*y),
        np.sqrt(5)*(6*r2*r2-6*r2+1),
        np.sqrt(10)*(4*r2-3)*(x*x-y*y),np.sqrt(10)*(4*r2-3)*2*x*y,
        np.sqrt(10)*(x**4-6*x*x*y*y+y**4),np.sqrt(10)*(4*x**3*y-4*x*y**3),
    ],axis=-1)


def pupil_points(size):
    axis=(np.arange(size)+.5)*2/size-1
    x,y=np.meshgrid(axis,axis)
    mask=x*x+y*y<1
    return x[mask],y[mask]


def fit_standard15(x,y,opd):
    return np.linalg.lstsq(standard15(x,y),np.asarray(opd),rcond=None)[0]
