"""p=m=2 Ince eigenpolynomial, independently evaluated over the whole waist."""
import asyncio
import json
import math
import pytest
from tests.support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize("polarity",[0,1])
@pytest.mark.parametrize("focal_separation",[.05,.1])
def test_ince_22_independent_field_native(polarity,focal_separation):
    async def work(e):
        import numpy as np
        await e.model();w=.1;epsilon=2*(focal_separation/w)**2
        a=2+2*math.sqrt(1+epsilon**2);c=2*epsilon/a
        parameters={0:w,4:focal_separation,5:polarity,6:2,7:2}
        result=await e.finish(await e.call("run_pop",dict(request=dict(beam_type="DLL",beam_file="Ince-Gaussian-64.dll",beam_parameters=parameters,
            x_sampling="S_256x256",y_sampling="S_256x256",x_width=1,y_width=1))))
        g=result["grids"][0];x=g["min_x"]+np.arange(g["nx"])*g["dx"];y=g["min_y"]+np.arange(g["ny"])*g["dy"]
        xx,yy=x[None,:],y[:,None]
        polynomial=xx*yy if polarity else (c*c-1)+2*(c+1)*xx*xx/focal_separation**2+2*(c-1)*yy*yy/focal_separation**2
        amplitude=polynomial*np.exp(-(xx*xx+yy*yy)/w**2);reference=amplitude**2
        reference/=reference.sum()*g["dx"]*g["dy"]
        actual=np.asarray(g["values"],dtype=float)
        error=float(np.max(np.abs(actual/reference.max()-reference/reference.max())))
        record=dict(order=2,degree=2,polarity=polarity,waist_mm=w,f0_mm=focal_separation,epsilon=epsilon,
            eigenvalue=a,c=c,max_normalized_irradiance_error=error,tolerance=.001,
            equation="Y''+epsilon*sin(2eta)*Y'+(a-2epsilon*cos(2eta))*Y=0; C=A+cos(2eta), A=2epsilon/a",
            field="even: [c^2-1+2(c+1)x^2/f0^2+2(c-1)y^2/f0^2]*exp(-r^2/w0^2); odd: x*y*exp(-r^2/w0^2)",
            sources=["https://doi.org/10.1364/JOSAA.21.000873","https://optics.ansys.com/hc/en-us/articles/43071103262611-Modeling-high-order-laser-beams-in-OpticStudio"],
            scope="whole-plane waist irradiance at p=m=2; arbitrary orders and propagated phase are separate")
        (e.folder/"ince-reference.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
        e.check("whole-waist Ince normalized irradiance error",error,0,atol=.001,rtol=0)
        e.check("Ince integrated power W",result["metrics"]["integrated_power"],1,atol=.0005)
        beam=next(a["path"]for a in result["artifacts"]if a["kind"]=="beam")
        points=[]
        for px,py in ((.05,.05),(-.05,.05),(.05,-.05),(.1,.05),(.05,.1),(0,.05)):
            ix=round(px/g["dx"]+g["nx"]/2);iy=round(py/g["dy"]+g["ny"]/2)
            page=await e.call("get_beam_file",dict(request=dict(path=beam,start=iy*g["nx"]+ix,count=1,include_coordinates=True)))
            row=page["rows"][0];xx,yy=row["x"],row["y"]
            p=xx*yy if polarity else(c*c-1)+2*(c+1)*xx*xx/focal_separation**2+2*(c-1)*yy*yy/focal_separation**2
            expected_field=p*math.exp(-(xx*xx+yy*yy)/w**2)
            points.append(dict(x_mm=xx,y_mm=yy,reference=expected_field,real=row["ex_real"],imag=row["ex_imag"]))
        anchor=complex(points[0]["real"],points[0]["imag"])/points[0]["reference"]
        for point in points:
            actual=complex(point["real"],point["imag"])/anchor
            e.check("Ince signed real field up to common phase",actual.real,point["reference"],atol=.0005)
            e.check("Ince relative imaginary field",actual.imag,0,atol=.0005)
        record.update(complex_field_samples=points,phase_reference="one common global complex factor; signed field ratios independently specified by Ince polynomial")
        (e.folder/"ince-reference.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    asyncio.run(execute("ince_22_field",work))
