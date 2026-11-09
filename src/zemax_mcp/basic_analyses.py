"""Native first-order queries and section-preserving text tables."""
import math
import re
from .errors import ZemaxError

CARD_NAMES=('object_focal_length','image_focal_length','object_focal_plane','image_focal_plane',
    'object_principal_plane','image_principal_plane','object_antiprincipal_plane','image_antiprincipal_plane',
    'object_nodal_plane','image_nodal_plane','object_antinodal_plane','image_antinodal_plane')


def cardinal_points(backend,q):
    backend._require_sequential()
    end=q.end_surface if q.end_surface is not None else backend.system.LDE.NumberOfSurfaces-2
    if end<q.start_surface:raise ZemaxError('INVALID_ARGUMENT','结束面必须不早于起始面。')
    backend._row(q.start_surface);backend._row(end)
    if q.wavelength>backend.system.SystemData.Wavelengths.NumberOfWavelengths:raise ZemaxError('INDEX_OUT_OF_RANGE','波长越界。')
    def flow(task):
        task['payload']=dict(analysis_kind=q.kind,computation_method='native_CARD_operand',
            position_unit=task['context']['lens_units'],start_surface=q.start_surface,end_surface=end,
            reference='object positions relative to start surface; image positions relative to end surface')
        operand=backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType,'CARD')
        for orientation in ('YZ','XZ') if q.orientation=='both' else (q.orientation,):
            for code,name in enumerate(CARD_NAMES):
                backend._cancel_boundary(task)
                value=float(backend.system.MFE.GetOperandValue(operand,q.start_surface,end,q.wavelength,0 if orientation=='YZ' else 1,code,0.,0.,0.))
                task['rows'].append(dict(index=len(task['rows']),orientation=orientation,key=name,value=value if math.isfinite(value) else None,
                    native_value=str(value),state='finite' if math.isfinite(value) else 'undefined',unit=task['context']['lens_units']))
                yield
    return backend._composite(q.kind,q.model_dump(),flow)


def parse_native_tables(text,kind):
    rows=[];headings=[];section=0;previous_data=False;columns=[];ray_section=None
    number=re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?$')
    coefficient=re.compile(r'\b(?:SPHA|COMA|ASTI|FCUR|DIST|CLA|CTR|W[0-9]{3}[A-Z]?|TSPH|TSCO|TTCO|TAST|TPFC|TSFC|TTFC|TDIS|TAXC|TLAC|LSPH|LSCO|LTCO|LAST|LPFC|LSFC|LTFC|LDIS|LAXC|LLAC)\b')
    for line_number,line in enumerate(text.splitlines(),1):
        tokens=line.split()
        if not tokens:continue
        if '近轴' in line or 'paraxial ray' in line.lower():ray_section='paraxial'
        elif '实际光线' in line or 'real ray' in line.lower():ray_section='real'
        cleaned=[t.rstrip('%') for t in tokens]
        numeric=sum(bool(number.fullmatch(t)) for t in cleaned)
        is_data=numeric>=2 and (number.fullmatch(cleaned[0]) or numeric==len(tokens)-1)
        if is_data:
            cells=[float(t) if number.fullmatch(t) and math.isfinite(float(t)) else original for t,original in zip(cleaned,tokens)]
            row=dict(index=len(rows),section=section,headers=list(headings[-3:]),cells=cells,source_line=line_number,raw=line)
            if kind=='seidel_coefficients' and columns and len(cells)==len(columns)+1:
                row.update(row_label=tokens[0],coefficients=dict(zip(columns,cells[1:])),unit='waves' if columns[0].startswith('W') else 'lens units')
            if kind=='single_ray_trace':
                row.update(ray_section=ray_section,surface=int(cells[0]) if isinstance(cells[0],float) else None)
                if len(cells)>=7:row.update(position=cells[1:4],direction_values=cells[4:7])
            if kind=='grid_distortion' and len(cells)==10:
                row.update(grid_index=cells[:2],field=cells[2:4],predicted=cells[5:7],actual=cells[7:9],distortion_percent=cells[9])
            rows.append(row);previous_data=True
        else:
            if previous_data:section+=1;headings=[];columns=[]
            previous_data=False;headings.append(line)
            found=coefficient.findall(line)
            if found:columns=found
    if not rows:raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','原生文本表格未识别。',analysis=kind)
    result=dict(rows=rows,structured_data_available=True,table_format='native columns with section headers',units_source='per-section native headers')
    if kind=='grid_distortion':
        result['scatter']=[dict(description=name+' image coordinates',x_label='image X',y_label='image Y',points=[dict(x=r[key][0],y=r[key][1],value=r['distortion_percent']) for r in rows if key in r]) for key,name in [('predicted','Predicted'),('actual','Actual')]]
    return result


