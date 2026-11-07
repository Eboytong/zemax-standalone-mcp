"""Local 2024 R2 solve fixtures and direct-native control. Never edits official samples."""
import json,math,sys
from pathlib import Path
from zemax_mcp.backend import Backend,COLUMNS
from zemax_mcp.config import Config
from zemax_mcp.models import SolveSpec
from zemax_mcp.data import clean
from zemax_mcp.modeling import SOLVES,SOLVE_FIELDS
TYPES=("Standard","EvenAspheric","OddAsphere","Toroidal","Biconic","Paraxial","CoordinateBreak","GridSag","GridPhase")
CASES=[dict(id=f"{t}-{m}",surface_type=t,cell="radius"if m=="f_number"else"thickness",mode=m)for t in TYPES for m in ("f_number","marginal_ray_height","chief_ray_height","edge_thickness","position")]
CASES += [dict(id=f"CoordinateBreak-pickup_chief_ray-{i}",surface_type="CoordinateBreak",cell=f"parameter_{i}",mode="pickup_chief_ray")for i in range(1,5)]
IGNORED=[("Paraxial","radius","variable"),("Paraxial","radius","surface_pickup"),("CoordinateBreak","radius","variable"),("CoordinateBreak","radius","surface_pickup"),("CoordinateBreak","semi_diameter","fixed"),("CoordinateBreak","semi_diameter","surface_pickup"),("CoordinateBreak","conic","variable"),("CoordinateBreak","conic","surface_pickup"),("GridPhase","radius","variable"),("GridPhase","radius","surface_pickup")]
CASES += [dict(id=f"audit-{t}-{c}-{m}",surface_type=t,cell=c,mode=m,audit=True)for t,c,m in IGNORED]

def spec(case,variant=0):
    m=case["mode"];s=dict(mode=m)
    if m=="f_number":s["f_number"]=4
    elif m=="marginal_ray_height":s.update(height=.1,pupil_zone=(0,.7,-.7)[variant])
    elif m=="chief_ray_height":s["height"]=1
    elif m=="edge_thickness":s.update(thickness=2,radial_height=1)
    elif m=="position":s.update(source_surface=(1,6,7)[variant],length=(60,40,15)[variant])
    elif m=="pickup_chief_ray":s.update(field=2,wavelength=2)
    elif m=="surface_pickup":s["source_surface"]=1
    return s

def grid(folder,kind):
    path=folder/(kind+".dat");lines=["33 33 1 1 0"]
    for iy in range(33):
        for ix in range(33):
            x=ix-16;y=16-iy
            a,b,c=(.0001,.0002,0)if kind=="GridSag"else(.02,.03,.01)
            lines.append(f"{a*x*x+b*y*y+c*x*y} {2*a*x+c*y} {2*b*y+c*x} {c}")
    path.write_text("\n".join(lines),encoding="ascii");return path

def prepare(b,case,folder):
    def call(name,args=None):
        r=b.dispatch(name,args or {})
        if not r["ok"]:raise RuntimeError(str(r))
        return r["data"]
    folder.mkdir(parents=True,exist_ok=True)
    if case.get("audit"):
        call("new_system");call("insert_surfaces",dict(at=1))
        call("update_surfaces",dict(changes=[dict(surface=i,surface_type=case["surface_type"],replace_solves=True)for i in (1,2)]))
        target=2 if case["mode"]=="surface_pickup"else 1
    else:
        call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
        target=2 if case["mode"]=="pickup_chief_ray"else 6
        patch=dict(surface=target,surface_type=case["surface_type"],replace_solves=True)
        call("update_surfaces",dict(changes=[patch]))
        t=case["surface_type"]
        parameters={}
        if t in ("Toroidal","Biconic"):parameters[1]=80
        if t in ("EvenAspheric","OddAsphere"):
            for name,cell in b._cells(b._row(target)):
                if name.startswith("parameter_")and("4阶" in str(cell.Header)or"4th" in str(cell.Header)):
                    parameters[int(name.split("_")[1])]=1e-6;break
        if parameters:call("update_surfaces",dict(changes=[dict(surface=target,parameters=parameters,replace_solves=True)]))
        if t in ("GridSag","GridPhase"):
            call("update_surfaces",dict(changes=[dict(surface=target,import_file=str(grid(folder,t)),replace_solves=True)]))
    path=folder/"baseline.zos";call("save_lens_as",dict(path=str(path)))
    return dict(path=str(path),target=target,system=call("get_system_settings"),surface=call("get_surfaces",dict(start=target,count=1))["surfaces"][0])

def direct(b,case,target):
    cell=b._cell(b._row(target),case["cell"]);s=SolveSpec(**spec(case));before=str(cell.Solve)
    result=dict(before=before,requested=SOLVES[s.mode],header=str(cell.Header),active=bool(cell.IsActive),read_only=bool(cell.IsReadOnly))
    try:
        if s.mode in ("fixed","variable"):
            status=cell.MakeSolveFixed()if s.mode=="fixed"else cell.MakeSolveVariable()
        else:
            solve=cell.CreateSolveType(b.native.enum(b.native.api.Editors.SolveType,SOLVES[s.mode]))
            if s.mode=="surface_pickup":
                p=solve._S_SurfacePickup;p.Surface=1;p.Column=b.native.enum(b.native.api.Editors.LDE.SurfaceColumn,COLUMNS.get(case["cell"],case["cell"]))
            elif s.mode=="f_number":solve._S_FNumber.FNumber=s.f_number
            else:
                p=getattr(solve,"_S_"+SOLVES[s.mode])
                for k,v in SOLVE_FIELDS[SOLVES[s.mode]].items():setattr(p,v,getattr(s,k))
            result["is_valid"]=bool(solve.IsValid);status=cell.SetSolveData(solve)
        result["return"]=str(status)
    except Exception as exc:result["error"]=str(exc)
    result.update(actual=str(cell.Solve),value=b._cell_value(cell))
    result["adopted"]=result["actual"]==result["requested"] and result.get("return")in ("True","Success")
    return result

def probe(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    b=Backend(Config(Config.from_env().install_dir,folder/"native"));rows=[]
    try:
        assert b.dispatch("connect",{})["ok"]
        for case in CASES:
            row=dict(**case)
            try:
                row["fixture"]=prepare(b,case,folder/case["id"])
                row["direct_native"]=direct(b,case,row["fixture"]["target"])
            except Exception as exc:row["preparation_error"]=str(exc)
            rows.append(row)
            print(case["id"],row.get("direct_native",row.get("preparation_error")),flush=True)
    finally:
        b.shutdown();(folder/"direct-native.json").write_text(json.dumps(clean(rows),ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
if __name__=="__main__":probe(sys.argv[1])

