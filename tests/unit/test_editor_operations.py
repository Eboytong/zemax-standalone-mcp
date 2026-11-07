"""Editor operations use native counts, adopted types and structured failures."""
from pathlib import Path
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.editors import EditorsMixin
from zemax_mcp.editor_models import EditorInsert,EditorCopy,EditorMetadata
from zemax_mcp.models import SaveLens,OpenLens
from zemax_mcp.errors import ZemaxError

class Row:
    def __init__(self,owner,kind='BLNK'):
        self.owner=owner;self.Type=kind;self.IsActive=True
        for j in range(1,4):setattr(self,f'Param{j}',j);setattr(self,f'Param{j}Enabled',True)
    @property
    def OperandNumber(self):return self.owner.rows.index(self)+1
    @property
    def TypeName(self):return self.Type
    def AvailableOperandTypes(self):return ['BLNK','TRAD','TTHI','REAY']
    def AvailableConfigOperandTypes(self):return ['MOFF','THIC']
    def GetOperandCell(self,column):return N(IsActive=True,IsReadOnly=column==3,DataType='Double',Header='column'+str(column),DoubleValue=float(column))
    def ChangeType(self,kind):
        if getattr(self.owner,'reject_type',False):return True
        self.Type=kind;return True

class Table:
    def __init__(self):
        self.rows=[Row(self,'TRAD'),Row(self,'TTHI')];self.NumberOfConfigurations=2;self.next_fail=False
    @property
    def NumberOfOperands(self):return len(self.rows)
    def GetOperandAt(self,i):return self.rows[i-1]
    def InsertNewOperandAt(self,i):
        if self.next_fail:return None
        row=Row(self);self.rows.insert(i-1,row);return row
    def CopyOperands(self,start,count,at):
        kinds=[r.Type for r in self.rows[start-1:start-1+count]]
        for j,k in enumerate(kinds):self.rows.insert(at-1+j,Row(self,k))
        return count
    def SaveToleranceFile(self,path):Path(path).write_text('native tolerance fixture',encoding='utf-8')
    def LoadToleranceFile(self,path):self.loaded=path;return True

class Backend(EditorsMixin):
    def __init__(self):
        self.table=Table();self.system=N(MFE=self.table,MCE=self.table,TDE=self.table)
        self.revision=0;self.last_checkpoint='before.zos'
        enums=N(MeritOperandType=N(),MultiConfigOperandType=N(),ToleranceOperandType=N(),MeritColumn=N(),ToleranceColumn=N())
        self.native=N(api=N(Editors=N(MFE=enums,MCE=enums,TDE=enums)),enum=lambda _,n:n,enum_names=lambda _:['Param1','Target','Value'])
    def _require_sequential(self):pass
    def _require_work(self):pass
    def _mutate(self,_):self.revision+=1
    def _cell_value(self,cell):return cell.DoubleValue
    def get_merit_function(self,req):return self.result(req)
    def get_tolerances(self,req):return self.result(req)
    def get_configurations(self,req):return self.result(req)
    def result(self,req):return dict(total=self.table.NumberOfOperands,start=req.start if req else 1,types=[r.Type for r in self.table.rows])

@pytest.mark.parametrize('editor',['MFE','MCE','TDE'])
def test_native_insert_and_copy_readback(editor):
    b=Backend();r=b.insert_editor_rows(EditorInsert(editor=editor,at=2,count=2))
    assert r['completed_operands']==[2,3]and r['total_after']==4
    assert [x.Type for x in b.table.rows]==['TRAD','BLNK','BLNK','TTHI']
    r=b.copy_editor_rows(EditorCopy(editor=editor,start=1,count=2,at=5))
    assert r['copied']==2 and [x.Type for x in b.table.rows][-2:]==['TRAD','BLNK']
    assert b.revision==2

def test_copy_overlapping_source_uses_original_range():
    b=Backend();b.copy_editor_rows(EditorCopy(editor='MFE',start=1,count=2,at=2))
    assert [x.Type for x in b.table.rows]==['TRAD','TRAD','TTHI','TTHI']

@pytest.mark.parametrize('req',[EditorInsert(editor='TDE',at=4),EditorCopy(editor='TDE',start=1,count=3,at=1),EditorCopy(editor='TDE',start=1,count=1,at=4)])
def test_bounds_before_checkpoint(req):
    b=Backend()
    with pytest.raises(ZemaxError)as err:
        (b.insert_editor_rows if isinstance(req,EditorInsert)else b.copy_editor_rows)(req)
    assert err.value.code=='INDEX_OUT_OF_RANGE'and b.revision==0

