"""Public variable entry point: success flags must match the actual native mode."""
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

class Cell:
    IsReadOnly=False
    IsActive=True
    Header="parameter"
    def __init__(self,variable,outcome):
        self.Solve="Fixed"if variable else"Variable";self.outcome=outcome;self.calls=0
    def IsSolveTypeSupported(self,kind):return True
    def apply(self,mode):
        self.calls+=1
        if self.outcome=="adopt":self.Solve=mode
        return self.outcome!="false"
    def MakeSolveVariable(self):return self.apply("Variable")
    def MakeSolveFixed(self):return self.apply("Fixed")

def setup(tmp_path,scope,cells):
    system=NS(Mode="NonSequential"if scope=="object"else"Sequential")
    system.MCE=NS(NumberOfOperands=len(cells),GetOperandAt=lambda i:NS(GetOperandCell=lambda c:cells[i-1]))
    native=NS(system=system,api=NS(Editors=NS(SolveType=NS())),enum=lambda kind,name:name)
    b=Backend(Config(Path("unused"),tmp_path),native);b.work_path=tmp_path/"work.zos";b.directory=tmp_path
    b._checkpoint=lambda _:setattr(b,"last_checkpoint","before.zos")
    b._row=lambda i:NS(Type="Standard",SurfaceNumber=i);b._cell=lambda row,name:cells[row.SurfaceNumber-1]
    b._nsc_cell=lambda row,name:cells[row-1]
    b._configuration_number=lambda _:None;b._validate_solve=lambda *a:None
    b.get_variables=lambda _:dict(variables=[])
    return b

def item(scope,index,variable):
    return dict(variable=variable,**({"surface":index,"cell":"thickness"}if scope=="surface"else
        {"object":index,"cell":"x"}if scope=="object"else{"operand":index,"configuration":1}))

@pytest.mark.parametrize("scope",["surface","object","configuration"])
@pytest.mark.parametrize("variable",[False,True])
@pytest.mark.parametrize("outcome",["adopt","ignored","false"])
def test_public_variable_mode(tmp_path,scope,variable,outcome):
    cell=Cell(variable,outcome);b=setup(tmp_path,scope,[cell])
    response=b.dispatch("set_variables",dict(variables=[item(scope,1,variable)]))
    assert response["ok"]==(outcome=="adopt")
    assert cell.calls==1
    if outcome!="adopt":
        assert response["error"]["code"]=="SOLVE_UPDATE_FAILED"
        d=response["error"]["details"]
        assert d["requested"]==("Variable"if variable else"Fixed")
        assert d["actual"]==("Fixed"if variable else"Variable")
        assert d["partial_changes_possible"]
        assert response["context"]["model_revision"]==1

@pytest.mark.parametrize("scope",["surface","object","configuration"])
def test_batch_stops_after_ignored_mode(tmp_path,scope):
    cells=[Cell(True,"adopt"),Cell(True,"ignored"),Cell(True,"adopt")]
    b=setup(tmp_path,scope,cells)
    r=b.dispatch("set_variables",dict(variables=[item(scope,i,True)for i in (1,2,3)]))
    assert not r["ok"]
    assert [c.calls for c in cells]==[1,1,0]
    assert r["error"]["details"]["completed_count"]==1
    assert r["error"]["details"]["failed_index"]==1


def test_surface_partial_update_preserves_native_cause(tmp_path):
    cells=[Cell(True,"ignored")]
    b=setup(tmp_path,"surface",cells)
    b._validate_aperture_batch=lambda *a:None
    b._validate_surface_extension=lambda *a:None
    b._apply_surface_extension=lambda *a:None
    r=b.dispatch("update_surfaces",dict(changes=[dict(surface=1,replace_solves=True,solves={"radius":{"mode":"variable"}})]))
    assert not r["ok"] and r["error"]["code"]=="PARTIAL_UPDATE"
    cause=r["error"]["details"]["cause"]
    assert cause["code"]=="SOLVE_UPDATE_FAILED"
    assert cause["details"]["requested"]=="Variable"
    assert cause["details"]["actual"]=="Fixed"
    assert r["error"]["details"]["completed_surfaces"]==[]


@pytest.mark.parametrize('outcome',['ignored','false'])
def test_replacing_pickup_must_adopt_fixed_before_value_write(tmp_path,outcome):
    cell=Cell(False,outcome);cell.Solve='SurfacePickup'
    b=setup(tmp_path,'surface',[cell]);writes=[]
    b._validate_aperture_batch=lambda *a:None
    b._validate_surface_extension=lambda *a:None
    b._apply_surface_extension=lambda *a:None
    b._write_cell=lambda *a,**kw:writes.append(a)
    r=b.dispatch('update_surfaces',dict(changes=[dict(surface=1,parameters={21:.004},replace_solves=True)]))
    assert not r['ok'] and r['error']['code']=='PARTIAL_UPDATE'
    assert r['error']['details']['cause']['code']=='SOLVE_UPDATE_FAILED'
    assert not writes and cell.calls==1
    assert r['context']['model_revision']==1


def test_inactive_high_parameter_rejected_before_batch_mutation(tmp_path):
    cells=[Cell(True,'adopt'),None]
    b=setup(tmp_path,'surface',cells)
    b._validate_surface_extension=lambda *a:None
    r=b.dispatch('update_surfaces',dict(changes=[dict(surface=1,parameters={21:.1}),dict(surface=2,parameters={254:.2})]))
    assert not r['ok'] and r['error']['code']=='CELL_NOT_WRITABLE'
    assert r['context']['model_revision']==0 and cells[0].calls==0


@pytest.mark.parametrize('kind',['ExtendedAsphere','ExtendedOddAsphere','ExtendedPolynomial'])
@pytest.mark.parametrize('solve',[False,True])
def test_term_reduction_conflict_is_preflight_error(tmp_path,kind,solve):
    cell=Cell(True,'adopt');b=setup(tmp_path,'surface',[cell])
    b._row=lambda i:NS(Type=kind,SurfaceNumber=i)
    change=dict(surface=1,parameters={13:3},replace_solves=True)
    if solve:change['solves']={'parameter_21':dict(mode='variable')}
    else:change['parameters'][21]=.1
    r=b.dispatch('update_surfaces',dict(changes=[change]))
    assert not r['ok'] and r['error']['code']=='CELL_NOT_WRITABLE'
    assert r['error']['details']['inactive_parameters']==[21]
    assert r['context']['model_revision']==0 and cell.calls==0
