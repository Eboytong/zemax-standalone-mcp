"""Universal Plot CFG execution and explicit native text readback."""
import math,re
from uuid import uuid4
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .schema import Request,PositiveIndex,FiniteFloat
from .errors import ZemaxError
from .data import unwrap
from .imaging import new_analysis
from .coatings import CoatingWavelengthAnalysis
from . import universal_targets as targets
from . import universal_nsc as nsc
from . import universal_surface as surface_axis
from . import universal_configuration as configuration_axis


class UniversalAxis(Request):
    category: Literal['Surface','System','Configuration','NSC']='Surface'
    surface: PositiveIndex | None = None
    parameter: Literal['Radius','Curvature','Thickness','Conic','TCE','SurfaceParameter','Aperture','ApodizationFactor','Temperature','Pressure','XField','YField','Wavelength','THIC','CRVT','ConfigurationValue','XPosition','YPosition','ZPosition','TiltX','TiltY','TiltZ','ObjectParameter']='Thickness'
    mce_operand: Annotated[str,Field(pattern=r'^[A-Z0-9]{4}$')] | None = Field(default=None,description='Expected installed MCE operand type; required only with ConfigurationValue. Cell must be active, numeric and writable.')
    object: PositiveIndex | None = None
    nsc_surface: PositiveIndex | None = Field(default=None,description='LDE NSC-component surface; required for mixed NSC axes, omitted in pure NSC.')
    parameter_number: Annotated[int,Field(strict=True,ge=1,le=254)] | None = Field(default=None,description='One-based SurfaceParameter1..254 or ObjectParameter1..250; omit for other parameters.')
    selection: PositiveIndex | None = Field(default=None,description='One-based field or wavelength number; required only for XField/YField/Wavelength.')
    configuration: PositiveIndex | None = None
    operand_row: PositiveIndex | None = Field(default=None,description='One-based MCE row; required for Configuration category.')
    start: FiniteFloat
    stop: FiniteFloat
    samples: Annotated[int,Field(strict=True,ge=2,le=1001)]=21
    @model_validator(mode='after')
    def bounds(self):
        if (self.category=='NSC')!=(self.object is not None):raise ValueError('NSC category requires object; other categories omit it.')
        if self.nsc_surface is not None and self.category!='NSC':raise ValueError('Only NSC category accepts nsc_surface.')
        if (self.category=='NSC')!=(self.parameter in nsc.POSITIONS or self.parameter=='ObjectParameter'):raise ValueError('NSC parameter must select an object position, tilt or ObjectParameter.')
        if (self.parameter in {'ObjectParameter','SurfaceParameter'})!=(self.parameter_number is not None):raise ValueError('ObjectParameter/SurfaceParameter requires parameter_number; other parameters omit it.')
        if self.parameter=='ObjectParameter'and self.parameter_number>250:raise ValueError('NSC parameter_number must not exceed250.')
        config=self.category=='Configuration'
        if config!=(self.configuration is not None)or config!=(self.operand_row is not None):raise ValueError('Configuration category requires configuration and operand_row; other categories omit them.')
        if config!=(self.parameter in {'THIC','CRVT','ConfigurationValue'}):raise ValueError('Configuration parameter must be THIC, CRVT or ConfigurationValue.')
        if (self.parameter=='ConfigurationValue')!=(self.mce_operand is not None):raise ValueError('Only ConfigurationValue requires mce_operand.')
        indexed=self.parameter in {'XField','YField','Wavelength'}
        if indexed!=(self.selection is not None):raise ValueError('selection is required only for XField/YField/Wavelength.')
        if self.parameter=='Wavelength'and self.start<=0:raise ValueError('Wavelength must be positive.')
        surface_parameter=self.parameter in {'Radius','Curvature','Thickness','Conic','TCE','SurfaceParameter'}
        if (self.category=='Surface')!=surface_parameter:raise ValueError('Parameter does not belong to the requested category.')
        if self.category=='Surface'and self.surface is None:raise ValueError('Surface category requires surface.')
        if self.category!='Surface'and self.surface is not None:raise ValueError('Only Surface category has a surface selector.')
        if self.parameter in {'Pressure','ApodizationFactor'}and self.start<0:raise ValueError('Pressure and apodization must be nonnegative.')
        if self.parameter=='Aperture'and self.start<=0:raise ValueError('Aperture must be positive.')
        if self.parameter=='Temperature'and self.start<=-273.15:raise ValueError('Temperature must exceed absolute zero.')
        if self.stop<=self.start:raise ValueError('stop must exceed start.')
        return self


