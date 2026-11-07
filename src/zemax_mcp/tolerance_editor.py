"""Typed TDE row edits with final native adoption and partial-update evidence."""
from .errors import ZemaxError
from .detectors import check_setting_value

FIELDS={
    'param1':('Param1','IsParam1Used','Param1Cell'),
    'param2':('Param2','IsParam2Used','Param2Cell'),
    'param3':('Param3','IsParam3Used','Param3Cell'),
    'minimum':('Min','IsMinUsed','MinCell'),
    'maximum':('Max','IsMaxUsed','MaxCell'),
    'comment':('Comment',None,'CommentCell'),
    'ignore':('IgnoreThisOperandDuringTolerancing',None,None),
    'inverse_protected':('DoNotAdjustDuringInverseTolerancing',None,None),
}


def row_data(row,index,metadata=False):
    result=dict(operand=index,type=str(row.Type),
        parameters={j:int(getattr(row,f'Param{j}')) for j in range(1,4) if getattr(row,f'IsParam{j}Used')},
        minimum=float(row.Min) if row.IsMinUsed else None,
        maximum=float(row.Max) if row.IsMaxUsed else None,
        nominal=float(row.Nominal) if row.IsNominalUsed else None,
        comment=str(row.Comment),ignore=bool(row.IgnoreThisOperandDuringTolerancing),
        inverse_protected=bool(row.DoNotAdjustDuringInverseTolerancing))
    if metadata:
        columns={}
        for key,(_,enabled,cell_name) in FIELDS.items():
            if cell_name is None:
                continue
            cell=getattr(row,cell_name)
            columns[key]=dict(active=bool(getattr(row,enabled))if enabled else bool(cell.IsActive),
                read_only=bool(cell.IsReadOnly),data_type=str(cell.DataType),header=str(cell.Header))
        cell=row.NominalCell
        columns['nominal']=dict(active=bool(row.IsNominalUsed),read_only=bool(cell.IsReadOnly),data_type=str(cell.DataType),header=str(cell.Header))
        result['metadata']=dict(active=bool(row.IsActive),type_name=str(row.TypeName),
            available_types=[str(x)for x in row.AvailableOperandTypes()],columns=columns)
    return result


def read_tolerances(backend,req):
    backend._require_sequential();table=backend.system.TDE
    start=req.start if req else 1;count=req.count if req else 200
    end=min(int(table.NumberOfOperands)+1,start+count)
    return dict(rows=[row_data(table.GetOperandAt(i),i,bool(req and req.include_metadata))for i in range(start,end)],
        total=int(table.NumberOfOperands),next_start=end if end<=table.NumberOfOperands else None,
        units='按各公差操作数定义；长度、角度与 fringes 分别解释。')


def check_fields(row,values):
    for key in values:
        if key not in FIELDS:
            continue
        _,enabled,cell_name=FIELDS[key]
        if enabled and not getattr(row,enabled):
            raise ZemaxError('CELL_NOT_WRITABLE','公差字段未启用。',field=key,type=str(row.Type))
        if cell_name:
            cell=getattr(row,cell_name)
            if not cell.IsActive or cell.IsReadOnly:
                raise ZemaxError('CELL_NOT_WRITABLE','公差单元格未激活或只读。',field=key,type=str(row.Type))


def apply_fields(row,values,kind,preserve=False):
    if kind is not None and row.Type!=kind:
        previous={key:getattr(row,attr)for key,(attr,enabled,_)in FIELDS.items()
            if preserve and key not in values and (enabled is None or getattr(row,enabled))}
        if not row.ChangeType(kind):
            raise ZemaxError('OPERAND_UPDATE_FAILED','公差类型设置失败。',requested=str(kind),actual=str(row.Type))
        if row.Type!=kind:
            raise ZemaxError('SETTING_REJECTED','原生未采用公差类型。',setting='type',requested=str(kind),actual=str(row.Type))
        for key,value in previous.items():
            _,enabled,cell_name=FIELDS[key]
            if (enabled is None or getattr(row,enabled))and (cell_name is None or (getattr(row,cell_name).IsActive and not getattr(row,cell_name).IsReadOnly)):
                values[key]=value
    check_fields(row,values)
    for key,value in values.items():
        if key in FIELDS:
            try:setattr(row,FIELDS[key][0],value)
            except Exception as exc:
                raise ZemaxError('OPERAND_UPDATE_FAILED','公差字段写入失败。',field=key,type=str(row.Type),native_reason=str(exc))from exc


def verify_fields(row,values,kind):
    if kind is not None and row.Type!=kind:
        raise ZemaxError('SETTING_REJECTED','公差类型最终回读不符。',setting='type',requested=str(kind),actual=str(row.Type))
    check_fields(row,values)
    for key,value in values.items():
        if key in FIELDS:
            check_setting_value('tolerance.'+key,value,getattr(row,FIELDS[key][0]))


