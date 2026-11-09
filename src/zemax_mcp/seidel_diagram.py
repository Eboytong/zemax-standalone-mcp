"""Seidel bar diagrams from the documented unconverted native coefficient table."""
import math
from .errors import ZemaxError

COEFFICIENTS=('SPHA','COMA','ASTI','FCUR','DIST','CLA','CTR')


def diagram_data(result,q,stop_surface,image_surface,last_surface):
    source=[row for row in result.get('rows',[]) if set(COEFFICIENTS)<=row.get('coefficients',{}).keys()]
    if not source:raise ZemaxError('NO_RESULT_DATA','缺少未转换Seidel系数分区。')
    sections={row['section'] for row in source}
    if len(sections)!=1:raise ZemaxError('INVALID_RESULT_DATA','未转换Seidel分区不唯一。',sections=sorted(sections))
    columns=[key for key in COEFFICIENTS if not (q.ignore_distortion and key=='DIST') and not (q.ignore_chromatic and key in {'CLA','CTR'})]
    rows=[];seen=set();native_totals=[]
    for row in source:
        label=str(row['row_label']).strip()
        if label.casefold() in {'sum','total','累计','总和'}:
            native_totals.append(row);continue
        if label.casefold() in {'stop','sto','光阑'}:surface=stop_surface
        elif label.casefold() in {'image','ima','像面'}:surface=image_surface
        else:
            try:surface=int(label)
            except ValueError as exc:raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','Seidel曲面标签无法归属。',label=label) from exc
        if surface in seen:raise ZemaxError('INVALID_RESULT_DATA','Seidel曲面重复。',surface=surface)
        seen.add(surface)
        if surface==image_surface or not q.first_surface<=surface<=last_surface:continue
        values={key:row['coefficients'][key] for key in columns}
        if any(not isinstance(v,(float,int)) or not math.isfinite(v) for v in values.values()):
            raise ZemaxError('INVALID_RESULT_DATA','Seidel系数不是有限数值。',surface=surface)
        rows.append(dict(index=len(rows),surface=surface,row_label=label,coefficients=values,
            unit=row['unit'],source_line=row.get('source_line'),row_kind='surface'))
    expected=set(range(q.first_surface,last_surface+1))
    if {row['surface'] for row in rows}!=expected:
        raise ZemaxError('NO_RESULT_DATA','所选范围有曲面未返回Seidel系数。',expected=sorted(expected),actual=[r['surface'] for r in rows])
    units={row['unit'] for row in rows}
    if len(units)!=1:raise ZemaxError('INVALID_RESULT_DATA','Seidel系数单位不一致。',units=sorted(units))
    unit=rows[0]['unit']
    rows.sort(key=lambda row:row['surface'])
    for i,row in enumerate(rows):row['index']=i
    rows.append(dict(index=len(rows),surface=None,row_label='Sum',row_kind='sum',unit=unit,
        coefficients={key:math.fsum(row['coefficients'][key] for row in rows) for key in columns}))
    series=dict(series=0,plot_kind='bar',description='Unconverted Seidel coefficients',
        labels=columns,x=list(range(len(rows))),tick_labels=[str(r['surface']) if r['surface'] is not None else 'Sum' for r in rows],
        x_label='Surface',x_unit='index',y_label='Seidel coefficient',y_unit=unit,value_units=[unit]*len(columns),
        y=[[row['coefficients'][key] for key in columns] for row in rows],suppress_frame=q.suppress_frame)
    if q.plot_scale:series['y_limits']=[-q.plot_scale,q.plot_scale]
    return dict(rows=rows,series=[series],coefficient_order=columns,native_totals=native_totals,
        sample_count=len(rows),units=dict(coefficient=unit),structured_data_available=True)


def run_seidel_diagram(backend,q):
    backend._require_sequential()
    if q.method=='native':
        explicit=q.model_fields_set & {'first_surface','last_surface','wavelength'}
        if explicit:raise ZemaxError('UNSUPPORTED_SETTING','本机原生Seidel图未公开面范围/波长设置；可使用coefficients方法。',settings=sorted(explicit))
        return backend._run_general_analysis(q)
    from .analysis_models import SeidelCoefficients
    image=int(backend.system.LDE.NumberOfSurfaces)-1
    last=q.last_surface if q.last_surface is not None else image-1
    if last>=image or q.first_surface>=image:raise ZemaxError('INDEX_OUT_OF_RANGE','Seidel图面范围须位于像面之前。',image_surface=image)
    if q.wavelength>int(backend.system.SystemData.Wavelengths.NumberOfWavelengths):
        raise ZemaxError('INDEX_OUT_OF_RANGE','波长编号越界。',wavelength=q.wavelength)
    stop=int(backend.system.LDE.StopSurface)
    def flow(task):
        result=yield from backend._child_job(task,backend._run_general_analysis,SeidelCoefficients(kind='seidel_coefficients',wavelength=q.wavelength))
        backend._cancel_boundary(task)
        child=backend._task_view(backend.tasks[result['task']['task_id']])
        data=diagram_data(result,q,stop,image,last)
        task['rows'].extend(data.pop('rows'))
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_SeidelCoefficients_bar_chart',
            result_source='Native unconverted coefficients; chart definition from OpticStudio 2024 R2 manual p.746',
            fallback_reason='Native SeidelDiagram has no usable result outlet' if q.method=='auto' else None,
            actual_settings=dict(requested=q.model_dump(),first_surface=q.first_surface,last_surface=last,
                stop_surface=stop,image_surface=image,wavelength=q.wavelength,
                native_coefficient_settings=result['task']['settings']),
            native_source=dict(task_id=child['task_id'],state=child['state'],close_attempted=child.get('close_attempted'),cleanup_warnings=child.get('cleanup_warnings',[])),
            native_artifacts=result.get('artifacts',[]),
            artifacts=[a for a in result.get('artifacts',[]) if a.get('kind')=='native_text'],applicability=result.get('applicability'),**data)
        task['restoration']=dict(required=False,restored=True,source_model_modified=False)
    return backend._composite(q.kind,q.model_dump(),flow)
