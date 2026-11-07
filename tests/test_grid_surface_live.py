import json
from pathlib import Path
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from support.paths import run_dir

@pytest.mark.zemax
def test_grid_sag_import_and_reload():
    folder=run_dir("grid_surface")
    data=folder/"parabolic.dat"
    lines=["33 33 0.5 0.5 0"]
    for iy in range(33):
        for ix in range(33):
            x=(ix-16)*.5;y=(iy-16)*.5
            lines.append(f"{.001*(x*x+2*y*y)} {.002*x} {.004*y} 0")
    data.write_text("\n".join(lines),encoding="ascii")
    b=Backend(Config(Config.from_env().install_dir,folder));events=[]
    def call(name,args=None):
        r=b.dispatch(name,args or {});events.append(dict(tool=name,arguments=args,response=r));assert r["ok"],r
        return r["data"]
    try:
        call("connect");call("new_system");call("insert_surfaces",dict(at=1))
        call("update_surfaces",dict(changes=[dict(surface=1,surface_type="GridSag",radius="Infinity",semi_diameter=4,replace_solves=True,import_file=str(data))]))
        for _ in range(2):
            sag=call("get_surface_geometry",dict(surface=1,points=[dict(x=.5,y=.5)]))["rows"][0]["sag"]
            assert sag==pytest.approx(.00075,rel=1e-7,abs=1e-8)
            path=str(folder/"imported.zos");call("save_lens_as",dict(path=path,overwrite=True));call("open_lens",dict(path=path))
        import time
        task=call("run_analysis",dict(request=dict(kind="surface_sag",surface=1,sampling="S_33x33")))
        while task["state"]=="running":time.sleep(.02);task=call("get_task_status",dict(task_id=task["task_id"]))
        result=call("get_task_result",dict(task_id=task["task_id"]))
        assert task["state"]=="succeeded",result
        full=json.loads(Path(next(a["path"]for a in result["artifacts"]if a["kind"]=="json")).read_text(encoding="utf-8"))
        g=full["grids"][0]
        # Compare lattice points; the native grid interpolator has its own
        # between-node behavior, separate from the result axis convention.
        for ix,iy in ((18,20),(20,18),(18,22)):
            x=g["min_x"]+ix*g["dx"];y=g["min_y"]+iy*g["dy"]
            assert g["values"][iy][ix]==pytest.approx(.001*(x*x+2*y*y),rel=1e-7,abs=1e-8),(g,x,y)
        call("disconnect")
    finally:
        b.shutdown();(folder/"calls.json").write_text(json.dumps(events,ensure_ascii=False,indent=2),encoding="utf-8");print("Grid surface evidence:",folder,flush=True)