def failure_state(table,index):
    try:
        if index is not None and 1<=index<=table.NumberOfOperands:
            return row_data(table.GetOperandAt(index),index)
        return dict(operand=index,total=int(table.NumberOfOperands))
    except Exception as exc:
        return dict(operand=index,state_unavailable=str(exc))


def edit_tolerances(backend,req):
    backend._require_sequential();table=backend.system.TDE
    count=int(table.NumberOfOperands);plans=[]
    if req.mode=='insert' and req.at>count+1:
        raise ZemaxError('INDEX_OUT_OF_RANGE','插入位置超出TDE范围。',at=req.at,total=count)
    if req.mode in {'update','delete'}:
        indices=[p.operand for p in req.updates]if req.mode=='update'else req.operand_numbers
        for index in indices:
            if index>count:
                raise ZemaxError('INDEX_OUT_OF_RANGE','公差行编号超出范围。',operand=index,total=count)
    entries=req.updates if req.mode=='update'else req.operands
    for p in entries:
        values=p.model_dump(exclude_unset=True) if req.mode=='update'else p.model_dump(exclude_none=True)
        values.pop('operand',None)
        name=values.get('type')
        kind=backend.native.enum(backend.native.api.Editors.TDE.ToleranceOperandType,name)if name else None
        if req.mode=='update':
            row=table.GetOperandAt(p.operand)
            if kind is not None and kind not in list(row.AvailableOperandTypes()):
                raise ZemaxError('INVALID_ENUM','此TDE不提供请求的操作数类型。',type=name,operand=p.operand)
            if kind is None or row.Type==kind:
                check_fields(row,values)
        plans.append((p,values,kind))
    backend._mutate('tolerances')
    completed=[];adopted=[];failed=None;operation=0
    try:
        if req.mode=='replace' and count:
            removed=table.RemoveOperandsAt(1,count)
            placeholder=table.NumberOfOperands==1 and str(table.GetOperandAt(1).Type)=='TOFF'
            if removed!=count and not placeholder:
                raise ZemaxError('OPERAND_UPDATE_FAILED','公差表删除数量不符。',removed=removed,expected=count,remaining=int(table.NumberOfOperands))
        if req.mode=='delete':
            for operation,failed in enumerate(sorted(req.operand_numbers,reverse=True),1):
                before=int(table.NumberOfOperands)
                removed=table.RemoveOperandsAt(failed,1)
                after=int(table.NumberOfOperands)
                placeholder=before==after==1 and str(table.GetOperandAt(1).Type)=='TOFF'
                if (removed!=1 or after!=before-1)and not placeholder:
                    raise ZemaxError('OPERAND_UPDATE_FAILED','公差行删除未采用。',operand=failed,removed=removed,before=before,after=after)
                completed.append(failed)
        else:
            for operation,(p,values,kind)in enumerate(plans,1):
                if req.mode=='update':
                    failed=p.operand;row=table.GetOperandAt(failed)
                elif req.mode=='replace'and operation==1 and table.NumberOfOperands==1 and str(table.GetOperandAt(1).Type)=='TOFF':
                    failed=1;row=table.GetOperandAt(1)
                elif req.mode=='insert':
                    failed=req.at+operation-1;row=table.InsertNewOperandAt(failed)
                else:
                    failed=int(table.NumberOfOperands)+1;row=table.AddOperand()
                if row is None:
                    raise ZemaxError('OPERAND_UPDATE_FAILED','原生未返回公差行。',operand=failed)
                if int(row.OperandNumber)!=failed:
                    raise ZemaxError('SETTING_REJECTED','原生返回的公差行编号不符。',requested=failed,actual=int(row.OperandNumber))
                apply_fields(row,values,kind,preserve=req.mode=='update')
                verify_fields(row,values,kind)
                adopted.append((failed,values,kind));completed.append(failed)
            for failed,values,kind in adopted:
                verify_fields(table.GetOperandAt(failed),values,kind)
        result=read_tolerances(backend,None)
    except Exception as exc:
        cause=exc.as_dict()if isinstance(exc,ZemaxError)else dict(code='NATIVE_ERROR',message=str(exc))
        raise ZemaxError('PARTIAL_UPDATE','公差编辑未完成。',mode=req.mode,completed_operands=completed,
            operation_index=operation,failed_operand=failed,failed_operand_state=failure_state(table,failed),
            checkpoint=backend.last_checkpoint,current_revision=backend.revision,cause=cause)from exc
    result['edit']=dict(mode=req.mode,completed_operands=completed,total_before=count,total_after=int(table.NumberOfOperands),
        numbering='delete编号基于修改前；按降序删除。insert按输入顺序连续插入。',
        placeholder_retained=table.NumberOfOperands==1 and str(table.GetOperandAt(1).Type)=='TOFF')
    return result
