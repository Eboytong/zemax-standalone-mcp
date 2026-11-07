"""Universal Plot2D: native CFG, explicit text identity and endpoint grid."""
import math,re
from uuid import uuid4
from typing import Literal
from pydantic import model_validator
from .schema import Request,PositiveIndex
from .universal import UniversalAxis,UniversalPlot1D,verify_identity,checked_axis
from .data import unwrap,dotnet_array
from .imaging import new_analysis
from .errors import ZemaxError
from . import universal_targets as targets


class UniversalPlot2D(Request):
    kind: Literal['universal_plot_2d']
    x: UniversalAxis
    y: UniversalAxis
    operand: Literal['TTHI','CVVA']='TTHI'
    first_surface: PositiveIndex | None = None
    last_surface: PositiveIndex | None = None
    target: targets.UniversalTarget | None = None
    @model_validator(mode='after')
    def selection(self):
        family=lambda axis:'curvature'if axis.parameter in {'Radius','Curvature'}else axis.parameter
        identity=lambda axis:(axis.category,axis.surface,axis.selection,axis.configuration,axis.operand_row,axis.nsc_surface,axis.object,axis.parameter_number,family(axis))
        if identity(self.x)==identity(self.y):raise ValueError('X/Y must select independent variables; Radius and Curvature share one surface property.')
        if self.x.samples*self.y.samples>65536:raise ValueError('Universal grid budget is 65536 points.')
        return targets.validate_request(self)


NUMBER=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'


def readback(text,q,native,target=None,axes=None):
    targets.check_report(text)
    actual={};lines=text.splitlines();dependent=next((l for l in lines if re.match(r'\s*(因变量|Dependent Variable)\s*Z\s*[:：]',l,re.I)),None)
    if not dependent:raise ZemaxError('SETTING_UNCONFIRMED','Universal2D缺少原生操作数身份。')
    for name,axis in [('X',q.x),('Y',q.y)]:
        heading=next((l for l in lines if re.match(r'\s*(自变量|Independent Variable)\s*'+name+r'\s*[:：]',l,re.I)),None)
        range_line=next((l for l in lines if re.match(name+r'\s*[–-]\s*(范围|Range)\s*[:：]',l,re.I)),None)
        sample_line=next((l for l in lines if re.match(name+r'\s*[–-]\s*(方向采样|Sampling)\s*[:：]',l,re.I)),None)
        if not heading or not range_line or not sample_line:raise ZemaxError('SETTING_UNCONFIRMED','Universal2D轴设置头不完整。',axis=name)
        bounds=[float(v)for v in re.findall(NUMBER,re.split('[:：]',range_line,maxsplit=1)[1])]
        sample=[int(v)for v in re.findall(r'\d+',re.split('[:：]',sample_line,maxsplit=1)[1])]
        if len(bounds)!=2 or sample!=[axis.samples]or any(abs(v-w)>5e-7*max(1,abs(w))for v,w in zip(bounds,[axis.start,axis.stop])):raise ZemaxError('SETTING_REJECTED','Universal2D范围或采样未采用。',axis=name,native_range=bounds,native_samples=sample)
        dependent_args=dict(target=q.target)if q.target is not None else dict(operand=q.operand,first_surface=q.first_surface,last_surface=q.last_surface)
        selection=UniversalPlot1D(kind='universal_plot_1d',**axis.model_dump(),**dependent_args)
        verify_identity(re.sub(r'(自变量|Independent Variable)\s*'+name,lambda m:m[1]+'X',heading,flags=re.I),re.sub(r'(因变量|Dependent Variable)\s*Z',lambda m:m[1]+'Y',dependent,flags=re.I),selection,target,None if axes is None else axes[name])
        actual[name]=dict(axis=heading,dependent=dependent,start=bounds[0],stop=bounds[1],samples=sample[0],source='native 2D axis/operand identity, range and sampling header')
    nx,ny=q.x.samples,q.y.samples
    values=native['values']
    if (native['nx'],native['ny'])!=(nx,ny)or len(values)!=ny or any(len(row)!=nx for row in values):raise ZemaxError('INVALID_RESULT_DATA','Universal2D网格尺寸冲突。',native=native)
    for name,axis in [('x',q.x),('y',q.y)]:
        step=(axis.stop-axis.start)/(axis.samples-1)
        if not math.isclose(native['min_'+name],axis.start,rel_tol=1e-10,abs_tol=1e-10)or not math.isclose(native['d'+name],step,rel_tol=1e-10,abs_tol=1e-10):raise ZemaxError('SETTING_REJECTED','Universal2D原生网格坐标未采用端点采样。',axis=name,native=native)
    if any(not math.isfinite(v)for row in values for v in row):raise ZemaxError('INVALID_RESULT_DATA','Universal2D包含非有限网格值。')
    return actual


