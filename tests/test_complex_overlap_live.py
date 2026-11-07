"""Arbitrary complex fields against the documented power-weighted component overlaps."""
import asyncio
import json
import math
import struct

import pytest

from support.native import execute


def beam_file(path,nx,ny,dx,dy,ex,ey):
    header=[1,nx,ny,1,0,0,0,0,0]
    metadata=[dx,dy,0,math.pi*.1**2/.00055,.1,0,math.pi*.1**2/.00055,.1,.00055,1,0,0]+[0.]*8
    with path.open("wb")as stream:
        stream.write(struct.pack("<9i20d",*header,*metadata))
        for component in (ex,ey):
            for value in component:stream.write(struct.pack("<dd",value.real,value.imag))


@pytest.mark.zemax
@pytest.mark.parametrize("receiver",["matched","elliptical_mismatch","orthogonal"])
def test_complex_vector_file_overlap_native(receiver):
    async def work(e):
        await e.model()
        await e.call("update_system_settings",dict(settings=dict(polarization=dict(unpolarized=False,jx=1,jy=0))))
        nx,ny=128,64;dx,dy=.01,.02;source_x=[];source_y=[];receiver_x=[];receiver_y=[]
        for iy in range(ny):
            for ix in range(nx):
                x=(ix-nx/2)*dx;y=(iy-ny/2)*dy
                a=math.exp(-(x/.12)**2-(y/.09)**2)*(1+.2*math.cos(12*x))
                phase=7*x-3*y+5*x*y
                source=a*complex(math.cos(phase),math.sin(phase))
                b=math.exp(-((x-.025)/.1)**2-((y+.015)/.13)**2)
                phase_b=-4*x+2*y+3*x*x
                target=b*complex(math.cos(phase_b),math.sin(phase_b))
                sx,sy=source,.5j*source
                if receiver=="matched":rx,ry=sx,sy
                elif receiver=="orthogonal":rx,ry=.5j*source,source
                else:rx,ry=target,.3*complex(math.cos(.7),math.sin(.7))*target
                source_x.append(sx);source_y.append(sy);receiver_x.append(rx);receiver_y.append(ry)
        area=dx*dy
        inner=sum((sx.conjugate()*rx+sy.conjugate()*ry)*area for sx,sy,rx,ry in zip(source_x,source_y,receiver_x,receiver_y))
        source_norm=sum((abs(x)**2+abs(y)**2)*area for x,y in zip(source_x,source_y))
        receiver_norm=sum((abs(x)**2+abs(y)**2)*area for x,y in zip(receiver_x,receiver_y))
        vector_reference=abs(inner)**2/(source_norm*receiver_norm)
        expected=0.;components=[]
        for incident,received in ((source_x,receiver_x),(source_y,receiver_y)):
            a=sum(abs(v)**2*area for v in incident);b=sum(abs(v)**2*area for v in received)
            overlap=sum(s.conjugate()*r*area for s,r in zip(incident,received))
            eta=abs(overlap)**2/(a*b)
            expected+=a/source_norm*eta
            components.append(dict(incident_power=a,receiver_norm=b,efficiency=eta,weight=a/source_norm))
        source=e.folder/"source.zbf";target=e.folder/"receiver.zbf"
        beam_file(source,nx,ny,dx,dy,source_x,source_y);beam_file(target,nx,ny,dx,dy,receiver_x,receiver_y)
        result=await e.finish(await e.call("run_pop",dict(request=dict(beam_type="File",beam_file=str(source),beam_parameters={},
            fiber_type="File",fiber_file=str(target),fiber_parameters={},use_polarization=True,ignore_fiber_polarization=False,
            x_sampling="S_128x128",y_sampling="S_64x64",x_width=nx*dx,y_width=ny*dy))))
        assert result["coupling_definition"]["vector_inner_product"] is False
        e.check("arbitrary complex component-weighted receiver efficiency",result["metrics"]["receiver_efficiency"],expected,atol=5e-4)
        e.check("complex vector system efficiency",result["metrics"]["system_efficiency"],1,atol=5e-4)
        e.check("complex vector total coupling",result["metrics"]["total_coupling_efficiency"],expected,atol=5e-4)
        (e.folder/"overlap_reference.json").write_text(json.dumps(dict(receiver=receiver,
            formula="sum(Ps_component/Ps_total * abs(integral conj(Es_component)*Er_component)^2/(Ps_component*Pr_component))",
            definition_source="manual lines 21118 and 21130: independently normalized component integrals, weighted by incident power",
            vector_inner_product_reference=vector_reference,component_integrals=components,
            nx=nx,ny=ny,dx_mm=dx,dy_mm=dy,source_norm=source_norm,receiver_norm=receiver_norm,
            inner_real=inner.real,inner_imag=inner.imag,expected_efficiency=expected,actual=result["metrics"],
            scope="same coincident perpendicular planes; documented component-weighted POP coupling, not one normalized vector inner product; no large-angle projection"),indent=2),encoding="utf-8")
    asyncio.run(execute("complex_overlap_"+receiver,work))
