"""TDE edits preserve sparse updates, numbering, adoption and failure causes."""
from types import SimpleNamespace as N
import pytest
from pydantic import ValidationError
from zemax_mcp.errors import ZemaxError
from zemax_mcp.tolerance_models import TolerancePatch,ToleranceRange
from zemax_mcp.tolerance_editor import edit_tolerances,read_tolerances

class Row:
    def __init__(self,owner,kind='TOFF'):
        self.owner=owner;self.IsActive=True;self.reject=None;self.read_failure=False
        self.ChangeType(kind)
    def AvailableOperandTypes(self):return ['TOFF','TTHI','TRAD','SEED']
    @property
    def OperandNumber(self):return self.owner.rows.index(self)+1
    @property
    def TypeName(self):return self.Type
    def ChangeType(self,kind):
        self.Type=kind
        self.Param1=self.Param2=self.Param3=0;self.Min=self.Max=self.Nominal=0.
        self.Comment='';self.IgnoreThisOperandDuringTolerancing=False;self.DoNotAdjustDuringInverseTolerancing=False
        for name in ('Param1','Param2','Param3','Min','Max','Nominal','Comment'):
            active=name=='Comment'or kind in ('TTHI','TRAD')and name in ('Param1','Param2','Min','Max','Nominal')or kind=='SEED'and name=='Param1'
            setattr(self,name+'Cell',N(IsActive=active,IsReadOnly=name=='Nominal',DataType='Integer'if name.startswith('Param')else 'String'if name=='Comment'else'Double',Header=name))
            if name!='Comment':setattr(self,'Is'+name+'Used',active)
        return True
    def __setattr__(self,name,value):
        if name==getattr(self,'reject',None):return
        if name=='Max'and getattr(self,'explode',False):raise RuntimeError('native maximum setter failed')
        object.__setattr__(self,name,value)

class Table:
    def __init__(self):self.rows=[];self.fail_at=None;self.fail_read=False;self.deleted=[]
    @property
    def NumberOfOperands(self):return len(self.rows)
    def GetOperandAt(self,index):
        if self.fail_read:raise RuntimeError('state read failure')
        return self.rows[index-1]
    def AddOperand(self):
        row=Row(self)
        if self.fail_at==len(self.rows)+1:row.explode=True
        if getattr(self,'reject_field',None):row.reject=self.reject_field
        self.rows.append(row);return row
    def InsertNewOperandAt(self,index):
        row=Row(self);self.rows.insert(index-1,row);return row
    def RemoveOperandsAt(self,index,count):
        self.deleted.append(index);n=min(count,len(self.rows)-index+1);del self.rows[index-1:index-1+count]
        if not self.rows:self.AddOperand()
        return n

def backend():
    table=Table();b=N(system=N(TDE=table),last_checkpoint='baseline.zos',revision=0)
    b._require_sequential=lambda:None
    def mutate(_):b.revision+=1
    b._mutate=mutate
    def enum(_,name):
        if name not in ['TOFF','TTHI','TRAD','SEED']:raise ZemaxError('INVALID_ENUM','bad enum',name=name)
        return name
    b.native=N(enum=enum,api=N(Editors=N(TDE=N(ToleranceOperandType=N()))))
    return b

def edit(b,**args):return edit_tolerances(b,TolerancePatch(**args))

def seed(b,n=3):
    return edit(b,mode='replace',operands=[dict(type='TTHI',param1=i,param2=i+1,minimum=-.01,maximum=.01,comment=f'row{i}',ignore=True)for i in range(1,n+1)])

@pytest.mark.parametrize('args',[
 dict(mode='update',updates=[]),dict(mode='update',updates=[dict(operand=1)]),
 dict(mode='update',updates=[dict(operand=1,comment=None)]),
 dict(mode='update',updates=[dict(operand=1,param1=1.5)]),dict(mode='update',updates=[dict(operand=1,param1=True)]),
 dict(mode='update',updates=[dict(operand=1,param1=2147483648)]),
 dict(mode='update',updates=[dict(operand=1,minimum=float('nan'))]),
 dict(mode='delete',operand_numbers=[1,1]),dict(mode='delete',operand_numbers=[0]),
 dict(mode='insert',operands=[dict(type='TTHI')]),
 dict(mode='append',at=1,operands=[dict(type='TTHI')]),
 dict(mode='update',updates=[dict(operand=1,comment='x')],operands=[dict(type='TOFF')]),
 dict(mode='update',updates=[dict(operand=1,comment='x'),dict(operand=1,ignore=True)]),
 dict(mode='replace',operands=[]),dict(mode='delete',operand_numbers=[]),
 dict(mode='append',operands=[dict(type='TTHI',param1=1.2)])])
def test_reject_ambiguous_or_invalid_edits(args):
    with pytest.raises(ValidationError):TolerancePatch(**args)