def run(backend,q):
    if q.x.category=='NSC'and q.y.category=='NSC'and str(backend.system.Mode)=='NonSequential':backend._require_nsc()
    else:backend._require_sequential()
    for i in [i for i in [q.x.surface,q.y.surface,q.first_surface,q.last_surface]if i is not None]:backend._row(i)
    source=backend.system;tool=None
    axes={name:checked_axis(backend,axis)for name,axis in [('X',q.x),('Y',q.y)]}
    def physical(axis,resolved):
        if axis.category=='Configuration':return resolved['physical_identity']
        if axis.category=='Surface':return ('Surface',int(source.MCE.CurrentConfiguration),axis.surface,'Curvature'if axis.parameter=='Radius'else axis.parameter+(':'+str(axis.parameter_number)if axis.parameter=='SurfaceParameter'else''))
        if axis.category=='System':return ('System',int(source.MCE.CurrentConfiguration),axis.parameter,axis.selection)
        return None
    px,py=physical(q.x,axes['X']),physical(q.y,axes['Y'])
    if px is not None and px==py:raise ZemaxError('INVALID_ARGUMENT','Universal2D两轴解析到同一曲面属性。',x=axes['X'],y=axes['Y'])
    target=targets.resolve(backend,q)
    try:
        tool=new_analysis(backend,'UniversalPlot2D');settings=unwrap(tool.GetSettings());cfg=backend.directory/('universal2_'+uuid4().hex+'.CFG')
        if not settings.SaveTo(str(cfg)):raise ZemaxError('CFG_EXPORT_FAILED','Universal2D配置导出失败。')
        values=dict(UN2_OPERAND=target['operand'],UN2_MFLINE=target['line'],UN2_SHOWAS=2,UN2_TITLE='MCP Universal2D')
        for i,value in enumerate(target['parameters'],1):values['UN2_PAR'+str(i)]=value
        for name,axis in [('X',q.x),('Y',q.y)]:
            resolved=axes[name]
            for key,value in dict(CATEGORY=resolved['category_index'],PARAMETER=resolved['native_parameter_index'],SURFACE=resolved['native_surface'],STARTVAL=axis.start,STOPVAL=axis.stop,STEPS=axis.samples).items():values['UN2_'+key+name]=value
        operations=[]
        for key,value in values.items():
            accepted=bool(settings.ModifySettings(str(cfg),key,str(value)));operations.append(dict(key=key,value=value,accepted=accepted))
            if not accepted:raise ZemaxError('SETTING_REJECTED','Universal2D配置键被拒绝。',setting=key)
        if not settings.LoadFrom(str(cfg)):raise ZemaxError('CFG_LOAD_FAILED','Universal2D配置加载失败。')
    except Exception as original:
        try:
            if tool is not None:
                if not backend._close_task_native(dict(native=tool)):backend.requires_reconnect=True
        except Exception as cleanup:backend.requires_reconnect=True;original.add_note('Universal2D analysis cleanup failed: '+str(cleanup))
        raise
    actual=dict(native_display='GreyScale (UN2_SHOWAS=2); Surface view native close fault recorded separately',kind=q.kind,requested=q.model_dump(),cfg_operations=operations,source_system_id=int(source.SystemID),analysis_system_id=int(source.SystemID),isolation="native UniversalPlot internal system copies (manual3.6.1/3.6.2)",configuration=int(source.MCE.CurrentConfiguration),lens_unit=str(source.SystemData.Units.LensUnits))
    actual['axes']=axes
    actual['target']=target
    def collect(task):
        tool.WaitForCompletion()
        actual['completion_barrier']='IA_.WaitForCompletion after IsRunning=false, before result access'
        r=unwrap(tool.GetResults());path=backend.directory/(task['task_id']+'_native.txt')
        if r is None or not r.IsValid:
            messages=[]if r is None else [dict(code=str(r.GetMessageAt(i).ErrorCode),text=str(r.GetMessageAt(i).Text))for i in range(r.NumberOfMessages)]
            raise ZemaxError('ANALYSIS_FAILED','Universal2D原生计算无有效结果。',native_messages=messages)
        if not r.GetTextFile(str(path)):raise ZemaxError('EXPORT_FAILED','Universal2D原生文本导出失败。')
        native_text=path.read_text(encoding='utf-16')
        try:targets.check_report(native_text)
        except ZemaxError as exc:exc.details['native_text_path']=str(path);raise
        if r.NumberOfDataGrids!=1:raise ZemaxError('NO_RESULT_DATA','Universal2D须返回一个原生网格。',native_text_path=str(path))
        g=r.GetDataGrid(0);grid=dict(nx=int(g.Nx),ny=int(g.Ny),min_x=float(g.MinX),min_y=float(g.MinY),dx=float(g.Dx),dy=float(g.Dy),values=dotnet_array(g.Values))
        try:adopted=readback(native_text,q,grid,target,axes)
        except ZemaxError as exc:exc.details['native_text_path']=str(path);raise
        actual['native']=adopted
        grid.update(grid=0,description=target['label']+' Universal Plot',x_label=q.x.parameter,y_label=q.y.parameter,value_label=target['label'],x_unit=axes['X']['unit'],y_unit=axes['Y']['unit'],value_unit=target['unit'],unit_source=target['unit_source'],array_order='values[y][x], ascending X/Y; endpoint samples',invalid_count=0,x=[grid['min_x']+i*grid['dx']for i in range(grid['nx'])],y=[grid['min_y']+i*grid['dy']for i in range(grid['ny'])])
        if not backend._close_task_native(task):
            backend.requires_reconnect=True
            raise ZemaxError('CLEANUP_FAILED','Universal2D分析或副本关闭未确认。',cleanup_warnings=task.get('cleanup_warnings',[]),native_text_path=str(path))
        return dict(analysis_kind=q.kind,computation_method='native_analysis_cfg_internal_system_copy',actual_settings=adopted,series=[],grids=[grid],structured_data_available=True,artifacts=[dict(kind='native_text',path=str(path)),dict(kind='native_settings',path=str(cfg))])
    return backend._start_task('analysis',tool,actual,analysis=True,collector=collect)
