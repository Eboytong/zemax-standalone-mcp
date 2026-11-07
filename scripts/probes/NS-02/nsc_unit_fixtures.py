import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Create local unit-control models in one closed native process."""
import json
import sys
from pathlib import Path
from zemax_mcp.config import DEFAULT_INSTALL
from zemax_mcp.native import NativeSession
from zemax_mcp.data import unwrap

def create(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    native=NativeSession();cases=[]
    try:
        native.connect(DEFAULT_INSTALL);system=native.system
        for units in ("Watts","Lumens","Joules"):
            for prefix in ("None","Milli"):
                system.New(False);system.MakeNonSequential()
                system.SystemData.Wavelengths.GetWavelength(1).Wavelength=.55
                for _ in range(2):system.NCE.InsertNewObjectAt(1)
                native.set_enum(system.SystemData.Units,"SourceUnits",units)
                native.set_enum(system.SystemData.Units,"SourceUnitPrefix",prefix)
                for index,kind in ((1,"SourceRay"),(2,"DetectorPolar"),(3,"DetectorRectangle")):
                    row=system.NCE.GetObjectAt(index)
                    assert row.ChangeType(row.GetObjectTypeSettings(native.enum(native.api.Editors.NCE.ObjectType,kind)))
                    row.TypeData.UsePixelInterpolation=False
                    data=unwrap(row.ObjectData)
                    if index==1:
                        data.NumberOfAnalysisRays=1;data.Power=1;data.WaveNumber=1;data.ZCosine=1
                        row.SourcesData.RandomPolarization=False;row.SourcesData.Jx=1;row.SourcesData.Jy=0
                    elif index==2:
                        row.Material="";data.MaxAngle=180;data.RadialSize=10
                        data.NumberPPixels=181;data.NumberAPixels=36
                    else:
                        row.Material="ABSORB";row.ZPosition=20
                        data.NumberXPixels=8;data.NumberYPixels=8;data.XHalfWidth=2;data.YHalfWidth=2
                        row.TypeData.NormalizeCoherentPower=False
                path=folder/(units+"_"+prefix+".zos");system.SaveAs(str(path))
                tool=system.Tools.OpenNSCRayTrace()
                try:
                    assert str(tool.ClearDetectors(0))=="Success"
                    tool.UsePolarization=True
                    assert tool.RunAndWaitForCompletion() and tool.Succeeded
                finally:assert tool.Close()
                api=native.api.Editors.NCE
                ok,polar=system.NCE.GetPolarDetectorData(2,0,native.enum(api.PolarDetectorDataType,"Power"),0.)
                assert ok
                ok,flux=system.NCE.GetDetectorData(3,0,0,0.)
                assert ok
                coherent=float(sum(system.NCE.GetAllCoherentDataSafe(3,native.enum(api.DetectorDataType,"Power"))))
                cases.append(dict(units=units,prefix=prefix,path=str(path),
                    polar_power=float(polar),rectangle_flux=float(flux),rectangle_coherent=coherent,
                    polar_value_unit="Joules"if units=="Joules"else"Watts"))
    finally:native.disconnect()
    (folder/"reference.json").write_text(json.dumps(cases,indent=2),encoding="utf-8")
    return cases

if __name__=="__main__":create(sys.argv[1])

