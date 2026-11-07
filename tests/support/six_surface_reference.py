"""Independent 2024 R2 surface equations; no native API calls."""
import math
from .finite_reference import unit
from .surface_reference import conic_sag


def conjugate_value(x, y, z, p):
    a, b = tuple(p[i] for i in (1, 2, 3)), tuple(p[i] for i in (4, 5, 6))
    sign = 1 if a[2]*b[2] > 0 else -1
    vectors = [(x-q[0], y-q[1], z-q[2]) for q in (a, b)]
    lengths = [math.sqrt(sum(t*t for t in v)) for v in vectors]
    residual = lengths[0]+sign*lengths[1]-math.sqrt(sum(t*t for t in a))-sign*math.sqrt(sum(t*t for t in b))
    gradient = tuple(vectors[0][i]/lengths[0]+sign*vectors[1][i]/lengths[1] for i in range(3))
    return residual, gradient


def sag(kind, x, y, radius, conic, p):
    if kind == 'OddAsphere':
        return conic_sag(x,y,radius,conic)+sum(p.get(i,0)*math.hypot(x,y)**i for i in range(1,9))
    if kind == 'Biconic':
        cx=1/p[1] if p[1] else 0;cy=1/radius if radius else 0
        return (cx*x*x+cy*y*y)/(1+math.sqrt(1-(1+p[2])*cx*cx*x*x-(1+conic)*cy*cy*y*y))
    if kind == 'Conjugate':
        z=0.
        for _ in range(40):
            value,gradient=conjugate_value(x,y,z,p)
            if abs(value)<1e-12:return z
            if abs(gradient[2])<1e-12:raise ValueError('Conjugate branch singular')
            z-=value/gradient[2]
        raise ValueError('Conjugate root not converged')
    raise ValueError(kind)


def normal(kind,x,y,radius,conic,p,step=1e-5):
    if kind=='Conjugate':
        return unit(conjugate_value(x,y,sag(kind,x,y,radius,conic,p),p)[1])
    dx=(sag(kind,x+step,y,radius,conic,p)-sag(kind,x-step,y,radius,conic,p))/(2*step)
    dy=(sag(kind,x,y+step,radius,conic,p)-sag(kind,x,y-step,radius,conic,p))/(2*step)
    return unit((-dx,-dy,1))


def reflected(direction, normal):
    d,n=unit(direction),unit(normal);dot=sum(a*b for a,b in zip(d,n))
    return tuple(a-2*dot*b for a,b in zip(d,n))


def extended_sag(kind,x,y,p,radius=50,conic=-.2):
    base=conic_sag(x,y,radius,conic);count=int(p[13]);r=math.hypot(x,y)/p[14]
    if kind in ('ExtendedAsphere','ExtendedOddAsphere'):
        power=2 if kind=='ExtendedAsphere' else 1
        return base+sum(p.get(14+i,0)*r**(power*i) for i in range(1,count+1))
    terms=[(d-j,j) for d in range(1,21) for j in range(d+1)]
    return base+sum(p.get(15+i,0)*(x/p[14])**a*(y/p[14])**b for i,(a,b) in enumerate(terms[:count]))