def yni_operands(backend, q):
    backend._require_sequential()
    waves = backend.system.SystemData.Wavelengths
    if q.wavelength > waves.NumberOfWavelengths:
        raise ZemaxError('INDEX_OUT_OF_RANGE','YNI波长编号越界。',wavelength=q.wavelength)
    code = backend.native.enum(backend.native.api.Editors.MFE.MeritOperandType,'YNIP')
    def flow(task):
        unit = task['context']['lens_units']
        task['payload'] = dict(analysis_kind=q.kind,computation_method='native_YNIP_operand',
            position_unit=unit,wavelength_um=float(waves.GetWavelength(q.wavelength).Wavelength),
            actual_settings=dict(wavelength=q.wavelength,source='explicit YNIP Surf/Wave arguments',
                                 configuration=task['context']['configuration']),
            resource_ownership='active optical system; no analysis or SystemTool opened',series=[],grids=[])
        for surface in range(1,backend.system.LDE.NumberOfSurfaces-1):
            backend._cancel_boundary(task)
            arguments=[surface,q.wavelength,0.,0.,0.,0.,0.,0.]
            value=float(backend.system.MFE.GetOperandValue(code,*arguments))
            if not math.isfinite(value):
                raise ZemaxError('INVALID_RESULT_DATA','YNIP返回非有限值。',surface=surface,wavelength=q.wavelength,value=repr(value))
            task['rows'].append(dict(index=len(task['rows']),surface=surface,value=value,unit=unit,
                                     native_operand='YNIP',native_arguments=arguments))
            yield
        if not task['rows']:
            raise ZemaxError('RESULT_UNAVAILABLE','YNI缺少可计算的光学曲面。')
        task['payload']['series']=[dict(series=0,description='YNI contribution by surface',
            x_label='Surface number',labels=['YNI'],x=[r['surface'] for r in task['rows']],
            y=[[r['value']] for r in task['rows']],x_unit='surface index',y_unit=unit,invalid_count=0)]
    return backend._composite(q.kind,q.model_dump(),flow)


def parse_yni_contributions(text, lens_unit):
    rows=[]
    wavelength=None
    for line_number,line in enumerate(text.splitlines(),1):
        wave=re.search(r'(?:波长|wavelength)\s*:\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)\s*(?:μm|µm|um)',line,re.I)
        if wave:
            wavelength=float(wave.group(1))
        match=re.match(r'^\s*(\d+)\s+(\S+)\s*$',line)
        if match:
            try:
                value=float(match.group(2))
            except ValueError as exc:
                raise ZemaxError('INVALID_RESULT_DATA','YNI贡献行包含无效数值。',source_line=line_number,raw=line) from exc
            surface=int(match.group(1))
            if not math.isfinite(value) or (rows and surface<=rows[-1]['surface']):
                raise ZemaxError('INVALID_RESULT_DATA','YNI贡献须为有限值且面号严格递增。',source_line=line_number,raw=line)
            rows.append(dict(index=len(rows),surface=surface,value=value,unit=lens_unit,source_line=line_number,raw=line))
    if wavelength is None or not rows:
        raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','YNI报告缺少波长或有效曲面贡献行。',row_count=len(rows),wavelength=wavelength)
    if not math.isfinite(wavelength) or wavelength<=0:
        raise ZemaxError('INVALID_RESULT_DATA','YNI波长须为有限正数。',wavelength=wavelength)
    return dict(analysis_kind='yni_contributions',computation_method='native_YNIContributions_report',
        wavelength_um=wavelength,position_unit=lens_unit,rows=rows,structured_data_available=True,
        table_format='native surface/YNI rows',series=[dict(series=0,description='YNI contribution by surface',
        x_label='Surface number',labels=['YNI'],x=[r['surface'] for r in rows],y=[[r['value']] for r in rows],
        x_unit='surface index',y_unit=lens_unit,invalid_count=0)],grids=[])


