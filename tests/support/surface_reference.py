"""2024 R2 geometric surface equations, evaluated without native geometry APIs."""
import math


def conic_sag(x,y,radius,conic=0):
    if radius is None or isinstance(radius,str) or radius == 0:
        return 0.
    r2=x*x+y*y;c=1/radius
    return c*r2/(1+math.sqrt(1-(1+conic)*c*c*r2))


def fringe6(x,y):
    return (1,x,y,2*(x*x+y*y)-1,x*x-y*y,2*x*y)


def sag(kind,x,y,radius=50.,conic=0.,parameters=None):
    p=parameters or {};get=lambda i:float(p.get(i,0))
    base=conic_sag(x,y,radius,conic)
    if kind=='Tilted':return x*get(1)+y*get(2)
    if kind=='Standard':return base
    if kind=='EvenAspheric':
        return base+sum(get(i)*(x*x+y*y)**i for i in range(1,9))
    if kind=='Toroidal':
        zy=conic_sag(0,y,radius,conic)+sum(get(i+1)*y**(2*i)for i in range(1,8))
        rotation=get(1)
        if not rotation:return zy
        return rotation-math.copysign(math.sqrt((rotation-zy)**2-x*x),rotation-zy)
    if kind=='ChebyShv':
        def T(i,t):return math.cos(i*math.acos(t))
        nx,ny=int(get(1)),int(get(2));sx,sy=get(3),get(4);k=13;total=0.;origin=0.
        for j in range(ny+1):
            for i in range(nx+1):
                if i==j==0:continue
                total+=get(k)*T(i,x/sx)*T(j,y/sy)
                origin+=get(k)*T(i,0)*T(j,0);k+=1
        # The local vertex is z=0. c00 is implicit, fixed by P(0,0),
        # rather than an independently editable displacement of the vertex.
        return conic_sag(x,y,radius,0)+sx*sy*(total-origin)
    if kind=='ZernikeFringeSag':
        count=int(get(13))
        if count>6:raise ValueError('Independent polynomial list is limited to six terms')
        qx=(x-get(9))/get(14);qy=(y-get(10))/get(14)
        return base+sum(get(i)*(x*x+y*y)**i for i in range(1,9))+sum(get(15+i)*v for i,v in enumerate(fringe6(qx,qy)[:count]))
    if kind=='Irregular':
        if any(get(i)!=0 for i in (1,2,3,4)):
            raise ValueError('This controlled reference uses zero internal tilt/decenter')
        r=math.hypot(x,y)/5;yp=(y*math.cos(math.radians(get(8)))-x*math.sin(math.radians(get(8))))/5
        return base+get(5)*r**4+get(6)*yp**2+get(7)*r*r*yp
    if kind=='GridSag':return base+sum(get(i)*(x*x+y*y)**i for i in range(1,9))+.001*(x*x+2*y*y)
    raise ValueError('No reference for '+kind)


def normal(kind,x,y,**kwargs):
    # Fixed physical step for this controlled normal reference.
    step=1e-5
    dx=(sag(kind,x+step,y,**kwargs)-sag(kind,x-step,y,**kwargs))/(2*step)
    dy=(sag(kind,x,y+step,**kwargs)-sag(kind,x,y-step,**kwargs))/(2*step)
    return (-dx,-dy,1.)
