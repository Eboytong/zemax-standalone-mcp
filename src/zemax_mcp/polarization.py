"""Documented PPM CFG settings and native text results, without binary offsets."""
import math
import re
from uuid import uuid4
from .data import unwrap
from .errors import ZemaxError
from .imaging import new_analysis

NUMBER=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?'
ALIASES={
    '波长':'wavelength_um','wavelength':'wavelength_um',
    '视场pos':'field_position','fieldpos':'field_position','fieldposition':'field_position',
    'x场':'jx','xfield':'jx','y场':'jy','yfield':'jy',
    'x相位':'x_phase','xphase':'x_phase','y相位':'y_phase','yphase':'y_phase',
    '结构':'configuration','config':'configuration','configuration':'configuration',
    '表面':'surface','surface':'surface','透射':'transmission_percent','transmission':'transmission_percent',
}
COLUMNS=('px','py','ex','ey','intensity','relative_phase_deg','orientation_deg')


def parse_pupil_text(text):
    actual={};rows=[];started=False
    for line_number,line in enumerate(text.splitlines(),1):
        if re.match(r'^\s*Px\s+Py\s+Ex\s+Ey\b',line,re.I):
            started=True;continue
        if not started:
            if ':' not in line and '：' not in line:continue
            label,value=re.split('[:：]',line,maxsplit=1)
            key=ALIASES.get(re.sub(r'[\s-]','',label).casefold())
            if key:
                numbers=[float(v)for v in re.findall(NUMBER,value)]
                if key=='field_position' and len(numbers) in {1,2}:
                    actual[key]=dict(x=numbers[0] if len(numbers)==2 else 0.,y=numbers[-1])
                elif numbers:actual[key]=numbers[0]
            continue
        if not line.strip():continue
        if not re.match(r'^\s*[-+\d.]',line):
            raise ZemaxError('INVALID_RESULT_DATA','偏振瞳图数值表包含不可识别行。',line=line_number,native_line=line)
        tokens=line.split()
        try:values=[float(v) for v in tokens]
        except ValueError as exc:
            raise ZemaxError('INVALID_RESULT_DATA','偏振瞳图数值格式错误。',line=line_number,native_line=line) from exc
        if len(values)!=7 or not all(math.isfinite(v) for v in values):
            raise ZemaxError('INVALID_RESULT_DATA','偏振瞳图须提供七列有限数值。',line=line_number,native_line=line)
        rows.append(dict(index=len(rows),**dict(zip(COLUMNS,values))))
    if not rows:raise ZemaxError('NO_RESULT_DATA','偏振瞳图原生文本没有有效瞳点。',native_preamble=text[:2000])
    points=[(r['px'],r['py']) for r in rows]
    if len(set(points))!=len(points):raise ZemaxError('INVALID_RESULT_DATA','偏振瞳图瞳坐标重复。')
    return actual,rows


def verify_settings(actual,rows,settings):
    q=settings['requested']
    wanted=dict(surface=q['surface'],configuration=settings['configuration'],wavelength_um=settings['wavelength_um'],
                jx=q['jx'],jy=q['jy'],x_phase=q['x_phase'],y_phase=q['y_phase'])
    for key,value in wanted.items():
        tolerance=.0051 if key.endswith('phase') else .000051 if key in {'wavelength_um','jx','jy'} else 0
        difference=actual.get(key,float('inf'))-value
        if key.endswith('phase') and math.isfinite(difference):difference=(difference+180)%360-180
        if key not in actual or abs(difference)>tolerance:
            raise ZemaxError('SETTING_REJECTED','偏振瞳图原生文本设置与请求不符。',setting=key,requested=value,actual=actual.get(key))
    expected=settings['field_position']
    if 'field_position' not in actual or any(abs(actual['field_position'][axis]-expected[axis])>.000051 for axis in ('x','y')):
        raise ZemaxError('SETTING_REJECTED','偏振瞳图视场位置未确认。',requested=expected,actual=actual.get('field_position'))
    n=q['sampling'];step=2/(n-1)
    for row in rows:
        for key in ('px','py'):
            v=row[key]
            if abs(v)>1.00051 or abs((v+1)/step-round((v+1)/step))*step>.00051:
                raise ZemaxError('SETTING_REJECTED','偏振瞳图采样坐标未采用。',requested=n,coordinate=v)
    # The text rounds pupil coordinates to three decimals; observed adjacent spacing confirms density.
    spacings=[]
    for key in ('px','py'):
        coords=sorted({row[key] for row in rows})
        spacings.extend(b-a for a,b in zip(coords,coords[1:]) if b>a)
    if not spacings or abs(min(spacings)-step)>.00101:
        raise ZemaxError('SETTING_UNCONFIRMED','偏振瞳图有效点不足以确认采样密度。',sampling=n,observed_spacings=spacings[:10])
    return dict(**actual,sampling=n,readback_source='native text header and pupil lattice',
                field_selection_source='documented PPM_FIELD acknowledgement and native field coordinates',
                configuration_selection='current configuration; add/sub config lists set to 0')


