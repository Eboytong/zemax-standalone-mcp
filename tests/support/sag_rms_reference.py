"""Independent full-disk RMS sphere criterion reference for controlled paraboloids."""
import math
import numpy as np


def fit_paraboloid(a,semi_diameter,allow_offset,nodes=256):
    x,w=np.polynomial.legendre.leggauss(nodes)
    r=(x+1)*semi_diameter/2
    weights=w*semi_diameter/2*r
    weights/=sum(weights)
    raw=a*r*r
    def loss(c):
        difference=raw-c*r*r/(1+np.sqrt(1-(c*r)**2))
        offset=float(sum(weights*difference))if allow_offset else 0.
        return float(sum(weights*(difference-offset)**2)),offset
    lo,hi=sorted([2*a*.95,2*a*1.05])
    for _ in range(100):
        first=lo+(hi-lo)/3;second=hi-(hi-lo)/3
        if loss(first)[0]<loss(second)[0]:hi=second
        else:lo=first
    curvature=(lo+hi)/2
    variance,offset=loss(curvature)
    return dict(curvature=curvature,radius=1/curvature,offset=offset,rms=math.sqrt(variance),
        nodes=nodes,weighting='full disk area: integral(r*difference² dr)/integral(r dr)',
        offset_source='independent RMS optimum weighted-mean difference; not native physical-offset readback')
