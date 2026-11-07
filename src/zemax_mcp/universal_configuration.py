"""Typed numeric multi-configuration axes and native row identity."""
import re,math
from .errors import ZemaxError
from .universal_surface import parameter_unit


def resolve(source,q):
    m=source.MCE
    if q.configuration>int(m.NumberOfConfigurations)or q.operand_row>int(m.NumberOfOperands):raise ZemaxError('INDEX_OUT_OF_RANGE','Universal Plot MCE行或配置编号越界。',configuration=q.configuration,operand_row=q.operand_row)
    row=m.GetOperandAt(q.operand_row);cell=row.GetOperandCell(q.configuration);kind=str(row.Type)
    expected=q.mce_operand if q.parameter=='ConfigurationValue'else q.parameter
    if kind!=expected:raise ZemaxError('INVALID_ARGUMENT','Universal Plot MCE类型与请求不符。',requested=expected,actual=kind)
    if not cell.IsActive or cell.IsReadOnly or str(cell.Solve)not in {'Fixed','Variable'}:raise ZemaxError('INACTIVE_SETTING','Universal Plot MCE扫描单元格须活动、可写且无拾取求解。',solve=str(cell.Solve))
    dtype=str(cell.DataType)
    if dtype not in {'Integer','Double'}:raise ZemaxError('UNSUPPORTED_SETTING','Universal MCE轴需要数值单元格。',operand_type=kind,data_type=dtype)
    if dtype=='Integer'and(not float(q.start).is_integer()or not float(q.stop).is_integer()or not((q.stop-q.start)/(q.samples-1)).is_integer()):raise ZemaxError('INVALID_ARGUMENT','Universal MCE整数参数的全部采样点必须为整数。')
    if kind=='TEMP'and q.start<=-273.15:raise ZemaxError('INVALID_ARGUMENT','MCE温度须高于绝对零度。')
    if kind=='PRES'and q.start<0:raise ZemaxError('INVALID_ARGUMENT','MCE压力须为非负。')
    if kind=='WAVE'and q.start<=0:raise ZemaxError('INVALID_ARGUMENT','MCE波长须为正。')
    native_parameters=[int(getattr(row,'Param'+str(i)))for i in range(1,4)if getattr(row,'Param'+str(i)+'Enabled')]
    parameters=list(native_parameters)
    if kind in {'WAVE','XFIE','YFIE'}:
        count=int(source.SystemData.Wavelengths.NumberOfWavelengths)if kind=='WAVE'else int(source.SystemData.Fields.NumberOfFields)
        if not 0<=int(row.Param1)<count:raise ZemaxError('INDEX_OUT_OF_RANGE','MCE原生波长/视场索引越界。',operand_type=kind,native_index=int(row.Param1),count=count)
        if parameters:parameters[0]+=1
    lens_unit=str(source.SystemData.Units.LensUnits)
    unit={'THIC':lens_unit,'CRVT':'1/'+lens_unit,'CONN':'dimensionless','TCEX':'ppm/Celsius','TEMP':'Celsius','PRES':'atmospheres','WAVE':'micrometers'}.get(kind)
    surface=int(row.Param1)if kind in {'THIC','CRVT','CONN','PRAM','TCEX'}else None
    physical={'THIC':'Thickness','CRVT':'Curvature','CONN':'Conic','TCEX':'TCE','PRAM':'SurfaceParameter:'+str(int(row.Param2))if kind=='PRAM'else None}.get(kind)
    identity=('Surface',q.configuration,surface,physical)if surface is not None else('MCE',q.configuration,kind,tuple(parameters))
    if kind=='PRAM':unit=parameter_unit(source.LDE.GetSurfaceAt(surface),int(row.Param2),lens_unit)
    system_kind={'TEMP':'Temperature','PRES':'Pressure','WAVE':'Wavelength','XFIE':'XField','YFIE':'YField'}.get(kind)
    if system_kind:
        identity=('System',q.configuration,system_kind,int(row.Param1)+1 if kind in {'WAVE','XFIE','YFIE'}else None)
        if kind in {'XFIE','YFIE'}:
            field_type=str(source.SystemData.Fields.GetFieldType())
            if field_type=='ObjectHeight'and not math.isfinite(float(source.LDE.GetSurfaceAt(0).Thickness)):raise ZemaxError('INVALID_MODEL','MCE ObjectHeight扫描需要有限物距。')
            unit='degrees'if 'Angle'in field_type else lens_unit if 'Height'in field_type else None
    return dict(category_index=2,native_parameter_index=q.operand_row,native_surface=q.configuration,
        unit=unit,unit_source='native MCE/property definition'if unit else'physical unit not exposed by native MCE metadata',
        configuration_operand=kind,operand_parameters=parameters,native_operand_parameters=native_parameters,parameter_data_type=dtype,
        controlled_surface=surface,physical_parameter=physical,physical_identity=identity,selected_configuration=q.configuration)


def verify(axis,q,resolved=None):
    kind=q.mce_operand if q.parameter=='ConfigurationValue'else q.parameter
    match=re.search(r'[:：]\s*'+str(q.operand_row)+r'\s*[:：]\s*'+re.escape(kind)+r'\b(.*)$',axis,re.I)
    if not match:raise ZemaxError('SETTING_REJECTED','Universal Plot MCE行或类型未采用。',native_axis=axis)
    if resolved is not None:
        actual=[int(v)for v in re.findall(r'[-+]?\d+',match[1])]
        if actual!=resolved['operand_parameters']:raise ZemaxError('SETTING_REJECTED','Universal Plot MCE行参数未采用。',native_axis=axis,expected=resolved['operand_parameters'],actual=actual)
    elif q.parameter=='ConfigurationValue':raise ZemaxError('SETTING_UNCONFIRMED','Universal MCE通用轴缺少原生行参数回读。')
