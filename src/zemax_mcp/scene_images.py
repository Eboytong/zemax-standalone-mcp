"""Documented CFG scene-image settings with report and native-grid readback."""
import math
import uuid
from typing import Literal

from .schema import Request, Positive, PositiveIndex
from .data import unwrap, dotnet_array
from .errors import ZemaxError
from .image_viewers import ANALYSIS_IDS, MODIFY_SETTINGS, parse_report

KINDS=('extended_diffraction_image','partially_coherent_image')


class SceneImage(Request):
    field: PositiveIndex=1
    wavelength: PositiveIndex=1
    input_mode: Literal['native_current_input']='native_current_input'


class ExtendedDiffractionImage(SceneImage):
    kind: Literal['extended_diffraction_image']
    source_width: Positive
    display_width: Positive


class PartiallyCoherentImage(SceneImage):
    kind: Literal['partially_coherent_image']


def verify_selection(parsed, request, system):
    field=system['fields'][request.field-1]
    expected=dict(field_deg=field['y'],wavelength_um=system['wavelengths'][request.wavelength-1]['wavelength_um'])
    if request.kind=='extended_diffraction_image':
        expected.update(source_width=request.source_width,display_width=request.display_width)
    for key,value in expected.items():
        actual=parsed.get(key)
        if not isinstance(actual,(float,int)) or not math.isfinite(actual) or abs(actual-value)>5.1e-5:
            raise ZemaxError('SETTING_REJECTED','原生图像报告未确认请求设置。',
                             setting=key,requested=value,actual=actual,readback_source='native report header')
    return dict(**expected,source='native report header',absolute_rounding_tolerance=5.1e-5)


def image_grid(native_grid, parsed):
    nx,ny=int(native_grid.Nx),int(native_grid.Ny)
    values=dotnet_array(native_grid.Values)
    text=parsed['grid']
    if nx<=0 or ny<=0 or len(values)!=ny or any(len(row)!=nx for row in values) or len(text)!=ny or any(len(row)!=nx for row in text):
        raise ZemaxError('INVALID_RESULT_DATA','图像原生网格与报告尺寸不一致。',nx=nx,ny=ny)
    if any(not math.isfinite(v) or v<0 for row in values for v in row):
        raise ZemaxError('INVALID_RESULT_DATA','图像原生强度包含非有限或负值。')
    # Non-square 9x7 controlled native case confirms: text rows reverse native Y.
    error=max(abs(a-b) for row,other in zip(values,reversed(text),strict=True)
              for a,b in zip(row,other,strict=True))
    if error>5.1e-5:
        raise ZemaxError('INVALID_RESULT_DATA','图像原生数组与文本行方向或数值不匹配。',
                         max_error=error,absolute_tolerance=5.1e-5)
    return dict(grid=0,nx=nx,ny=ny,values=values,min_x=0,min_y=0,dx=1,dy=1,
                x_label='Native image column',y_label='Native image row',
                x_unit='pixel index',y_unit='pixel index',value_unit='relative intensity',
                description=parsed['kind'],array_order='values[y][x]; native array order',
                text_row_order='reverse of native array Y',text_comparison_max_error=error,
                physical_axes_verified=False,invalid_count=0,
                native_axes=dict(min_x=float(native_grid.MinX),min_y=float(native_grid.MinY),
                                 dx=float(native_grid.Dx),dy=float(native_grid.Dy),
                                 x_label=str(native_grid.XLabel),y_label=str(native_grid.YLabel)))


