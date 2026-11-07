"""Formal API controls for non-adopted LDE solve requests."""
from pathlib import Path
import json
from zemax_mcp.backend import Backend,COLUMNS
from zemax_mcp.config import Config
from zemax_mcp.data import clean

def run():
 folder=Path("verification/development/ED-02/diagnostics");folder.mkdir(parents=True,exist_ok=True)
 b=Backend(Config(Config.from_env().install_dir,folder/"native"));out=[]
 macro=Path.home()/"Documents/Zemax/Macros/ED02_DIAGNOSTIC018.ZPL";macro.write_text("SOLVERETURN 1.25\n",encoding="ascii")
 def call(n,a=None):
  r=b.dispatch(n,a or {});assert r["ok"],r;return r["data"]
 try:
  call("connect");from System import Array,Double; lens=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
  for cell,mode in [("semi_diameter","Maximum"),("mechanical_semi_diameter","SurfacePickup"),("chip_zone","SurfacePickup"),("mechanical_semi_diameter","ZPLMacro"),("chip_zone","ZPLMacro")]:
   for fixed in (False,True):
    call("open_lens",dict(path=lens))
    if mode=="Maximum":call("update_configurations",dict(actions=[dict(action="add",copy_current=True)]))
    c=b._cell(b._row(6),cell)
    if fixed:c.MakeSolveFixed()
    d=c.CreateSolveType(b.native.enum(b.native.api.Editors.SolveType,mode));p=getattr(d,"_S_"+mode)
    if mode=="SurfacePickup":p.Surface=1;p.Column=b.native.enum(b.native.api.Editors.LDE.SurfaceColumn,COLUMNS[cell]);p.ScaleFactor=1
    if mode=="ZPLMacro":p.Macro="ED02_DIAGNOSTIC018"
    rec=dict(cell=cell,mode=mode,fixed_first=fixed,before=str(c.Solve),data_type=str(d.Type) if hasattr(d,"Type") else None)
    try:
     rec["set_status"]=str(c.SetSolveData(d));rec["immediate"]=str(c.Solve);rec["update"]=str(b.system.UpdateStatus());rec["after"]=b._surface_data(6)["cells"][cell]
     if mode=="ZPLMacro":rec["macro"]=str(c.GetSolveData()._S_ZPLMacro.Macro)
    except Exception as ex:rec["error"]=str(ex)
    out.append(rec)
  call("open_lens",dict(path=lens));ix=Array[Double]([0.]*3)
  ret=b.system.LDE.GetIndex(5,3,ix);out.append(dict(get_index_return=ret,index=list(ix)))
  call("disconnect")
 finally:
  b.shutdown();macro.unlink(missing_ok=True);(folder/"controls.json").write_text(json.dumps(clean(out),ensure_ascii=False,indent=2),encoding="utf-8")
 print(out)
if __name__=="__main__":run()