def parse_source_spectrum(text):
    rows=[]
    meta={}
    in_table=False
    number=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?'
    for line_number,line in enumerate(text.splitlines(),1):
        xyz=re.search(r'输入\s*:\s*X\s*=\s*('+number+r'),\s*Y\s*=\s*('+number+r'),\s*Z\s*=\s*('+number+r')',line)
        if xyz:meta['input_xyz']=[float(x) for x in xyz.groups()]
        fitted=re.search(r'拟合\s*:\s*X\s*=\s*('+number+r'),\s*Y\s*=\s*('+number+r'),\s*Z\s*=\s*('+number+r')',line)
        if fitted:meta['fitted_xyz']=[float(x) for x in fitted.groups()]
        quality=re.search(r'CRI\s*=\s*('+number+r')\s*\(\s*CCT\s*=\s*('+number+r')\s*K\s*\)',line,re.I)
        if quality:meta.update(cri=float(quality.group(1)),cct_kelvin=float(quality.group(2)))
        if '波长' in line and '权重' in line:
            in_table=True
            continue
        point=re.match(r'^\s*('+number+r')\s+(\S+)\s*$',line)
        if point:
            try:
                wavelength,weight=map(float,point.groups())
            except ValueError as exc:
                raise ZemaxError('INVALID_RESULT_DATA','光谱行包含无效数值。',source_line=line_number,raw=line) from exc
            if not math.isfinite(wavelength) or not math.isfinite(weight) or wavelength<=0 or not 0<=weight<=1.000001:
                raise ZemaxError('INVALID_RESULT_DATA','光谱波长或相对权重超出有效范围。',source_line=line_number,raw=line)
            rows.append(dict(index=len(rows),wavelength_um=wavelength,relative_weight=weight,source_line=line_number,raw=line))
        elif in_table and line.strip():
            raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','光谱表包含无法识别的行。',source_line=line_number,raw=line)
    if len(rows)<2 or any(a['wavelength_um']>=b['wavelength_um'] for a,b in zip(rows,rows[1:])):
        raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','光源光谱报告缺少有效的递增波长/相对权重数据。',row_count=len(rows))
    if not {'input_xyz','fitted_xyz','cri','cct_kelvin'}<=meta.keys():
        raise ZemaxError('INVALID_RESULT_DATA','光源光谱报告缺少XYZ拟合或色彩质量字段。',available_fields=sorted(meta))
    if not all(math.isfinite(v) for key in ('input_xyz','fitted_xyz') for v in meta[key]) or not all(math.isfinite(meta[key]) for key in ('cri','cct_kelvin')):
        raise ZemaxError('INVALID_RESULT_DATA','光源光谱元数据包含非有限值。')
    return dict(analysis_kind='source_spectrum_viewer',computation_method='native_SourceSpectrumViewer_text',
        input_definition='native XYZ tristimulus fitting input',source_object_binding='not exposed by installed analysis settings',
        spectrum_normalization='native relative weights; maximum displayed weight is 1',spectral_unit='micrometers',
        weight_unit='dimensionless relative weight',rows=rows,structured_data_available=True,**meta,
        series=[dict(series=0,description='Native source spectrum',x_label='Wavelength',labels=['Relative weight'],
            x=[r['wavelength_um'] for r in rows],y=[[r['relative_weight']] for r in rows],x_unit='micrometers',
            y_unit='dimensionless relative weight',invalid_count=0)],grids=[])