class UniversalPlot1D(UniversalAxis):
    kind: Literal['universal_plot_1d']
    operand: Literal['TTHI','CVVA']='TTHI'
    first_surface: PositiveIndex | None = None
    last_surface: PositiveIndex | None = None
    target: targets.UniversalTarget | None = None
    @model_validator(mode='after')
    def dependent_bounds(self):
        return targets.validate_request(self)


def verify_identity(axis,dependent,q,target=None,resolved_axis=None):
    if not axis or not dependent:raise ZemaxError('SETTING_UNCONFIRMED','Universal Plot原生文本缺少变量身份。')
    if q.category=='NSC':nsc.verify(axis,q)
    label={'Thickness':r'(厚度|Thickness)','Radius':r'(半径|Radius)','Curvature':r'(曲率|Curvature)','Aperture':r'(系统孔径|System Aperture)','ApodizationFactor':r'(切趾因子|Apodization Factor)','Temperature':r'(温度|Temperature)','Pressure':r'(压力|Pressure)','XField':r'(X\s*视场|X\s*Field)','YField':r'(Y\s*视场|Y\s*Field)','Wavelength':r'(波长|Wavelength)','THIC':r'\bTHIC\b','CRVT':r'\bCRVT\b'}.get(q.parameter,'')
    if q.parameter=='Conic':label=r'(圆锥系数|Conic(?:\s+Constant)?)'
    if q.parameter=='TCE':label=r'TCE(?=\s*(?:表面|Surface))'
    if q.parameter=='SurfaceParameter':label=r'(?:参数|Parameter)\s*'+str(q.parameter_number)+r'(?=\s*(?:表面|Surface))'
    if q.category=='Configuration':configuration_axis.verify(axis,q,resolved_axis)
    if not re.search(label,axis,re.I)or (q.category=='Surface'and not re.search(r'(表面|Surface)\s*'+str(q.surface)+r'\s*$',axis,re.I)):
        raise ZemaxError('SETTING_REJECTED','Universal Plot扫描曲面/参数未采用。',native_axis=axis)
    if q.selection is not None and not re.search(label+r'\s*'+str(q.selection)+r'\s*$',axis,re.I):raise ZemaxError('SETTING_REJECTED','Universal Plot视场/波长编号未采用。',native_axis=axis,selection=q.selection)
    if q.target is not None:
        targets.verify(dependent,q.target,target)
        return
    expected=[q.first_surface,q.last_surface]if q.operand=='TTHI'else[q.first_surface]
    if not re.search(r'\b'+q.operand+r'\b',dependent)or [int(v)for v in re.findall(r'=\s*(\d+)',dependent)]!=expected:
        raise ZemaxError('SETTING_REJECTED','Universal Plot操作数参数未采用。',native_dependent=dependent)


def parse_curve(text,q,target=None,resolved_axis=None):
    targets.check_report(text)
    lines=text.splitlines();axis=next((line for line in lines if re.match(r'\s*(自变量|Independent Variable)\s*X\s*[:：]',line,re.I)),None)
    dependent=next((line for line in lines if re.match(r'\s*(因变量|Dependent Variable)\s*Y\s*[:：]',line,re.I)),None)
    verify_identity(axis,dependent,q,target,resolved_axis)
    rows=[];started=False
    for line in lines:
        if re.fullmatch(r'\s*X\s+Y\s*',line):started=True;continue
        if started and line.strip():
            try:row=list(map(float,line.split()))
            except ValueError as exc:raise ZemaxError('INVALID_RESULT_DATA','Universal Plot曲线格式错误。',native_line=line)from exc
            if len(row)!=2 or not all(math.isfinite(v)for v in row):raise ZemaxError('INVALID_RESULT_DATA','Universal Plot须返回两列有限数值。')
            rows.append(row)
    if len(rows)!=q.samples:raise ZemaxError('SETTING_REJECTED','Universal Plot采样数未采用。',requested=q.samples,actual=len(rows))
    for i,row in enumerate(rows):
        fraction=i/(q.samples-1);expected=(1-fraction)*q.start+fraction*q.stop
        if abs(row[0]-expected)>5e-7*max(1,abs(expected)):raise ZemaxError('SETTING_REJECTED','Universal Plot扫描坐标未采用。',index=i,requested=expected,actual=row[0])
    return rows,dict(axis=axis,dependent=dependent,samples=len(rows),start=rows[0][0],stop=rows[-1][0],source='native text identity and coordinates; six-digit scientific text precision')


