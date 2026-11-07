"""Receiver definitions checked with explicit scalar overlap integrals."""
import asyncio,math,struct
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize("mode",["GaussianAngle","GaussianSizeAngle","AstigmaticGaussian","TopHat","File"])
def test_receiver_modes_native(mode):
    async def work(e):
        await e.model();w=.1;wave=.00055;expected=1.;extra={}
        params={0:w,1:w}
        if mode in {"GaussianAngle","GaussianSizeAngle"}:
            wf=wave/(math.pi*math.tan(math.radians(.1)))
            params={0:.1,1:.1}if mode=="GaussianAngle"else {0:wf,1:wf,2:.1,3:.1}
            expected=(2*w*wf/(w*w+wf*wf))**2
        elif mode=="AstigmaticGaussian":params={0:w,1:w,2:0,3:0}
        elif mode=="TopHat":
            radius=.2;params={0:radius,1:radius};expected=2*w*w/(radius*radius)*(1-math.exp(-radius*radius/(w*w)))**2
        elif mode=="File":
            nx=ny=128;d=2/nx
            header=[1,nx,ny,0,0,0,0,0,0];metadata=[d,d,0,math.pi*w*w/wave,w,0,math.pi*w*w/wave,w,wave,1,0,0]+[0.]*8
            values=[]
            for iy in range(ny):
                for ix in range(nx):values.extend((math.exp(-(((ix-nx/2)*d/w)**2+((iy-ny/2)*d/w)**2)),0))
            file=e.folder/"receiver.zbf";file.write_bytes(struct.pack("<9i20d",*header,*metadata)+struct.pack("<"+str(len(values))+"d",*values))
            extra=dict(fiber_file=str(file));params={}
        r=await e.finish(await e.call("run_pop",dict(request=dict(beam_parameters={0:w,1:w},fiber_type=mode,
            fiber_parameters=params,x_sampling="S_256x256",y_sampling="S_256x256",x_width=2,y_width=2,**extra))))
        e.check("receiver scalar overlap "+mode,r["metrics"]["receiver_efficiency"],expected,atol=.005 if mode=="TopHat"else 5e-4)
        e.check("receiver efficiency product",r["metrics"]["total_coupling_efficiency"],r["metrics"]["receiver_efficiency"]*r["metrics"]["system_efficiency"])
    asyncio.run(execute("pop_receiver_"+mode,work))
