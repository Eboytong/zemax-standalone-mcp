"""Public installed editor interfaces owned by the existing sequential worker."""
from .errors import ZemaxError
from .files import input_path,output_path

EDITOR_ENUMS={'MFE':('MFE','MeritOperandType'),'MCE':('MCE','MultiConfigOperandType'),'TDE':('TDE','ToleranceOperandType')}


def get_table(backend,editor):
    backend._require_sequential()
    return getattr(backend.system,editor)


def check_index(table,index,insert=False):
    total=int(table.NumberOfOperands)
    if not 1<=index<=total+int(insert):
        raise ZemaxError('INDEX_OUT_OF_RANGE','编辑器行编号超出范围。',operand=index,total=total,insertion=insert)


def cell_data(backend,cell,column,name):
    return dict(column=column,name=name,active=bool(cell.IsActive),read_only=bool(cell.IsReadOnly),
        data_type=str(cell.DataType),header=str(cell.Header),
        value=backend._cell_value(cell)if cell.IsActive else None)


def editor_rows(backend,editor,start,count):
    from .models import MeritRange
    from .configuration_models import ConfigurationRange
    from .tolerance_models import ToleranceRange
    if editor=='MFE':return backend.get_merit_function(MeritRange(start=start,count=min(count,200)))
    if editor=='MCE':return backend.get_configurations(ConfigurationRange(start=start,count=count))
    return backend.get_tolerances(ToleranceRange(start=start,count=count,include_metadata=True))


def table_state(table):
    try:return dict(total_after=int(table.NumberOfOperands))
    except Exception as exc:return dict(state_unavailable=str(exc))