def system_parameter_index(system,q):
    fields=int(system.SystemData.Fields.NumberOfFields);waves=int(system.SystemData.Wavelengths.NumberOfWavelengths)
    if q.selection is not None:
        count=waves if q.parameter=='Wavelength'else fields
        if q.selection>count:raise ZemaxError('INDEX_OUT_OF_RANGE','Universal Plot系统选择编号越界。',selection=q.selection,count=count)
    if q.parameter=='XField':return q.selection
    if q.parameter=='YField':return fields+q.selection
    if q.parameter=='Wavelength':return 2*fields+q.selection
    return {'Aperture':0,'ApodizationFactor':2*fields+waves+1,'Temperature':2*fields+waves+2,'Pressure':2*fields+waves+3}[q.parameter]


def resolve_axis(source,q,native=None):
    """Resolve the native selector and physical unit before opening an analysis."""
    if q.category=='NSC':return nsc.resolve(source,q,native)
    if q.category=='Surface'and q.parameter in {'Conic','TCE','SurfaceParameter'}:return surface_axis.resolve(source,q,native)
    if q.category=='Configuration':return configuration_axis.resolve(source,q)
    if q.parameter=='ApodizationFactor'and str(source.SystemData.Aperture.ApodizationType)=='Uniform':raise ZemaxError('INACTIVE_SETTING','Uniform切趾模式没有活动的切趾因子。')
    aperture_type=str(source.SystemData.Aperture.ApertureType)if q.parameter=='Aperture'else None
    if aperture_type=='FloatByStopSize':raise ZemaxError('INACTIVE_SETTING','FloatByStopSize无独立系统孔径数值。')
    parameter_index={'Radius':0,'Curvature':1,'Thickness':2}[q.parameter]if q.category=='Surface'else system_parameter_index(source,q)
    field_type=str(source.SystemData.Fields.GetFieldType())if q.parameter in {'XField','YField'}else None
    if field_type=='ObjectHeight'and not math.isfinite(float(source.LDE.GetSurfaceAt(0).Thickness)):raise ZemaxError('INVALID_MODEL','ObjectHeight扫描需要有限物距。',field_type=field_type)
    if field_type is not None and not any(t in field_type for t in ['Angle','Height']):raise ZemaxError('SETTING_UNCONFIRMED','Universal Plot视场单位尚未确认。',field_type=field_type)
    lens_unit=str(source.SystemData.Units.LensUnits)
    unit=('1/'+lens_unit if q.parameter=='Curvature'else {'Temperature':'Celsius','Pressure':'atmospheres','ApodizationFactor':'dimensionless','Wavelength':'micrometers',**({q.parameter:'degrees'if 'Angle'in field_type else lens_unit}if field_type is not None else {})}.get(q.parameter,('degrees'if aperture_type=='ObjectConeAngle'else 'dimensionless'if aperture_type in {'ImageSpaceFNum','ObjectSpaceNA','ParaxialWorkingFNum'}else lens_unit)))
    return dict(category_index=0 if q.category=='Surface'else 1,native_parameter_index=parameter_index,native_surface=q.surface if q.surface is not None else 1,unit=unit,aperture_type=aperture_type,field_type=field_type)


def checked_axis(backend,q):
    try:return resolve_axis(backend.system,q,getattr(backend,'native',None))
    except ZemaxError as exc:
        if exc.code=='RESTORE_FAILED':backend.requires_reconnect=True
        raise


