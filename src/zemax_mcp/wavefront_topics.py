"""Dedicated Zernike field scan and interferogram settings."""
import math,re
from .errors import ZemaxError


def configure_zernike_field(q, put):
    terms=list(range(1,38 if q.coefficient_type=='Fringe'else 232))if q.coefficients==[0]else q.coefficients
    for name, value in [('ZernikeCoefficientType', q.coefficient_type),
                        ('FieldScanDirection', q.field_scan), ('SampleSize', q.sampling),
                        ('ObscurationFactor', q.obscuration), ('FieldDensity', q.field_density),
                        ('Coefficients', ','.join(map(str, terms))),
                        ('ScaleMinimum', q.scale_minimum), ('ScaleMaximum', q.scale_maximum)]:
        put(name, value)


def check_interferogram_configurations(q, count):
    for name in ('beam_1', 'beam_2'):
        beam = getattr(q, name)
        if beam != 'Reference' and int(beam.removeprefix('Configuration_')) > count:
            raise ZemaxError('INDEX_OUT_OF_RANGE', 'Interferogram beam configuration exceeds model count.',
                             setting=name, requested=beam, configuration_count=count)


def configure_interferogram(q, put):
    for name, value in [('Sampling', q.sampling), ('ShowAs', q.show_as),
                        ('Beam_1', q.beam_1), ('Beam_2', q.beam_2),
                        ('Ref_Beam_1_To_Vertex', q.ref_beam_1_to_vertex),
                        ('Ref_Beam_2_To_Vertex', q.ref_beam_2_to_vertex),
                        ('UseExitPupil', q.use_exit_pupil), ('ConsiderOPL', q.consider_opl),
                        ('ScaleFactor', q.scale_factor), ('X_Tilt', q.x_tilt), ('Y_Tilt', q.y_tilt),
                        ('Subaperture_X', q.subaperture_x), ('Subaperture_Y', q.subaperture_y),
                        ('Subaperture_R', q.subaperture_radius)]:
        put(name, value)
    if q.contour_format is not None:
        put('ContourFormat', q.contour_format)


def describe_wavefront_topic(data, request):
    kind = request['kind']
    data['analysis_kind'] = kind
    if kind == 'zernike_coefficients_vs_field':
        if not data.get('series'):
            raise ZemaxError('NO_RESULT_DATA', 'Zernike field scan returned no native series.')
        data.update(coefficient_type=request['coefficient_type'], requested_coefficients=request['coefficients'],
                    coefficient_unit='waves', field_axis_source='native XLabel and text; native field scale acceptance pending')
        if all(s.get('source')=='native formatted text'for s in data['series']):
            data['field_axis_source']='native field distance with explicit scan direction; displayed digits retained'
            for series in data['series']:
                direction=request['field_scan'];sign=-1 if direction.startswith('Minus')else 1
                series['native_x']=list(series['x'])
                series['x']=[sign*v for v in series['x']]
                series['field_coordinates']=[dict(x=v if direction.endswith('X')else 0,y=v if direction.endswith('Y')else 0)for v in series['x']]
                series['axis_definition']='signed field coordinate; native_x is nonnegative scan distance'
                series['field_scan']=direction
        for series in data['series']:
            series.update(value_units=['waves']*len(series['labels']),
                          native_labels=list(series['labels']), coefficient_mapping=series.get('term_mapping_source','native labels; no positional term inference'))
    else:
        data.update(beam_1=request['beam_1'], beam_2=request['beam_2'],
                    pupil_coordinates='exit pupil shape' if request['use_exit_pupil'] else 'normalized entrance pupil',
                    scale_factor_unit='fringes per wave OPD', tilt_unit='fringes',
                    value_unit_source='normalized interference intensity; independent real-ray OPD/cosine reference',
                    phase_convention='beam 1 OPD minus beam 2 OPD; added tilt is half X_Tilt*px plus half Y_Tilt*py in waves; ConsiderOPL adds chief path2-path1 (controlled air-path reference)',
                    validity_source='native arrays contain finite pupil-exterior fill values; invalid_count counts nonfinite values, not ray validity')
        for grid in data.get('grids',[]):
            nx,ny=grid['nx'],grid['ny']
            if len(grid['values'])!=ny or any(len(row)!=nx for row in grid['values']):
                raise ZemaxError('INVALID_RESULT_DATA','Interferogram native grid dimensions do not match values.',nx=nx,ny=ny)
            grid['native_axes']={key:grid.get(key) for key in ('x_label','y_label','value_label','min_x','min_y','dx','dy')}
            grid.update(x_label='Native pupil display X',y_label='Native pupil display Y',
                        value_label='Interference intensity',value_unit='dimensionless',
                        x_unit='native normalized display coordinate',y_unit='native normalized display coordinate',
                        array_order='values[y][x]',value_quantity='normalized interference intensity',
                        pupil_validity='native trace-validity mask unavailable; finite exterior fill retained')


def zernike_field_text_series(text,requested,applied=None):
    lines=text.splitlines()
    header=next((i for i,line in enumerate(lines)if re.match(r'^\s*(?:视场|Field)\s*[:：]\s*\d',line)),None)
    if header is None and not applied:return None
    terms=list(applied)if header is None else[int(v)for v in re.findall(r'\d+',lines[header])]
    if not terms or len(set(terms))!=len(terms):
        raise ZemaxError('INVALID_RESULT_DATA','Zernike视场表的系数标题无效。',header=None if header is None else lines[header])
    if requested!=[0]and terms!=requested:
        raise ZemaxError('INVALID_RESULT_DATA','Zernike视场表与请求系数不匹配。',requested=requested,native_terms=terms)
    rows=[]
    for line in (lines if header is None else lines[header+1:]):
        if header is None and not re.match(r'^\s*[-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?\s+[-+]?\d',line):continue
        if not line.strip():continue
        try:row=[float(v)for v in line.split()]
        except ValueError as exc:
            raise ZemaxError('INVALID_RESULT_DATA','Zernike视场表包含非数值行。',line=line)from exc
        if len(row)!=len(terms)+1 or not all(math.isfinite(v)for v in row):
            raise ZemaxError('INVALID_RESULT_DATA','Zernike视场表列数或数值无效。',line=line)
        rows.append(row)
    if not rows:return None
    return dict(series=0,description='native Zernike field text table',x_label='native physical field',
                labels=['Z'+str(t)for t in terms],native_term_header=None if header is None else lines[header],coefficient_terms=terms,
                term_mapping_source='native term header'if header is not None else'confirmed ordered Coefficients setting; native header omitted',
                x=[r[0]for r in rows],y=[r[1:]for r in rows],invalid_count=0,
                source='native formatted text',precision='native displayed scientific digits',
                field_density_definition='native interval count; N intervals produce N+1 points')