def test_typed_insert_rejects_unsupported_type_before_mutation():
    b=Backend()
    with pytest.raises(ZemaxError)as err:b.insert_editor_rows(EditorInsert(editor='TDE',at=1,operand_type='bad'))
    assert err.value.code=='UNSUPPORTED_OPERAND'and b.revision==0

def test_insert_silent_type_rejection_retains_inserted_state():
    b=Backend();b.table.reject_type=True
    with pytest.raises(ZemaxError)as err:b.insert_editor_rows(EditorInsert(editor='TDE',at=2,operand_type='TRAD'))
    d=err.value.details
    assert d['cause']['code']=='SETTING_REJECTED'and d['total_after']==3 and d['failed_operand']==2

def test_copy_count_disagreement_reports_native_effect():
    b=Backend();original=b.table.CopyOperands
    def bad(*args):original(*args);return 0
    b.table.CopyOperands=bad
    with pytest.raises(ZemaxError)as err:b.copy_editor_rows(EditorCopy(editor='TDE',start=1,count=1,at=3))
    assert err.value.details['cause']['code']=='SETTING_REJECTED'and err.value.details['total_after']==3

def test_insert_readback_error_preserves_completed_rows():
    b=Backend();b.get_tolerances=lambda _:(_ for _ in ()).throw(RuntimeError('readback failed'))
    with pytest.raises(ZemaxError)as err:b.insert_editor_rows(EditorInsert(editor='TDE',at=1,count=2))
    assert err.value.details['completed_operands']==[1,2]and err.value.details['cause']['message']=='readback failed'

def test_save_load_tolerance_files_and_overwrite_condition(tmp_path):
    b=Backend();path=tmp_path/'example.tol'
    saved=b.save_tolerance_file(SaveLens(path=str(path)))
    assert saved['artifacts'][0]['kind']=='tolerance_file'and b.revision==0
    with pytest.raises(ZemaxError)as err:b.save_tolerance_file(SaveLens(path=str(path)))
    assert err.value.code=='OUTPUT_EXISTS'
    loaded=b.load_tolerance_file(OpenLens(path=str(path)))
    assert loaded['tolerances']['total']==2 and b.revision==1 and b.table.loaded==str(path)

def test_native_file_rejection_preserves_error_and_checkpoint(tmp_path):
    b=Backend();path=tmp_path/'example.tol';path.write_text('fixture',encoding='utf-8');b.table.LoadToleranceFile=lambda _:False
    with pytest.raises(ZemaxError)as err:b.load_tolerance_file(OpenLens(path=str(path)))
    assert err.value.details['cause']['code']=='EDITOR_LOAD_FAILED'and err.value.details['checkpoint']=='before.zos'

def test_mce_metadata_returns_configuration_cells_and_parameters():
    b=Backend();r=b.get_editor_metadata(EditorMetadata(editor='MCE',operand=2,column_start=1,column_count=1))
    assert r['columns'][0]['column']==2 and r['total_columns']==2 and r['next_start']is None
    assert r['parameters']['1']==dict(enabled=True,value=1)
    assert r['available_operand_types']==['MOFF','THIC']and r['file_operations']==[]

@pytest.mark.parametrize('model,payload',[(EditorInsert,dict(editor='NCE',at=1)),(EditorInsert,dict(editor='TDE',at=0)),(EditorCopy,dict(editor='MFE',start=1,count=True,at=1)),(EditorMetadata,dict(editor='MCE',column_start=-1))])
def test_editor_request_boundaries(model,payload):
    with pytest.raises(ValidationError):model(**payload)


@pytest.mark.parametrize('editor',['MFE','TDE'])
def test_native_column_numbers_and_metadata_pagination(editor):
    b=Backend();columns={'Param1':2,'Target':10,'Value':12}
    b.native.enum=lambda _,name:columns[name]
    r=b.get_editor_metadata(EditorMetadata(editor=editor,operand=1,column_start=1,column_count=1))
    assert r['columns'][0]['column']==10 and r['columns'][0]['data_type']=='Double'
    assert r['next_start']==2 and r['total_columns']==3


def test_insert_error_survives_table_count_read_failure():
    b=Backend()
    class BadTable(Table):
        @property
        def NumberOfOperands(self):
            if getattr(self,'broken',False):raise RuntimeError('count unavailable')
            return len(self.rows)
        def InsertNewOperandAt(self,index):
            self.broken=True
            raise RuntimeError('original insert error')
    b.table=BadTable();b.system.TDE=b.table
    with pytest.raises(ZemaxError)as err:b.insert_editor_rows(EditorInsert(editor='TDE',at=1))
    assert err.value.details['cause']['message']=='original insert error'
    assert err.value.details['state_unavailable']=='count unavailable'