def run(backend,q):
    if q.category=='NSC'and str(backend.system.Mode)=='NonSequential':backend._require_nsc()
    else:backend._require_sequential()
    for surface in [i for i in [q.surface,q.first_surface,q.last_surface]if i is not None]:backend._row(surface)
    source=backend.system;axis=checked_axis(backend,q)
    target=targets.resolve(backend,q)
    copy=source.CopySystem()
    if copy is None:raise ZemaxError('COPY_FAILED','Universal Plot无法创建分析副本。')
    tool=None
    try:
        owner=type('AnalysisOwner',(),dict(system=copy,native=backend.native))()
        tool=CoatingWavelengthAnalysis(new_analysis(owner,'UniversalPlot1D'),copy,int(source.SystemID))
        native=unwrap(tool.GetSettings());cfg=backend.directory/('universal_'+uuid4().hex+'.CFG')
        if not native.SaveTo(str(cfg)):raise ZemaxError('CFG_EXPORT_FAILED','Universal Plot配置导出失败。')
        values=dict(UN1_CATEGORY=axis['category_index'],UN1_PARAMETER=axis['native_parameter_index'],UN1_SURFACE=axis['native_surface'],UN1_STARTVAL=q.start,UN1_STOPVAL=q.stop,UN1_STEPS=q.samples,UN1_OPERAND=target['operand'],UN1_MFLINE=target['line'],UN1_TITLE='MCP Universal Plot')
        for i,value in enumerate(target['parameters'],1):values['UN1_PAR'+str(i)]=value
        operations=[]
        for key,value in values.items():
            accepted=bool(native.ModifySettings(str(cfg),key,str(value)));operations.append(dict(key=key,value=value,accepted=accepted))
            if not accepted:raise ZemaxError('SETTING_REJECTED','Universal Plot正式配置键未采用。',setting=key)
        if not native.LoadFrom(str(cfg)):raise ZemaxError('CFG_LOAD_FAILED','Universal Plot配置加载失败。')
    except Exception as original:
        try:
            if tool is not None:
                if not backend._close_task_native(dict(native=tool)):backend.requires_reconnect=True
            elif copy.Close(False)is False:backend.requires_reconnect=True
        except Exception as cleanup:
            backend.requires_reconnect=True
            original.add_note('Universal Plot copy cleanup failed: '+str(cleanup))
        raise
    settings=dict(kind=q.kind,requested=q.model_dump(),cfg_operations=operations,cfg_path=str(cfg),lens_unit=str(source.SystemData.Units.LensUnits),source_system_id=int(source.SystemID),analysis_system_id=int(copy.SystemID),configuration=int(source.MCE.CurrentConfiguration))
    settings['x_unit']=axis['unit']
    settings.update(axis)
    settings['target']=target
    def collect(task):
        result=unwrap(tool.GetResults());path=backend.directory/(task['task_id']+'_native.txt')
        if result is None or not result.IsValid:
            messages=[]if result is None else [dict(code=str(result.GetMessageAt(i).ErrorCode),text=str(result.GetMessageAt(i).Text))for i in range(result.NumberOfMessages)]
            raise ZemaxError('ANALYSIS_FAILED','Universal Plot没有有效原生结果。',native_messages=messages)
        if not result.GetTextFile(str(path)):raise ZemaxError('EXPORT_FAILED','Universal Plot原生文本导出失败。')
        try:rows,actual=parse_curve(path.read_text(encoding='utf-16'),q,target,axis)
        except ZemaxError as exc:exc.details['native_text_path']=str(path);raise
        settings['native']=actual
        if not backend._close_task_native(task):
            backend.requires_reconnect=True
            raise ZemaxError('CLEANUP_FAILED','Universal Plot分析或副本关闭未确认。',cleanup_warnings=task.get('cleanup_warnings',[]),native_text_path=str(path))
        return dict(analysis_kind=q.kind,computation_method='native_analysis_cfg_on_owned_copy',actual_settings=actual,rows=[dict(index=i,x=r[0],value=r[1])for i,r in enumerate(rows)],series=[dict(series=0,description=target['label']+' vs '+q.parameter,x_label=q.parameter,labels=[target['label']],x=[r[0]for r in rows],y=[[r[1]]for r in rows],x_unit=settings['x_unit'],y_unit=target['unit'],unit_source=target['unit_source'],invalid_count=0)],grids=[],structured_data_available=True,artifacts=[dict(kind='native_text',path=str(path)),dict(kind='native_settings',path=str(cfg))])
    return backend._start_task('analysis',tool,settings,analysis=True,collector=collect)