def collect_scene_image(backend, task):
    native=unwrap(task['native'].GetResults())
    path=backend.directory/(task['task_id']+'_native.txt')
    if native is None or not native.IsValid:
        raise ZemaxError('ANALYSIS_FAILED','原生图像结果无效。')
    if not native.GetTextFile(str(path)):
        raise ZemaxError('EXPORT_FAILED','原生图像文本导出失败。',path=str(path))
    request=task['scene_request']
    try:
        parsed=parse_report(request.kind,path.read_text(encoding='utf-16'))
        readback=verify_selection(parsed,request,task['system_settings'])
        if int(native.NumberOfDataGrids)!=1:
            raise ZemaxError('NO_RESULT_DATA','原生图像应返回一个强度网格。',count=int(native.NumberOfDataGrids))
        grid=image_grid(native.GetDataGrid(0),parsed)
    except ZemaxError as exc:
        exc.details['native_text']=str(path)
        raise
    task['settings']['actual_readback']=readback
    header={key:value for key,value in parsed.items() if key!='grid'}
    return dict(analysis_kind=request.kind,structured_data_available=True,grids=[grid],series=[],
                image_header=header,actual_settings=task['settings'],
                input_selection=dict(mode='native_current_input',identity_verified=False,
                    source='existing native analysis image; no confirmed file selector'),
                computation_method='native '+ANALYSIS_IDS[request.kind][0]+'; documented CFG and report readback',
                native_messages=[dict(code=str(native.GetMessageAt(i).ErrorCode),text=str(native.GetMessageAt(i).Text))
                                 for i in range(int(native.NumberOfMessages))],
                artifacts=[dict(kind='native_text',path=str(path))])


def run_scene_image(backend, request):
    from .imaging import new_analysis
    backend._require_sequential(focused=True)
    system=backend.get_system_settings(None)
    if request.field>len(system['fields']) or request.wavelength>len(system['wavelengths']):
        raise ZemaxError('INDEX_OUT_OF_RANGE','图像视场或波长编号越界。')
    if system['lens_units']!='Millimeters':
        raise ZemaxError('UNIT_MISMATCH','当前图像报告适配要求毫米镜头单位。',actual=system['lens_units'],required='Millimeters')
    field=system['fields'][request.field-1]
    matches=[f for f in system['fields'] if f['x']==0 and f['y']==field['y']]
    if system['field_type']!='Angle' or field['x']!=0 or field['y']<0 or len(matches)!=1:
        raise ZemaxError('SETTING_UNCONFIRMED','当前报告需唯一的非负Y方向角度视场以核对选择。',field=request.field)
    tool=new_analysis(backend,ANALYSIS_IDS[request.kind][0])
    settings=dict(kind=request.kind,requested=request.model_dump(),cfg_operations=[],
                  input_selection='native_current_input; identity unverified')
    try:
        native=unwrap(tool.GetSettings())
        settings['native_settings_type']=str(native.GetType().FullName)
        cfg=backend.directory/('scene_'+uuid.uuid4().hex+'.CFG')
        settings['cfg_path']=str(cfg)
        if not native.SaveTo(str(cfg)):
            raise ZemaxError('CFG_EXPORT_FAILED','原生图像配置导出失败。',path=str(cfg))
        prefix='EXD_' if request.kind=='extended_diffraction_image' else 'PCI_'
        entries={prefix+'FIELD':request.field,prefix+'WAVE':request.wavelength}
        if request.kind=='extended_diffraction_image':
            entries.update(EXD_FILESIZE=request.source_width,EXD_DISPLAYSIZE=request.display_width)
        for key,value in entries.items():
            assert key in MODIFY_SETTINGS[request.kind]
            accepted=bool(native.ModifySettings(str(cfg),key,str(value)))
            settings['cfg_operations'].append(dict(key=key,value=value,accepted=accepted))
            if not accepted:
                raise ZemaxError('SETTING_REJECTED','原生图像配置键被拒绝。',setting=key,requested=value,path=str(cfg))
        if not native.LoadFrom(str(cfg)):
            raise ZemaxError('CFG_LOAD_FAILED','原生图像配置加载失败。',path=str(cfg))
    except Exception:
        if not backend._close_task_native(dict(native=tool)):backend.requires_reconnect=True
        raise
    # _start_task may collect immediately, so bind request before starting.
    def collect(task):
        task['scene_request']=request
        return collect_scene_image(backend,task)
    return backend._start_task('analysis',tool,settings,analysis=True,collector=collect)