@pytest.mark.parametrize('mode',['replace','append'])
def test_existing_modes_preserved(mode):
    b=backend();seed(b,1);r=edit(b,mode=mode,operands=[dict(type='TRAD',param1=2,minimum=-.1,maximum=.1)])
    assert r['total']==(1 if mode=='replace'else 2)
    assert r['rows'][-1]['type']=='TRAD'

def test_sparse_update_preserves_unmentioned_values():
    b=backend();seed(b);before=read_tolerances(b,None)['rows'][1]
    result=edit(b,mode='update',updates=[dict(operand=2,maximum=.5)])
    assert result['rows'][1]==dict(before,maximum=.5)
    assert result['edit']['completed_operands']==[2]

def test_type_change_preserves_shared_fields_and_flags():
    b=backend();seed(b,1)
    r=edit(b,mode='update',updates=[dict(operand=1,type='TRAD',maximum=.5)])['rows'][0]
    assert (r['type'],r['parameters'],r['minimum'],r['maximum'],r['comment'],r['ignore'])==('TRAD',{1:1,2:2},-.01,.5,'row1',True)

def test_insert_keeps_order_and_returns_shifted_rows():
    b=backend();seed(b)
    r=edit(b,mode='insert',at=2,operands=[dict(type='SEED',param1=42,comment='a'),dict(type='SEED',param1=43,comment='b')])
    assert [x['comment']for x in r['rows']]==['row1','a','b','row2','row3']
    assert r['edit']['completed_operands']==[2,3]

def test_delete_original_numbers_descending():
    b=backend();seed(b,5);r=edit(b,mode='delete',operand_numbers=[2,4])
    assert [x['comment']for x in r['rows']]==['row1','row3','row5']
    assert b.system.TDE.deleted[-2:]==[4,2]

def test_delete_all_keeps_native_blank_placeholder():
    b=backend();seed(b,2);r=edit(b,mode='delete',operand_numbers=[1,2])
    assert r['edit']['placeholder_retained']and r['rows'][0]['type']=='TOFF'

@pytest.mark.parametrize('args',[dict(mode='update',updates=[dict(operand=4,comment='x')]),dict(mode='delete',operand_numbers=[4]),dict(mode='insert',at=5,operands=[dict(type='TRAD')])])
def test_index_errors_before_mutation(args):
    b=backend();seed(b);revision=b.revision
    with pytest.raises(ZemaxError)as err:edit(b,**args)
    assert err.value.code=='INDEX_OUT_OF_RANGE'and b.revision==revision

def test_inactive_field_preflight_preserves_revision():
    b=backend();edit(b,mode='replace',operands=[dict(type='SEED',param1=42)]);revision=b.revision
    with pytest.raises(ZemaxError)as err:edit(b,mode='update',updates=[dict(operand=1,minimum=.1)])
    assert err.value.code=='CELL_NOT_WRITABLE'and b.revision==revision

def test_silent_field_rejection_is_partial_failure_with_state():
    b=backend();seed(b,1);b.system.TDE.rows[0].reject='Max'
    with pytest.raises(ZemaxError)as err:edit(b,mode='update',updates=[dict(operand=1,maximum=.5)])
    assert err.value.code=='PARTIAL_UPDATE'
    d=err.value.details
    assert d['cause']['code']=='SETTING_REJECTED'and d['failed_operand_state']['maximum']==.01
    assert d['checkpoint']=='baseline.zos'and d['current_revision']==2

def test_partial_batch_retains_completed_row_and_failure_cause():
    b=backend();seed(b);b.system.TDE.rows[1].explode=True
    with pytest.raises(ZemaxError)as err:edit(b,mode='update',updates=[dict(operand=1,maximum=.2),dict(operand=2,maximum=.3)])
    d=err.value.details
    assert d['completed_operands']==[1]and d['failed_operand']==2
    assert d['cause']['details']['native_reason']=='native maximum setter failed'
    assert b.system.TDE.rows[0].Max==.2

def test_failed_state_read_does_not_replace_original_error():
    b=backend();seed(b,1);row=b.system.TDE.rows[0]
    def bad(*_):
        b.system.TDE.fail_read=True;raise RuntimeError('original change error')
    row.ChangeType=bad
    with pytest.raises(ZemaxError)as err:edit(b,mode='update',updates=[dict(operand=1,type='TRAD')])
    d=err.value.details
    assert d['cause']['message']=='original change error'
    assert d['failed_operand_state']['state_unavailable']=='state read failure'

def test_metadata_and_pagination():
    b=backend();seed(b);r=read_tolerances(b,ToleranceRange(start=2,count=1,include_metadata=True))
    assert r['next_start']==3 and r['rows'][0]['operand']==2
    m=r['rows'][0]['metadata'];assert m['available_types']==['TOFF','TTHI','TRAD','SEED']
    assert m['columns']['minimum']['data_type']=='Double'and m['columns']['nominal']['read_only']
    assert read_tolerances(b,ToleranceRange(start=9))['rows']==[]
