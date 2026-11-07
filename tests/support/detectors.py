"""Native-like arrays and detector backend for ordinary tests."""
from pathlib import Path
from types import SimpleNamespace as N
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

TRACE_OPTIONS=dict(use_polarization=False,split_rays=False,scatter_rays=False,ignore_errors=False,number_of_cores=1,random_seed=None,filter="")

class Matrix:
    Rank=2
    def __init__(self, rows):self.rows=rows
    def GetLength(self,i):return len(self.rows) if i==0 else len(self.rows[0]) if self.rows else 0
    def __getitem__(self,at):return self.rows[at[0]][at[1]]


def backend(tmp_path, kind="DetectorRectangle", array=None):
    row=N(Type=kind,ObjectData=N(NumberXPixels=2,NumberYPixels=2,NumberPPixels=3,NumberAPixels=4,MaxAngle=180),
          TypeData=N(NormalizeCoherentPower=False,UsePixelInterpolation=False))
    editor=N(NumberOfObjects=2,GetObjectAt=lambda _:row,
             GetAllDetectorDataSafe=lambda *_:array,GetAllPolarDetectorDataSafe=lambda *_:array,
             GetAllCoherentDataSafe=lambda *_:array)
    system=N(Mode="NonSequential",NCE=editor,SystemData=N(Units=N(
        SourceUnits="Watts",SourceUnitPrefix="Milli",AnalysisUnits="WattsPerCMSq",
        AnalysisUnitPrefix="Micro",LensUnits="Millimeters")))
    native=N(system=system,enum=lambda t,v:v,
             api=N(Editors=N(NCE=N(PolarDetectorDataType=None,DetectorDataType=None))))
    b=Backend(Config(Path("unused"),tmp_path),native)
    b.directory=tmp_path;b.work_path=tmp_path/"working.zos"
    b._checkpoint=lambda _: "before.zos"
    return b

