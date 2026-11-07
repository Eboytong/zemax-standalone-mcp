"""Independent transport in a sphere, with a solid-angle-uniform scattering cone."""
import math


def sphere_transport(half_angle_deg, rays=100000, seed=42, radius=3., mean_path=2.):
    import numpy as np
    rng=np.random.default_rng(seed)
    positions=np.zeros((rays,3));directions=np.zeros((rays,3));directions[:,2]=1
    length=np.zeros(rays);events=np.zeros(rays,int);active=np.ones(rays,bool)
    for _ in range(1000):
        idx=np.flatnonzero(active)
        if not len(idx):return events,length
        p=positions[idx];d=directions[idx];dot=np.sum(p*d,axis=1)
        boundary=-dot+np.sqrt(dot*dot+radius*radius-np.sum(p*p,axis=1))
        free=rng.exponential(mean_path,len(idx));scatter=free<boundary
        length[idx]+=np.minimum(free,boundary)
        active[idx[~scatter]]=False
        selected=idx[scatter]
        if not len(selected):continue
        positions[selected]+=free[scatter,None]*d[scatter]
        old=d[scatter];basis=np.zeros_like(old)
        use_x=abs(old[:,2])>.9;basis[use_x,0]=1;basis[~use_x,2]=1
        u=np.cross(old,basis);u/=np.linalg.norm(u,axis=1)[:,None];v=np.cross(old,u)
        mu=rng.uniform(math.cos(math.radians(half_angle_deg)),1,len(selected))
        phi=rng.uniform(0,2*math.pi,len(selected));sine=np.sqrt(1-mu*mu)
        directions[selected]=mu[:,None]*old+sine[:,None]*(np.cos(phi)[:,None]*u+np.sin(phi)[:,None]*v)
        events[selected]+=1
    raise ValueError('Independent transport did not converge within its fixed event bound')
