"""Read local solve metadata; application lifecycle is always closed."""
import json
from pathlib import Path
from zemax_mcp.config import Config
from zemax_mcp.native import NativeSession

def probe(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    s=NativeSession();out={"surfaces":[],"closed":False}
    try:
        app=s.connect(Config.from_env().install_dir)
        from System import Enum
        from System.Reflection import Assembly
        asm=Assembly.LoadFrom(str(Config.from_env().install_dir/"ZOSAPI_Interfaces.dll"))
        enum=asm.GetType("ZOSAPI.Editors.SolveType")
        out["enums"]={str(n):int(Enum.Parse(enum,n)) for n in Enum.GetNames(enum)}
        out["interfaces"]={str(t.Name):{str(p.Name):str(p.PropertyType) for p in t.GetProperties()} for t in asm.GetTypes() if str(t.Name).startswith("ISolve")}
        out["version"]=f"{app.ZOSMajorVersion}.{app.ZOSMinorVersion}.{app.ZOSSPVersion}";out["license"]=str(app.LicenseStatus)
        lde=s.system.LDE
        for kind in [str(x) for x in lde.GetSurfaceAt(1).AvailableSurfaceTypes()]:
            row=lde.GetSurfaceAt(1)
            settings=row.GetSurfaceTypeSettings(s.enum(s.api.Editors.LDE.SurfaceType,kind))
            if not row.ChangeType(settings):
                out.setdefault("type_rejections",[]).append(kind);continue
            cells={}
            for name in ("RadiusCell","ThicknessCell","MaterialCell","SemiDiameterCell","MechanicalSemiDiameterCell","ChipZoneCell","ConicCell","TCECell"):
                c=getattr(row,name)
                cells[name]={"active":bool(c.IsActive),"read_only":bool(c.IsReadOnly),"available":list(dict.fromkeys(str(x) for x in c.GetAvailableSolveTypes()))}
            for i in range(1,255):
                c=row.GetSurfaceCell(s.enum(s.api.Editors.LDE.SurfaceColumn,"Par"+str(i)))
                if c is not None and c.IsActive:cells["parameter_"+str(i)]={"active":True,"read_only":bool(c.IsReadOnly),"header":str(c.Header),"available":list(dict.fromkeys(str(x) for x in c.GetAvailableSolveTypes()))}
            out["surfaces"].append(dict(type=kind,cells=cells))
        row=lde.GetSurfaceAt(1)
        out["macros"]=list(row.ThicknessCell.CreateSolveType(s.api.Editors.SolveType.ZPLMacro)._S_ZPLMacro.GetAvailableMacros())
    finally:
        s.disconnect();out["closed"]=True
        (folder/"probe.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
        print("probe closed",folder)
if __name__=="__main__":probe("verification/development/ED-02/all-types")