class EditorsMixin:
    def get_editor_metadata(self,req):
        table=get_table(self,req.editor);check_index(table,req.operand)
        row=table.GetOperandAt(req.operand);columns=[]
        if req.editor=='MCE':
            types=row.AvailableConfigOperandTypes()
            for j in range(1,int(table.NumberOfConfigurations)+1):
                columns.append(cell_data(self,row.GetOperandCell(j),j,'configuration_'+str(j)))
            parameters={str(j):dict(enabled=bool(getattr(row,f'Param{j}Enabled')),value=int(getattr(row,f'Param{j}')))for j in range(1,4)}
        else:
            types=row.AvailableOperandTypes();parameters=None
            enum=self.native.api.Editors.MFE.MeritColumn if req.editor=='MFE'else self.native.api.Editors.TDE.ToleranceColumn
            for name in self.native.enum_names(enum):
                value=self.native.enum(enum,name)
                columns.append(cell_data(self,row.GetOperandCell(value),int(value),name))
        end=min(len(columns),req.column_start+req.column_count)
        return dict(editor=req.editor,total_operands=int(table.NumberOfOperands),operand=req.operand,
            type=str(row.Type),type_name=str(row.TypeName),active=bool(row.IsActive),
            available_operand_types=[str(x)for x in types],columns=columns[req.column_start:end],
            total_columns=len(columns),next_start=end if end<len(columns)else None,parameters=parameters,
            numbering='operand从1开始；column_start为元数据列表的0基偏移；column为原生列号或配置号。',
            file_operations={'MFE':['load_merit_function','save_merit_function'],
                'TDE':['load_tolerance_file','save_tolerance_file'],
                'MCE':[]}[req.editor],
            file_operation_source='本机IToleranceDataEditor/IMeritFunctionEditor/IMultiConfigEditor公开方法；MCE随完整系统保存和加载。')

    def insert_editor_rows(self,req):
        table=get_table(self,req.editor);check_index(table,req.at,True)
        before=int(table.NumberOfOperands);kind=None
        if req.operand_type is not None:
            namespace,enum_name=EDITOR_ENUMS[req.editor]
            kind=self.native.enum(getattr(getattr(self.native.api.Editors,namespace),enum_name),req.operand_type)
            if before:
                row=table.GetOperandAt(1)
                available=row.AvailableConfigOperandTypes()if req.editor=='MCE'else row.AvailableOperandTypes()
                if kind not in list(available):
                    raise ZemaxError('UNSUPPORTED_OPERAND','编辑器不支持请求的操作数。',editor=req.editor,operand_type=req.operand_type)
        self._mutate('editor_insert');completed=[];index=req.at
        try:
            for index in range(req.at,req.at+req.count):
                row=table.InsertNewOperandAt(index)
                if row is None or int(row.OperandNumber)!=index:
                    raise ZemaxError('SETTING_REJECTED','原生未返回指定插入行。',operand=index)
                if kind is not None:
                    if not row.ChangeType(kind)or row.Type!=kind:
                        raise ZemaxError('SETTING_REJECTED','新行未采用请求的类型。',operand=index,requested=str(kind),actual=str(row.Type))
                completed.append(index)
            if int(table.NumberOfOperands)!=before+req.count:
                raise ZemaxError('SETTING_REJECTED','插入后的行数不符。',expected=before+req.count,actual=int(table.NumberOfOperands))
            if kind is not None:
                for index in completed:
                    if table.GetOperandAt(index).Type!=kind:
                        raise ZemaxError('SETTING_REJECTED','插入行类型最终回读不符。',operand=index,requested=str(kind),actual=str(table.GetOperandAt(index).Type))
            return dict(editor=req.editor,completed_operands=completed,total_before=before,total_after=int(table.NumberOfOperands),
                result=editor_rows(self,req.editor,req.at,req.count),next_action='使用对应编辑器的有类型修改入口设置新行参数。')
        except Exception as exc:
            raise ZemaxError('PARTIAL_UPDATE','编辑器插入未完成。',editor=req.editor,completed_operands=completed,failed_operand=index,
                total_before=before,**table_state(table),checkpoint=self.last_checkpoint,current_revision=self.revision,
                cause=exc.as_dict()if isinstance(exc,ZemaxError)else dict(code='NATIVE_ERROR',message=str(exc)))from exc

    def copy_editor_rows(self,req):
        table=get_table(self,req.editor);check_index(table,req.start);check_index(table,req.start+req.count-1);check_index(table,req.at,True)
        before=int(table.NumberOfOperands)
        types=[str(table.GetOperandAt(i).Type)for i in range(req.start,req.start+req.count)]
        self._mutate('editor_copy');copied=None
        try:
            copied=int(table.CopyOperands(req.start,req.count,req.at))
            if copied!=req.count or int(table.NumberOfOperands)!=before+req.count:
                raise ZemaxError('SETTING_REJECTED','编辑器复制数量或最终行数不符。',requested=req.count,copied=copied,total_before=before,total_after=int(table.NumberOfOperands))
            actual=[str(table.GetOperandAt(i).Type)for i in range(req.at,req.at+req.count)]
            if types!=actual:
                raise ZemaxError('SETTING_REJECTED','复制目标的操作数类型与源不符。',requested=types,actual=actual)
            return dict(editor=req.editor,start=req.start,at=req.at,copied=copied,total_before=before,total_after=int(table.NumberOfOperands),
                result=editor_rows(self,req.editor,req.at,req.count),relations='引用重编号由原生CopyOperands处理；结果返回实际关系。')
        except Exception as exc:
            raise ZemaxError('PARTIAL_UPDATE','编辑器复制未完成。',editor=req.editor,copied=copied,total_before=before,
                **table_state(table),checkpoint=self.last_checkpoint,current_revision=self.revision,
                cause=exc.as_dict()if isinstance(exc,ZemaxError)else dict(code='NATIVE_ERROR',message=str(exc)))from exc

    def save_tolerance_file(self,req):
        table=get_table(self,'TDE');self._require_work()
        path=output_path(req.path,{'.tol'},req.overwrite);path.parent.mkdir(parents=True,exist_ok=True)
        table.SaveToleranceFile(str(path))
        if not path.is_file():
            raise ZemaxError('EDITOR_SAVE_FAILED','原生未生成公差文件。',path=str(path))
        return dict(path=str(path),editor='TDE',total_operands=int(table.NumberOfOperands),artifacts=[dict(kind='tolerance_file',path=str(path))])

    def load_tolerance_file(self,req):
        table=get_table(self,'TDE');self._require_work();path=input_path(req.path,{'.tol'})
        self._mutate('tolerance_load')
        try:
            if not table.LoadToleranceFile(str(path)):
                raise ZemaxError('EDITOR_LOAD_FAILED','原生公差文件载入失败。',path=str(path))
            return dict(path=str(path),editor='TDE',tolerances=self.get_tolerances(None))
        except Exception as exc:
            raise ZemaxError('PARTIAL_UPDATE','公差文件载入或结果读取失败。',path=str(path),checkpoint=self.last_checkpoint,current_revision=self.revision,
                cause=exc.as_dict()if isinstance(exc,ZemaxError)else dict(code='NATIVE_ERROR',message=str(exc)))from exc
