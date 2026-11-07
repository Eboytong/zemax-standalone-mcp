"""Requested beam definitions compared with analytic moments at zero propagation."""
import asyncio,math,json
import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize("mode",["GaussianAngle","GaussianSizeAngle","AstigmaticGaussian","TopHat","Multimode"])
def test_additional_pop_beam_modes_native(mode):
    async def work(e):
        await e.model()
        theta_x,theta_y=map(math.radians,(.1,.05));lambda_mm=.00055
        params={0:.1,1:.2,2:.03,3:-.02};center=(.03,-.02);expected=(.1,.2);radius_factor=2
        extra={}
        if mode=="GaussianAngle":
            params={0:.1,1:.05,2:.03,3:-.02};expected=(lambda_mm/(math.pi*math.tan(theta_x)),lambda_mm/(math.pi*math.tan(theta_y)))
        elif mode=="GaussianSizeAngle":params={0:.2,1:.15,2:.1,3:.05,4:.03,5:-.02};expected=(.2,lambda_mm/(math.pi*math.tan(theta_y)))
        elif mode=="AstigmaticGaussian":
            params={0:.1,1:.2,2:10,3:-20,4:.03,5:-.02}
            expected=tuple(w*math.sqrt(1+(z/(math.pi*w*w/lambda_mm))**2)for w,z in ((.1,10),(.2,-20)))
        elif mode=="TopHat":radius_factor=2
        elif mode=="Multimode":
            params={0:42,1:.1};extra=dict(beam_file="two_top_hats.zmm");center=(0,0)
            expected=(math.sqrt(.1**2+.1**2/4)*2,)*2
        result=await e.finish(await e.call("run_pop",dict(request=dict(beam_type=mode,beam_parameters=params,
            x_sampling="S_256x256",y_sampling="S_256x256",x_width=2,y_width=2,**extra))))
        e.check("normalized beam power W",result["metrics"]["integrated_power"],1,atol=5e-4)
        g=result["grids"][0];mass=sum(v for row in g["values"] for v in row if v is not None)
        for axis_index,key in enumerate(("x","y")):
            mean=sum((g["min_"+key]+(ix if key=="x"else iy)*g["d"+key])*v for iy,row in enumerate(g["values"])for ix,v in enumerate(row)if v is not None)/mass
            variance=sum((g["min_"+key]+(ix if key=="x"else iy)*g["d"+key]-mean)**2*v for iy,row in enumerate(g["values"])for ix,v in enumerate(row)if v is not None)/mass
            e.check("requested beam center "+key,mean,center[axis_index],atol=.005 if mode in {"TopHat","Multimode"} else 5e-4,rtol=0)
            e.check("analytic twice RMS "+key,2*math.sqrt(variance),expected[axis_index],atol=.005 if mode in {"TopHat","Multimode"} else 5e-4,rtol=0)
        (e.folder/"beam_reference.json").write_text(json.dumps(dict(mode=mode,requested_parameters=params,
            expected_twice_rms_mm=expected,expected_center_mm=center,model="documented Gaussian propagation or uniform ellipse moments"),indent=2),encoding="utf-8")
    asyncio.run(execute("pop_mode_"+mode,work))


@pytest.mark.zemax
@pytest.mark.parametrize("filename,parameters,expected",[
    ("beamsamp1.DLL",{0:.1,1:.2},(.1,.2)),
    ("Laguerre beam.dll",{0:0,1:1,2:.1,3:0},(.1,math.sqrt(3)*.1)),
    ("Ince-Gaussian-64.dll",{0:.1,4:.1,5:0,6:2,7:2},None),
])
def test_local_pop_dll_parameter_failure_native(filename,parameters,expected):
    async def work(e):
        await e.model()
        result=await e.finish(await e.call("run_pop",dict(request=dict(beam_type="DLL",beam_file=filename,
            beam_parameters=parameters,fiber_type="DLL",fiber_file=filename,fiber_parameters=parameters,
            x_sampling="S_256x256",y_sampling="S_256x256",x_width=2,y_width=2))))
        metadata=result["task"]["settings"]["parameter_metadata"]["beam"]
        assert metadata["source"] in {"ZOS-API","isolated installed DLL UserParamNames"}
        e.check("DLL normalized output W",result["metrics"]["integrated_power"],1,atol=5e-4)
        e.check("identical DLL source/receiver overlap",result["metrics"]["receiver_efficiency"],1,atol=5e-4)
        if expected:
            g=result["grids"][0];mass=sum(v for row in g["values"]for v in row if v is not None)
            for axis,w in zip(("x","y"),expected):
                moment=sum((g["min_"+axis]+(ix if axis=="x"else iy)*g["d"+axis])**2*v
                    for iy,row in enumerate(g["values"])for ix,v in enumerate(row)if v is not None)/mass
                e.check("source-defined DLL twice RMS "+axis,2*math.sqrt(moment),w,atol=5e-4)
        (e.folder/"dll_scope.json").write_text(json.dumps(dict(filename=filename,parameters=parameters,
            numerical_reference="installed C source Gaussian/Laguerre second moments"if expected else"native call and power normalization only; Ince field reference pending"),indent=2),encoding="utf-8")
    asyncio.run(execute("pop_dll_"+filename.split('.')[0].replace(' ','_'),work))