def parse_directivity_plot(text):
    source=re.search(r'IESNA\s*光源文件\s*:\s*(.+)',text,re.I)
    peak=re.search(r'峰值强度\s*:\s*([\d.+-Ee]+)\s*坎德拉',text)
    flux=re.search(r'文件中的总光通量\s*:\s*([\d.+-Ee]+)\s*流明',text)
    if not source or not peak or not flux:
        raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','方向性报告缺少IES身份、峰值强度或总光通量。')
    peak_value,flux_value=float(peak.group(1)),float(flux.group(1))
    if not all(math.isfinite(v) and v>=0 for v in (peak_value,flux_value)):
        raise ZemaxError('INVALID_RESULT_DATA','方向性峰值或总光通量须为有限非负值。')
    groups=[];scan=None
    for line_number,line in enumerate(text.splitlines(),1):
        angle_scan=re.search(r'扫描角度\s*:\s*([+-]?[\d.]+)\s*度',line)
        if angle_scan:
            scan=float(angle_scan.group(1));groups.append(dict(scan_angle_deg=scan,rows=[]));continue
        point=re.match(r'^\s*([+-]?[\d.]+)\s+(\S+)\s*$',line)
        if point and scan is not None:
            try:
                angle,value=map(float,point.groups())
            except ValueError as exc:
                raise ZemaxError('INVALID_RESULT_DATA','方向性曲线包含无效数值。',source_line=line_number,raw=line) from exc
            if not all(math.isfinite(v) for v in (scan,angle,value)) or value<0:
                raise ZemaxError('INVALID_RESULT_DATA','方向性曲线须为有限值且光强非负。',source_line=line_number,raw=line)
            groups[-1]['rows'].append(dict(scan_angle_deg=scan,angle_deg=angle,normalized_candela=value,source_line=line_number,raw=line))
        elif scan is not None and line.strip() and not ('角度' in line and '坎德拉' in line):
            raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','方向性曲线行无法识别。',source_line=line_number,raw=line)
    if not groups or any(len(g['rows'])<2 or any(a['angle_deg']>=b['angle_deg'] for a,b in zip(g['rows'],g['rows'][1:])) for g in groups):
        raise ZemaxError('INVALID_RESULT_DATA','方向性报告缺少有效且递增的角度曲线。',scans=len(groups))
    series=[dict(series=i,description=f"Directivity at scan angle {g['scan_angle_deg']:g} deg",x_label='Angle',labels=['Normalized candela'],
        x=[r['angle_deg'] for r in g['rows']],y=[[r['normalized_candela']] for r in g['rows']],x_unit='degrees',
        y_unit='dimensionless normalized candela',invalid_count=0) for i,g in enumerate(groups)]
    rows=[r for group in groups for r in group['rows']]
    return dict(analysis_kind='directivity_plot',computation_method='native_DirectivityPlot_text',
        ies_file=source.group(1).strip(),peak_intensity_candela=peak_value,total_luminous_flux_lumens=flux_value,
        normalization='native report normalized candela; peak equals 1',angle_unit='degrees',rows=rows,series=series,grids=[],structured_data_available=True)


