"""Independent one-layer Fabry–Perot reference with exp(-i delta) propagation."""
import cmath
import math


def single_layer(angle_degrees,wavelength_um,substrate_index,thickness_um=.1,index=1.38):
    a=math.radians(angle_degrees)
    c0=math.cos(a)
    c1=math.sqrt(1-(math.sin(a)/index)**2)
    cs=math.sqrt(1-(math.sin(a)/substrate_index)**2)
    phase=cmath.exp(-1j*2*math.pi*index*thickness_um*c1/wavelength_um)
    amplitudes=[]
    for p in [False,True]:
        q0,q1,qs=(1/c0,index/c1,substrate_index/cs) if p else (c0,index*c1,substrate_index*cs)
        r01=(q0-q1)/(q0+q1);r12=(q1-qs)/(q1+qs)
        denominator=1+r01*r12*phase**2
        r=(r01+r12*phase**2)/denominator
        t=(2*q0/(q0+q1))*(2*q1/(q1+qs))*phase/denominator
        # Tangential-electric admittance gives the opposite reflected P basis.
        if p:r=-r
        amplitudes.append((r,t,abs(r)**2,abs(t)**2*qs/q0))
    s,p=amplitudes
    deg=lambda z:math.degrees(cmath.phase(z))
    return dict(reflection=[s[2],p[2],(s[2]+p[2])/2],
                transmission=[s[3],p[3],(s[3]+p[3])/2],absorption=[0,0,0],
                phase=[deg(s[1]),deg(p[1])],
                retardance=[deg(p[0]/s[0]),deg(p[1]/s[1])],
                diattenuation=[abs(s[2]-p[2])/(s[2]+p[2]),abs(s[3]-p[3])/(s[3]+p[3])])


def bk7_index(wavelength_um):
    # SCHOTT N-BK7 Sellmeier coefficients, wavelength in micrometers.
    b=[1.03961212,.231792344,1.01046945]
    c=[.00600069867,.0200179144,103.560653]
    l2=wavelength_um**2
    return math.sqrt(1+sum(bi*l2/(l2-ci) for bi,ci in zip(b,c)))
