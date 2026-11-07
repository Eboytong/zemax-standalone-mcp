"""Finite Fourier solution of Ince's equation, independent of the installed DLL."""
import math


def coefficients(p,m,odd,epsilon):
    import numpy as np
    if p<0 or m<0 or m>p or (p-m)%2 or (odd and m==0):
        raise ValueError('Illegal finite Ince parity/order')
    modes=list(range(-p,p+1,2));orders=list(range(1 if p%2 else(2 if odd else 0),p+1,2))
    matrix=np.zeros((p+1,p+1),complex)
    for j,k in enumerate(modes):
        matrix[j,j]=k*k
        if k+2 in modes:matrix[modes.index(k+2),j]=(p-k)*epsilon/2
        if k-2 in modes:matrix[modes.index(k-2),j]=(p+k)*epsilon/2
    basis=np.zeros((p+1,len(orders)),complex)
    for j,k in enumerate(orders):
        if not k:basis[modes.index(0),j]=1
        elif odd:
            basis[modes.index(k),j]=-0.5j;basis[modes.index(-k),j]=0.5j
        else:basis[modes.index(k),j]=basis[modes.index(-k),j]=.5
    reduced=np.linalg.lstsq(basis,matrix@basis,rcond=None)[0]
    eigenvalues,vectors=np.linalg.eig(reduced)
    if np.max(abs(eigenvalues.imag))>1e-10:raise ValueError('Non-real Ince eigenvalue')
    which=np.argsort(eigenvalues.real)[orders.index(m)]
    v=vectors[:,which];v=v/v[np.argmax(abs(v))]
    if np.max(abs(v.imag))>1e-10:raise ValueError('Non-real Ince eigenvector')
    return orders,v.real,float(eigenvalues[which].real)


def field(x,y,p,m,odd,w0,f0,z=0,wavelength=.00055):
    import numpy as np
    zR=math.pi*w0*w0/wavelength;scale=math.sqrt(1+(z/zR)**2)
    epsilon=2*(f0/w0)**2;orders,c,eigenvalue=coefficients(p,m,odd,epsilon)
    coordinate=np.arccosh((np.asarray(x,dtype=complex)+1j*np.asarray(y))/(f0*scale))
    xi,eta=coordinate.real,coordinate.imag
    if odd:
        radial=sum(a*np.sinh(k*xi)for a,k in zip(c,orders))
        angular=sum(a*np.sin(k*eta)for a,k in zip(c,orders))
        value=1j*radial*angular
    else:
        radial=sum(a*np.cosh(k*xi)for a,k in zip(c,orders))
        angular=sum(a*np.cos(k*eta)for a,k in zip(c,orders))
        value=radial*angular
    r2=np.asarray(x)**2+np.asarray(y)**2
    value=value*np.exp(-r2/(w0*scale)**2)/scale
    if z:
        curvature=z*(1+(zR/z)**2)
        value=value*np.exp(-1j*math.pi*r2/(wavelength*curvature)+1j*(p+1)*math.atan(z/zR))
    return value
