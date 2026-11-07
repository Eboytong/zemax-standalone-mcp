"""Universal dependent targets, formal operand metadata and native identity."""
import math,re
from typing import Annotated,Literal
from pydantic import Field
from .schema import Request,Index,FiniteFloat
from .errors import ZemaxError


class OperandTarget(Request):
    mode: Literal['operand']
    operand: Annotated[str,Field(pattern=r'^[A-Z0-9]{4}$')]
    parameters: Annotated[list[FiniteFloat],Field(max_length=8)]=Field(default_factory=list)


class MeritTarget(Request):
    mode: Literal['merit']
    line: Index=0


UniversalTarget=Annotated[OperandTarget|MeritTarget,Field(discriminator='mode')]


def validate_request(q):
    if q.target is not None:
        if q.operand!='TTHI'or q.first_surface is not None or q.last_surface is not None:raise ValueError('target requires omission of legacy operand/first_surface/last_surface.')
    else:
        axes=[q]if hasattr(q,'category')else[q.x,q.y]
        if any(axis.category=='NSC'for axis in axes):raise ValueError('NSC axes require an explicit operand or merit target.')
        if q.first_surface is None:raise ValueError('Legacy operand requires first_surface.')
        if q.operand=='TTHI'and(q.last_surface is None or q.last_surface<q.first_surface):raise ValueError('TTHI requires an increasing surface range.')
        if q.operand=='CVVA'and q.last_surface is not None:raise ValueError('CVVA uses first_surface only; omit last_surface.')
    return q


def operand_unit(name,lens_unit):
    if name=='CVVA':return '1/'+lens_unit
    if name=='COVA':return 'dimensionless'
    if name=='TCVA':return 'ppm/Celsius'
    if name in {'TTHI','REAX','REAY','NPXV','NPYV','NPZV'}:return lens_unit
    if name in {'NTXV','NTYV','NTZV'}:return 'degrees'
    if name in {'RSCE','RSCH','RSRE','RSRH'}:return lens_unit
    if name in {'RWCE','RWCH','RWRE','RWRH'}:return 'waves'
    return None