def run_pupil_map(backend,q):
    backend._require_sequential();backend._row(q.surface)
    system=backend.system.SystemData
    if q.field>system.Fields.NumberOfFields or q.wavelength>system.Wavelengths.NumberOfWavelengths:
        raise ZemaxError('INDEX_OUT_OF_RANGE','偏振瞳图视场或波长编号越界。')
    field=system.Fields.GetField(q.field)
    field_position=dict(x=float(field.X),y=float(field.Y))
    matching=[i for i in range(1,int(system.Fields.NumberOfFields)+1)
        if float(system.Fields.GetField(i).X)==field_position['x'] and float(system.Fields.GetField(i).Y)==field_position['y']]
    if matching != [q.field]:
        raise ZemaxError('SETTING_UNCONFIRMED','所选视场坐标与其他视场重复，原生文本不能唯一核实视场编号。',field=q.field,matching_fields=matching)
    settings=dict(kind=q.kind,requested=q.model_dump(),configuration=int(backend.system.MCE.CurrentConfiguration),
        wavelength_um=float(system.Wavelengths.GetWavelength(q.wavelength).Wavelength),field_type=str(system.Fields.GetFieldType()),
        field_position=field_position,cfg_method='IAS_.SaveTo/ModifySettings/LoadFrom')
    tool=new_analysis(backend,'PolarizationPupilMap')
    cfg=backend.directory/('pupil_'+uuid4().hex+'.CFG')
    settings['cfg_path']=str(cfg);settings['cfg_operations']=[]
    try:
        native=unwrap(tool.GetSettings());settings['runtime_settings_type']=str(native.GetType().FullName)
        if not native.SaveTo(str(cfg)):raise ZemaxError('CFG_EXPORT_FAILED','偏振瞳图初始配置导出失败。',path=str(cfg))
        values=dict(PPM_SAMP=(q.sampling-3)//2,PPM_FIELD=q.field,PPM_WAVE=q.wavelength,PPM_SURFACE=q.surface,
            PPM_JX=q.jx,PPM_JY=q.jy,PPM_PX=q.x_phase,PPM_PY=q.y_phase,PPM_ADDCONFIG=0,PPM_SUBCONFIGS=0)
        for key,value in values.items():
            accepted=bool(native.ModifySettings(str(cfg),key,str(value)))
            settings['cfg_operations'].append(dict(key=key,value=value,accepted=accepted))
            if not accepted:raise ZemaxError('SETTING_REJECTED','偏振瞳图配置键写入被拒绝。',setting=key,requested=value,path=str(cfg))
        if not native.LoadFrom(str(cfg)):raise ZemaxError('CFG_LOAD_FAILED','偏振瞳图配置加载失败。',path=str(cfg))
    except Exception:
        if not backend._close_task_native(dict(native=tool)):
            backend.requires_reconnect=True
        raise
    return backend._start_task('analysis',tool,settings,analysis=True,collector=lambda task:collect_pupil_map(backend,task))


def collect_pupil_map(backend,task):
    result=unwrap(task['native'].GetResults());path=backend.directory/(task['task_id']+'_native.txt')
    if result is None or not result.IsValid:raise ZemaxError('ANALYSIS_FAILED','偏振瞳图没有有效原生结果。')
    if not result.GetTextFile(str(path)):raise ZemaxError('EXPORT_FAILED','偏振瞳图原生文本导出失败。')
    text=path.read_text(encoding='utf-16')
    try:
        actual,rows=parse_pupil_text(text);actual=verify_settings(actual,rows,task['settings'])
    except ZemaxError as exc:
        exc.details['native_text_path']=str(path)
        raise
    task['settings']['native']=actual
    return dict(analysis_kind='polarization_pupil_map',computation_method='native_analysis_cfg',rows=rows,
        actual_settings=actual,field_type=task['settings']['field_type'],columns=list(COLUMNS),units=dict(px='normalized pupil',py='normalized pupil',ex='native electric-field amplitude',ey='native electric-field amplitude',intensity='native relative intensity',relative_phase_deg='degrees',orientation_deg='degrees'),
        intensity_definition='native PPM transverse XY intensity: abs(Ex)**2 + abs(Ey)**2; bulk ray intensity additionally includes Ez',
        phase_definition='native relative Ex/Ey phase; phase/orientation are degenerate when a component vanishes or polarization is circular',
        native_header=[str(x)for x in result.HeaderData.Lines],
        native_messages=[dict(code=str(result.GetMessageAt(i).ErrorCode),text=str(result.GetMessageAt(i).Text))for i in range(result.NumberOfMessages)],
        scatter=[dict(description='Polarization pupil intensity',x_label='Normalized pupil X',y_label='Normalized pupil Y',points=[dict(x=r['px'],y=r['py'],value=r['intensity'])for r in rows])],
        artifacts=[dict(kind='native_text',path=str(path)),dict(kind='native_settings',path=task['settings']['cfg_path'])])