def parse_polarization_transmission_fan(text):
    fields=[];wavelengths=[];rows=[];section=None
    number=r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?'
    if not re.search(r'非偏振|unpolarized',text,re.IGNORECASE):
        raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','TransmissionFan报告未确认非偏振输入。')
    for line_no,line in enumerate(text.splitlines(),1):
        match=re.search(r'(子午|弧矢).*?视场号\s*(\d+)\s*=\s*('+number+r')\s*\(度\)',line)
        if match:
            section=dict(fan='tangential' if match.group(1)=='子午' else 'sagittal',field_number=int(match.group(2)),field_deg=float(match.group(3)),rows=[])
            if section['field_number']<1 or not math.isfinite(section['field_deg']):
                raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan视场身份无效。',source_line=line_no,raw=line)
            if any((f['fan'],f['field_number'])==(section['fan'],section['field_number']) for f in fields):
                raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan方向/视场重复。',source_line=line_no,raw=line)
            fields.append(section);wavelengths=[];continue
        if section is None:continue
        if not line.strip():continue
        header=re.match(r'^\s*(?:光瞳|Pupil)\s+(.+?)\s*$',line,re.IGNORECASE)
        if header:
            if wavelengths or section['rows']:
                raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan波长标题重复。',source_line=line_no,raw=line)
            try:
                wavelengths=[float(x) for x in header.group(1).split()]
            except ValueError as exc:
                raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan波长标题无效。',source_line=line_no,raw=line) from exc
            if not wavelengths or any(not math.isfinite(w) or w<=0 for w in wavelengths) or len(set(wavelengths))!=len(wavelengths):
                raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan波长须为不重复的正有限值。',source_line=line_no,raw=line)
            continue
        pupil_match=re.match(r'^\s*('+number+r')(?=\s|-{3,}|$)',line)
        if not pupil_match:
            raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan数据行无效。',source_line=line_no,raw=line)
        tail=line[pupil_match.end():]
        values=[];end=0
        for token in re.finditer(r'-{3,}|'+number,tail):
            if tail[end:token.start()].strip():
                raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan数据行无效。',source_line=line_no,raw=line)
            values.append(None if token[0].startswith('---') else float(token[0]))
            end=token.end()
        pupil=float(pupil_match[1])
        if tail[end:].strip() or not wavelengths or len(values)!=len(wavelengths) or not math.isfinite(pupil) or any(v is not None and not math.isfinite(v) for v in values):
            raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan数据列数或有限值无效。',source_line=line_no,raw=line)
        if not -1.000001<=pupil<=1.000001 or any(v is not None and v<0 for v in values) or (section['rows'] and pupil<=section['rows'][-1]['pupil']):
            raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan瞳坐标须递增且透射非负。',source_line=line_no,raw=line)
        row=dict(index=len(rows),fan=section['fan'],field_number=section['field_number'],field_deg=section['field_deg'],
            pupil=pupil,wavelengths_um=wavelengths,transmission=values,invalid_count=sum(v is None for v in values),source_line=line_no,raw=line)
        section['rows'].append(row);rows.append(row)
    if not fields or any(not f['rows'] for f in fields):
        raise ZemaxError('UNRECOGNIZED_RESULT_FORMAT','TransmissionFan报告缺少方向、视场或瞳坐标曲线。',sections=len(fields))
    wave_sets={tuple(f['rows'][0]['wavelengths_um']) for f in fields}
    if len(wave_sets)!=1:raise ZemaxError('INVALID_RESULT_DATA','TransmissionFan不同曲线的波长轴不一致。')
    wavelengths=list(next(iter(wave_sets)))
    series=[]
    for index,f in enumerate(fields):
        for wi,wave in enumerate(wavelengths):
            series.append(dict(series=len(series),description=f"{f['fan']} transmission at field {f['field_number']}",
                fan=f['fan'],field_number=f['field_number'],field_deg=f['field_deg'],wavelength_um=wave,
                x_label='Normalized pupil',labels=['Normalized intensity'],x=[r['pupil'] for r in f['rows']],
                y=[[r['transmission'][wi]] for r in f['rows']],x_unit='normalized pupil',
                y_unit='dimensionless normalized intensity',invalid_count=sum(r['transmission'][wi] is None for r in f['rows'])))
    return dict(analysis_kind='polarization_transmission_fan',computation_method='native_TransmissionFan_text',
        polarization='unpolarized',intensity_unit='dimensionless normalized intensity',wavelengths_um=wavelengths,
        rows=rows,series=series,grids=[],structured_data_available=True)
