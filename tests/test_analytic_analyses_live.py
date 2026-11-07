"""Independent references for an on-axis paraboloid in air, and its diffraction."""
import json,math,time
from pathlib import Path
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.analyses import ANALYSES
from zemax_mcp.evaluation import interpolate
from support.paths import run_dir

def bessel(order,x):
    term=(x/2)**order/math.factorial(order);total=term
    for k in range(1,70):
        term*=-(x*x/4)/(k*(k+order));total+=term
        if abs(term)<1e-18:break
    return total

@pytest.mark.zemax
def test_parabolic_mirror_independent_references():
    folder=run_dir("analytic_analyses")
    b=Backend(Config(Config.from_env().install_dir,folder));events=[];checks=[];failures=[]
    def call(name,args=None):
        response=b.dispatch(name,args or {});events.append(dict(tool=name,arguments=args,response=response));assert response["ok"],response
        return response["data"]
    def analyze(request):
        task=call("run_analysis",dict(request=request));deadline=time.monotonic()+60
        while task["state"]not in {"succeeded","failed","cancelled"}:
            assert time.monotonic()<deadline;time.sleep(.01);task=call("get_task_status",dict(task_id=task["task_id"]))
        result=call("get_task_result",dict(task_id=task["task_id"]));assert task["state"]=="succeeded",result
        return json.loads(Path(next(a["path"]for a in result["artifacts"]if a["kind"]=="json")).read_text(encoding="utf-8"))
    def check(kind,label,actual,expected,atol=1e-8):
        passed=abs(actual-expected)<=atol+1e-7*abs(expected)
        checks.append(dict(kind=kind,check=label,actual=actual,expected=expected,absolute_tolerance=atol,passed=passed))
        if not passed:failures.append(checks[-1])
    try:
        call("connect");call("new_system")
        call("update_system_settings",dict(aperture_value=10,fields=[dict(x=0,y=0),dict(x=0,y=1),dict(x=0,y=2)],wavelengths=[dict(wavelength_um=.48),dict(wavelength_um=.55),dict(wavelength_um=.65)],primary_wavelength=2))
        call("update_surfaces",dict(changes=[dict(surface=1,radius=-200,conic=-1,material="MIRROR",thickness=-100,semi_diameter=5,replace_solves=True)]))
        call("save_lens_as",dict(path=str(folder/"paraboloid.zos")))
        for kind in ANALYSES:
            request=dict(kind=kind)
            if kind.startswith("surface_"):request.update(surface=1,sampling="S_65x65")
            elif kind in {"longitudinal_aberration","lateral_color","focal_shift"}:pass
            elif kind=="field_curvature_distortion":request["wavelength"]=2
            else:
                request.update(field=1,wavelength=2)
                if kind not in {"ray_fan","opd_fan"}:request["sampling"]="S_256x256"
                if kind.startswith("zernike_"):request["maximum_terms"]=37 if kind=="zernike_fringe"else 22
                if "through_focus"in kind:request.update(number_of_steps=3,delta_focus=.1,frequency=50)
                if kind in {"huygens_mtf","huygens_psf","huygens_psf_cross","fft_psf"}:request["image_sampling"]="S_256x256"
                if kind in {"geometric_through_focus_mtf","geometric_encircled_energy"}:request["multiply_by_diffraction_limit"]=False
            result=analyze(request)
            if kind in {"huygens_mtf","geometric_mtf"}or"through_focus"in kind:
                s=result["series"][0];target=0 if"through_focus"in kind else 50
                nu=50*.00055*100/10
                expected=1 if kind.startswith("geometric_")else 2/math.pi*(math.acos(nu)-nu*math.sqrt(1-nu*nu))
                check(kind,"MTF at 50 cycles/mm, focus=0",interpolate(s["x"],[row[0]for row in s["y"]],target),expected,.02)
            elif kind in {"fft_psf","huygens_psf","fft_psf_cross","huygens_psf_cross"}:
                if result.get("grids"):
                    g=result["grids"][0];iy,ix=max(((iy,ix)for iy,row in enumerate(g["values"])for ix,v in enumerate(row)if v is not None),key=lambda p:g["values"][p[0]][p[1]])
                    samples=[((j-ix)*g["dx"],g["values"][iy][j])for j in range(max(0,ix-6),min(g["nx"],ix+7))]
                else:
                    s=result["series"][0];samples=list(zip(s["x"],[y[0]for y in s["y"]]));samples=[(x,y)for x,y in samples if abs(x)<=8]
                for radius,value in samples:
                    u=math.pi*abs(radius)/(0.55*10)
                    expected=(2*bessel(1,u)/u)**2 if u else 1
                    check(kind,"Airy profile relative to sampled peak",value,expected,.025)
            elif kind in {"diffraction_encircled_energy","geometric_encircled_energy"}:
                s=result["series"][-1];value=interpolate(s["x"],[y[0]for y in s["y"]],5)
                u=math.pi*5/(.55*10);expected=1 if kind=="geometric_encircled_energy"else 1-bessel(0,u)**2-bessel(1,u)**2
                check(kind,"encircled fraction within 5 um",value,expected,.05)
            elif kind=="wavefront":
                check(kind,"on-axis paraboloid OPD",max(abs(v)for row in result["grids"][0]["values"]for v in row if v is not None),0)
            elif kind.startswith("zernike_"):
                check(kind,"on-axis paraboloid coefficients",max(abs(r["value"])for r in result["rows"]),0)
            elif kind.startswith("surface_"):
                if result.get("grids"):
                    g=result["grids"][0];iy=ix=g["nx"]//2+4
                    x=g["min_x"]+ix*g["dx"];y=g["min_y"]+iy*g["dy"];value=g["values"][iy][ix]
                else:
                    s=result["series"][0];i=len(s["x"])//2+4;x=s["x"][i];y,value=s["y"][i]
                expected=-(x*x+y*y)/400 if"sag"in kind else -.005/(1+.005**2*(x*x+y*y))**1.5 if"curvature"in kind else 0
                check(kind,"analytic local surface value",value,expected)
            else:
                series=result["series"]
                values=[v for s in series for row in s["y"]for v in row if v is not None]
                if kind=="field_curvature_distortion":values=[v for s in series for v in s["y"][0]if v is not None]
                if kind=="lateral_color":values=[row[0]for s in series for row in s["y"]]
                check(kind,"zero geometric/chromatic aberration or center-field origin",max(abs(v)for v in values),0)
            print("Analytic",kind,"checked",flush=True)
        for kind in ["geometric_through_focus_mtf","geometric_encircled_energy"]:
            request=dict(kind=kind,field=1,wavelength=2,sampling="S_256x256",multiply_by_diffraction_limit=True)
            if kind.endswith("mtf"):request.update(frequency=50,delta_focus=.1,number_of_steps=3)
            result=analyze(request);s=result["series"][0]
            if kind.endswith("mtf"):
                nu=50*.00055*100/10;expected=2/math.pi*(math.acos(nu)-nu*math.sqrt(1-nu*nu));target=0
            else:
                u=math.pi*5/(.55*10);expected=1-bessel(0,u)**2-bessel(1,u)**2;target=5
            check(kind,"explicit diffraction correction",interpolate(s["x"],[r[0]for r in s["y"]],target),expected,.02)
        call("disconnect")
    finally:
        b.shutdown()
        (folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8")
        (folder/"checks.json").write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding="utf-8")
        print("Analytic analysis evidence:",folder,flush=True)
    assert not failures,failures