def resolve(backend,q):
    unit=str(backend.system.SystemData.Units.LensUnits)
    if q.target is None:
        return dict(operand=q.operand,line=0,parameters=[q.first_surface,q.last_surface if q.operand=='TTHI'else 0]+[0]*6,
                    label=q.operand,unit=operand_unit(q.operand,unit),unit_source='native operand definition')
    target=q.target
    if target.mode=='merit':
        m=backend.system.MFE
        if target.line>int(m.NumberOfOperands):raise ZemaxError('INDEX_OUT_OF_RANGE','Universal Plot评价函数行号越界。',line=target.line,count=int(m.NumberOfOperands))
        name=str(m.GetOperandAt(target.line).Type)if target.line else None
        configurations=[dict(line=i,configuration=int(m.GetOperandAt(i).GetCellAt(2).IntegerValue))for i in range(1,int(m.NumberOfOperands)+1)if str(m.GetOperandAt(i).Type)=='CONF']
        return dict(operand='Merit',line=target.line,parameters=[0]*8,label='Merit'if not target.line else f'Merit line {target.line}: {name}',
                    line_operand=name,unit=operand_unit(name,unit),unit_source='selected native operand definition'if target.line else 'weighted native merit function; physical unit not exposed',
                    merit_configurations=configurations,configuration_scope='merit CONF directives'if configurations else'current configuration')
    kind=backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType,target.operand)
    values=target.parameters+[0.]*(8-len(target.parameters));copy=None;original=None
    try:
        copy=backend.system.CopySystem()
        if copy is None:raise ZemaxError('COPY_FAILED','Universal Plot操作数元数据副本创建失败。')
        row=copy.MFE.AddOperand()
        if row.ChangeType(kind)is False or str(row.Type)!=target.operand:raise ZemaxError('SETTING_REJECTED','Universal Plot操作数类型未采用。',operand=target.operand)
        active=[]
        for i,value in enumerate(values):
            cell=row.GetCellAt(i+2)
            if not cell.IsActive:
                if value!=0:raise ZemaxError('INACTIVE_SETTING','Universal Plot操作数参数未启用。',parameter=i+1,operand=target.operand)
                continue
            dtype=str(cell.DataType)
            if dtype not in {'Integer','Double'}:raise ZemaxError('UNSUPPORTED_SETTING','Universal Plot参数不是数值类型。',parameter=i+1,data_type=dtype)
            if dtype=='Integer'and value!=int(value):raise ZemaxError('INVALID_ARGUMENT','Universal Plot操作数整数参数包含小数。',parameter=i+1,value=value)
            if re.fullmatch(r'(?:Wave(?:length)?|波(?:长)?)\s*#?\s*\d*',str(cell.Header).strip(),re.I):
                count=int(backend.system.SystemData.Wavelengths.NumberOfWavelengths)
                if value!=int(value)or not 0<=value<=count:raise ZemaxError('INDEX_OUT_OF_RANGE','Universal操作数波长编号越界；原生可能静默回退。',parameter=i+1,wavelength=value,count=count)
            if re.fullmatch(r'(?:Field|Fld|视场|场)\s*#?\s*\d*',str(cell.Header).strip(),re.I):
                count=int(backend.system.SystemData.Fields.NumberOfFields)
                if value!=int(value)or not 0<=value<=count:raise ZemaxError('INDEX_OUT_OF_RANGE','Universal操作数视场编号越界。',parameter=i+1,field=value,count=count)
            if re.fullmatch(r'(?:Surf(?:ace)?|面|表面)\s*\d*',str(cell.Header),re.I):
                maximum=1 if str(getattr(backend.system,'Mode','Sequential'))=='NonSequential'else int(backend.system.LDE.NumberOfSurfaces)-1
                if value!=int(value)or not 0<=value<=maximum:raise ZemaxError('INDEX_OUT_OF_RANGE','Universal操作数曲面编号越界。',parameter=i+1,surface=value,maximum=maximum)
            active.append(dict(parameter=i+1,header=str(cell.Header),data_type=dtype,value=value))
        result_unit=operand_unit(target.operand,unit)
        if target.operand=='PMVA'and str(getattr(backend.system,'Mode','Sequential'))=='Sequential'and 0<=values[0]<int(copy.LDE.NumberOfSurfaces)and 1<=values[1]<=254:
            from .universal_surface import parameter_unit
            result_unit=parameter_unit(copy.LDE.GetSurfaceAt(int(values[0])),int(values[1]),unit)
        if target.operand=='NPVA':
            from .universal_nsc import parameter_unit
            pure=str(getattr(backend.system,'Mode','Sequential'))=='NonSequential'
            valid_group=values[0]==1 if pure else 0<values[0]<int(copy.LDE.NumberOfSurfaces)and str(copy.LDE.GetSurfaceAt(int(values[0])).Type)=='NonSequential'
            if valid_group:
                if not pure:
                    accepted=bool(copy.NCE.SetActiveSurface(int(values[0])))
                    if not accepted or int(copy.NCE.ActiveSurface)!=values[0]:raise ZemaxError('NSC_GROUP_SELECTION_FAILED','Universal NPVA元数据副本未采用目标组。',nsc_surface=values[0])
                if 1<=values[1]<=int(copy.NCE.NumberOfObjects):result_unit=parameter_unit(copy.NCE.GetObjectAt(int(values[1])),int(values[2]),unit)
        return dict(operand=target.operand,line=0,parameters=values,active_parameters=active,label=target.operand,
                    unit=result_unit,unit_source='native operand/object property definition'if result_unit else 'physical unit not exposed by native operand metadata')
    except Exception as exc:
        original=exc
        raise
    finally:
        if copy is not None:
            try:
                if copy.Close(False)is False:raise RuntimeError('Close(False) returned false')
            except Exception as exc:
                backend.requires_reconnect=True
                if original is not None:original.add_note('Universal operand metadata copy cleanup failed: '+str(exc))
                else:raise ZemaxError('CLEANUP_FAILED','Universal Plot操作数元数据副本关闭失败。',native_error=str(exc))from exc


NUMBER=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'


def check_report(text):
    if re.search(r'(操作数.*不能计算|operands?.*cannot\s+be\s+comput)',text,re.I):
        raise ZemaxError('ANALYSIS_FAILED','Universal Plot原生报告操作数不能计算。',error_source='native_report',native_report=text[:4000])


def verify(dependent,target,resolved=None):
    if target.mode=='merit':
        if not re.search(r'(评价函数|Merit(?: Function)?)',dependent,re.I):raise ZemaxError('SETTING_REJECTED','Universal Plot评价函数目标未采用。',native_dependent=dependent)
        line=re.search(r'(?:操作数|Operand|Line)\s*(\d+)',dependent,re.I)
        actual=int(line[1])if line else 0
        if actual!=target.line:raise ZemaxError('SETTING_REJECTED','Universal Plot评价函数行号未采用。',requested=target.line,actual=actual,native_dependent=dependent)
        if resolved and target.line and not re.search(r'\b'+re.escape(resolved['line_operand'])+r'\b',dependent):raise ZemaxError('SETTING_REJECTED','Universal Plot评价函数行类型未采用。',native_dependent=dependent)
        return
    if not re.search(r'\b'+target.operand+r'\b',dependent):raise ZemaxError('SETTING_REJECTED','Universal Plot操作数身份未采用。',native_dependent=dependent)
    if resolved is None:raise ZemaxError('SETTING_UNCONFIRMED','Universal Plot一般操作数缺少原生活动参数元数据。')
    actual=[float(x)for x in re.findall(r'=\s*('+NUMBER+r')',dependent)]
    expected=[p['value']for p in resolved['active_parameters']]
    if len(actual)!=len(expected)or any(not math.isclose(a,b,rel_tol=5e-7,abs_tol=5e-7)for a,b in zip(actual,expected)):
        raise ZemaxError('SETTING_REJECTED','Universal Plot操作数活动参数未采用。',expected=expected,actual=actual,native_dependent=dependent)
