"""Native-text polarization topics and selectable formal pupil transmission.

The installed topic objects expose AS_Default settings. Default requests retain
native reports; pupil transmission selectors use an explicit normalized batch
ray-trace path with its own recorded inputs and result source.
"""
import math
import re

from typing import Literal, Annotated
from pydantic import Field

from .errors import ZemaxError
from .schema import Request, Index
from .transmission_fan import FanJones

TOPIC_KINDS = ('phase_aberration', 'polarization_ray_trace', 'polarization_transmission', 'fiber_coupling_settings')

NUMBER = r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[EeDd][-+]?\d+)?'
NUMBER_RE = re.compile(NUMBER)
BAD_NUMBER_RE = re.compile(r'(?i)1\.#(?:inf|ind|qnan|snan)|\b(?:nan|inf)\b')


class PhaseAberration(Request):
    """Native polarized phase-aberration pupil table; the report states its own inputs."""
    kind: Literal['phase_aberration']
    method: Literal['auto', 'native', 'system_copy'] = 'auto'
    field: Annotated[int, Field(strict=True, ge=1)] | None = None
    wavelength: Annotated[int, Field(strict=True, ge=1)] | None = None
    polarization: FanJones | None = None


class PolarizationRayTrace(Request):
    """Native polarization report or explicitly selected CODA operand ray data."""
    kind: Literal['polarization_ray_trace']
    method: Literal['auto', 'native', 'operand'] = 'auto'
    field: Annotated[int, Field(ge=1)] = 1
    wavelength: Annotated[int, Field(ge=1)] = 1
    surface: Index = 0
    pupil_x: Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)] = 0
    pupil_y: Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)] = 1


class PolarizationTransmission(Request):
    """Native report by default; selectors use formal normalized pupil tracing."""
    kind: Literal['polarization_transmission']
    method: Literal['auto','native','ray_trace'] = 'auto'
    field: Index = 0
    wavelength: Index = 0
    sampling: Literal[8,16,32,64,128] = 32
    polarization: FanJones | None = None
    include_chief_ray: bool = True


class FiberCouplingSettings(Request):
    """Native fiber-coupling efficiencies; the report states receiver NA, position and units."""
    kind: Literal['fiber_coupling_settings']
    method: Literal['auto', 'native', 'operand'] = 'auto'
    sampling: Literal[32, 64, 128, 256] = 64
    field: Annotated[int, Field(ge=1)] = 1
    wavelength: Annotated[int, Field(ge=1)] = 1
    ignore_source: bool = True
    source_na: Annotated[float, Field(gt=0, allow_inf_nan=False)] = .1
    receiver_na: Annotated[float, Field(gt=0, allow_inf_nan=False)] = .1
    integration: Literal['fast', 'huygens'] = 'huygens'
    use_polarization: bool = False


def _numbers(line, where=None):
    """Extract every finite number from one native line, rejecting native NaN/Inf spellings."""
    if BAD_NUMBER_RE.search(line):
        raise ZemaxError('INVALID_RESULT_DATA', '原生文本包含非有限数值。', line=line.strip()[:200], where=where)
    values = [float(token.replace('D', 'E').replace('d', 'e')) for token in NUMBER_RE.findall(line)]
    if not all(math.isfinite(value) for value in values):
        raise ZemaxError('INVALID_RESULT_DATA', '原生文本包含非有限数值。', line=line.strip()[:200], where=where)
    return values


def _one(line, where):
    values = _numbers(line, where)
    if len(values) != 1:
        raise ZemaxError('INVALID_RESULT_DATA', '原生文本行数值个数不符。', where=where, count=len(values), line=line.strip()[:200])
    return values[0]


_COLON_RE = re.compile(r'[:：]')


def _split_colon(line):
    """Split at the first ASCII or full-width colon; native reports use both."""
    match = _COLON_RE.search(line)
    if match is None:
        return None, line
    return line[:match.start()], line[match.end():]


def _label(line):
    """Native label without whitespace; continuation lines have an empty label."""
    head, tail = _split_colon(line)
    if head is None:
        return None, line
    return re.sub(r'[\s\u3000]+', '', head), tail


def _value_part(line):
    head, tail = _split_colon(line)
    return tail if head is not None else ''

# ---------------------------------------------------------------------------
# Phase aberration
# ---------------------------------------------------------------------------

_PHASE_HEADER_RES = (
    ('wavelength', re.compile(r'^(?:波长|Wavelength)\s*[:：]', re.I)),
    ('field', re.compile(r'^(?:视场Pos|Field\s*Pos|Field)\s*[:：]', re.I)),
    ('jx', re.compile(r'^Jx\s*[:：]', re.I)),
    ('jy', re.compile(r'^Jy\s*[:：]', re.I)),
    ('x_phase', re.compile(r'^(?:X-?相位|X\s*Phase)\s*[:：]', re.I)),
    ('y_phase', re.compile(r'^(?:Y-?相位|Y\s*Phase)\s*[:：]', re.I)),
)
_PHASE_TABLE_RE = re.compile(r'\bP\b.*(?:相位|Phase)', re.I)
_PHASE_SECTIONS_RE = re.compile(r'(弧矢|子午|Sagittal|Tangential)', re.I)
_SECTION_NAMES = {'弧矢': 'sagittal', '子午': 'tangential', 'sagittal': 'sagittal', 'tangential': 'tangential'}
_UNIT_NAMES = {'度': 'degrees', 'deg': 'degrees', 'degree': 'degrees', 'degrees': 'degrees', '°': 'degrees',
               '毫米': 'millimeters', 'mm': 'millimeters', 'millimeter': 'millimeters', 'millimeters': 'millimeters',
               '厘米': 'centimeters', 'cm': 'centimeters', '英寸': 'inches', 'in': 'inches'}
_FIELD_TYPE_UNITS = {'Angle': 'degrees', 'ObjectHeight': 'object height in system lens units',
                     'ParaxialImageHeight': 'paraxial image height in system lens units',
                     'RealImageHeight': 'real image height in system lens units'}


def resolve_field_unit(text, system_settings=None):
    """Resolve the field-coordinate unit from the native header, else the system field type.

    The native report prints the unit in parentheses when it prints one at all, and the
    system field type is only a fallback. When neither is available the unit stays unknown
    instead of being labelled degrees: an object-height field is not an angle.
    """
    raw = None
    if text:
        match = re.search(r'[(（]\s*([^)）]+?)\s*[)）]', text)
        if match:
            raw = match.group(1)
    if raw:
        return dict(unit=_UNIT_NAMES.get(raw.strip().lower(), raw.strip()), unit_raw=raw.strip(),
                    unit_source='native report header parentheses')
    field_type = (system_settings or {}).get('field_type') if system_settings else None
    if field_type:
        return dict(unit=_FIELD_TYPE_UNITS.get(str(field_type), str(field_type)), unit_raw=None,
                    unit_source=f'system field_type {field_type}; native header prints no unit')
    return dict(unit=None, unit_raw=None,
                unit_source='unknown: native header prints no unit and system field_type is unavailable')


def parse_phase_aberration_text(text, context=None):
    """Parse the native phase-aberration report into a pupil table plus its declared inputs.

    The native report prints no unit. The manual (2024 R2, \"Phase Aberration\") defines the
    quantity by example: an E-field phase change from 45 to 135 degrees is \"one-quarter
    wave\", so the printed values are waves. That basis is recorded but not treated as
    verified until the native reference comparison runs.
    """
    lines = text.splitlines()
    header = {}
    header_lines = []
    raw_header = {}
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        for name, pattern in _PHASE_HEADER_RES:
            if name in header or not pattern.match(stripped):
                continue
            values = _numbers(_value_part(stripped), where=name)
            if not values:
                break
            header[name] = values
            raw_header[name] = stripped
            header_lines.append(stripped)
            break
    missing = [name for name, _ in _PHASE_HEADER_RES if name not in header]
    if missing:
        raise ZemaxError('INVALID_RESULT_DATA', '原生文本不是偏振相位像差报告：缺少输入头字段。', missing=missing, native_lines=lines[:12])

    wavelength_um = _exactly_one(header['wavelength'], 'wavelength')
    field_values = header['field']
    unit_info = resolve_field_unit(raw_header.get('field'), (context or {}).get('system_settings'))
    if len(field_values) == 1:
        field_position = dict(x=None, y=field_values[0], **unit_info)
    elif len(field_values) == 2:
        field_position = dict(x=field_values[0], y=field_values[1], **unit_info)
    else:
        raise ZemaxError('INVALID_RESULT_DATA', '视场坐标个数无法解释。', values=field_values)
    jones = dict(jx=_exactly_one(header['jx'], 'Jx'), jy=_exactly_one(header['jy'], 'Jy'),
                 x_phase_deg=_exactly_one(header['x_phase'], 'X phase'), y_phase_deg=_exactly_one(header['y_phase'], 'Y phase'))

    table_index = None
    for index, line in enumerate(lines):
        if _PHASE_TABLE_RE.search(line) and count_pupil_columns(line) >= 5:
            table_index = index
            break
    if table_index is None:
        raise ZemaxError('INVALID_RESULT_DATA', '原生文本缺少相位表列标题。', native_lines=lines[:16])
    section_order = ['sagittal', 'tangential']
    for line in lines[max(0, table_index - 4):table_index]:
        found = [_SECTION_NAMES.get(match.group(1).strip().lower()) for match in _PHASE_SECTIONS_RE.finditer(line)]
        found = [name for name in found if name]
        if len(found) >= 2:
            section_order = found[:2]
            break

    rows = []
    for offset, line in enumerate(lines[table_index + 1:], start=table_index + 2):
        stripped = line.strip()
        if not stripped:
            if rows:
                break
            continue
        values = _numbers(stripped, where='phase table')
        if len(values) != 5:
            if rows:
                break
            raise ZemaxError('INVALID_RESULT_DATA', '相位表行不是 5 列数值。', line_number=offset, values=values)
        first, second = values[1:3], values[3:5]
        sections = {section_order[0]: first, section_order[1]: second}
        rows.append(dict(index=len(rows), pupil=values[0],
                         sagittal=dict(x_phase=sections['sagittal'][0], y_phase=sections['sagittal'][1]),
                         tangential=dict(x_phase=sections['tangential'][0], y_phase=sections['tangential'][1]),
                         raw_line=stripped))
    if not rows:
        raise ZemaxError('NO_RESULT_DATA', '偏振相位像差报告没有数值行。', native_lines=lines[:16])
    if len(rows) < 3:
        raise ZemaxError('INVALID_RESULT_DATA', '相位表采样点不足。', point_count=len(rows))
    pupils = [row['pupil'] for row in rows]
    if any(pupil < -1.000001 or pupil > 1.000001 for pupil in pupils):
        raise ZemaxError('INVALID_RESULT_DATA', '相位表瞳坐标超出 -1..1。', minimum=min(pupils), maximum=max(pupils))
    if any(later <= earlier for earlier, later in zip(pupils, pupils[1:])):
        raise ZemaxError('INVALID_RESULT_DATA', '相位表瞳坐标未严格递增。', first_pupils=pupils[:5])

    series = []
    for section in ('sagittal', 'tangential'):
        for component in ('x_phase', 'y_phase'):
            series.append(dict(series=len(series),
                               description=f'{section} pupil {component.replace("_", " ")}',
                               x_label='Normalized pupil', labels=[f'{section}_{component}'],
                               x=[row['pupil'] for row in rows],
                               y=[[row[section][component]] for row in rows],
                               x_unit='normalized pupil', y_unit='waves', value_units=['waves'],
                               invalid_count=0))
    return {
        'analysis_kind': 'phase_aberration',
        'computation_method': 'native PhaseAberration UTF-16 report (AS_Default settings, AR_Default results)',
        'input_header': dict(wavelength_um=wavelength_um, field_position=field_position, jones=jones),
        'input_header_lines': header_lines,
        'input_header_source': 'native report header; the analysis settings object exposes no writable selectors',
        'phase_unit': 'waves',
        'phase_unit_verified': False,
        'phase_unit_source': 'manual 2024 R2 phase-aberration definition: a 90 degree E-field phase change is one-quarter wave; the native report prints no unit label',
        'phase_reference': 'chief ray at the image surface; the native manual describes interpolating its phase from two rays on either side to handle zero-intensity components; the phase is indeterminate where the component intensity is zero',
        'phase_sign_convention': 'native signed value; sign convention not independently verified',
        'section_order': section_order,
        'columns': ['pupil', 'sagittal_x_phase', 'sagittal_y_phase', 'tangential_x_phase', 'tangential_y_phase'],
        'rows': rows,
        'series': series,
        'units': dict(pupil='normalized entrance-pupil coordinate', phase='waves (declared, not native-labelled)',
                      field_position=unit_info['unit'],
                      wavelength='micrometers'),
        'units_source': 'manual p.903 for waves; native header parentheses for the field unit when printed, otherwise the system field type; native table prints no unit',
        'coordinate_definition': 'normalized pupil coordinate from -1 to +1 along the sagittal and tangential sections; the native table lists both sections side by side',
        'selection': _selection(context, writable=[]),
        'structured_data_available': True,
    }


def count_pupil_columns(line):
    """Count the numeric-looking column labels of a heading line (P, X, Y, X, Y)."""
    return len(re.findall(r'(?<![A-Za-z])(?:P|X|Y)(?![A-Za-z])', line))


def _exactly_one(values, where):
    if len(values) != 1:
        raise ZemaxError('INVALID_RESULT_DATA', '原生输入头数值个数不符。', where=where, values=values)
    return values[0]


def _selection(context, writable):
    context = context or {}
    return dict(requested_kind=context.get('requested_kind'),
                writable_selectors=writable,
                native_settings_type=context.get('native_settings_type', 'AS_Default'),
                native_settings_readback=context.get('native_settings'),
                readback_source='native report input header',
                selection_status='native defaults only; no documented writable selector exists for this analysis')

# ---------------------------------------------------------------------------
# Polarization ray trace
# ---------------------------------------------------------------------------

_RT_LABEL_RES = (
    (r'(tau)', 'path_length'),
    (r'(alpha)', 'internal_absorption'),
    (r'(IT)', 'internal_transmittance'),
    (r'(pc,ps)', 'propagation_phase'),
    (r'(x,y,z)', 'surface_coordinates'),
    (r'(l1,m1,n1)', 'incident_direction'),
    (r'(l2,m2,n2)', 'exit_direction'),
    (r'(ln,mn,nn)', 'normal'),
    (r'(Rs,Rp)', 'reflectance'),
    (r'(Ts,Tp)', 'transmittance'),
    (r'(As,Ap)', 'absorptance'),
    (r'(D)', 'diattenuation'),
    (r'(I1)', 'intensity_before'),
    (r'(Pxy)', 'phase_difference_xy'),
    (r'(EM,Em)', 'ellipse_axes'),
    (r'(Exr,Eyr,Ezr)', 'e_before_coating_xyz'),
    (r'(Exi,Eyi,Ezi)', None),
    (r'(Esr,Epr)', None),
    (r'(Esi,Epi)', None),
    (r'(Ax,Ay,Az)', 'amplitude_xyz'),
    (r'(Px,Py,Pz)', 'phase_xyz'),
)
_RT_PREFIXES = (
    ('新S弧矢', 'new_s_vector', 'vector3'),
    ('新P弧矢', 'new_p_vector', 'vector3'),
    ('S弧矢', 's_vector', 'vector3'),
    ('P弧矢', 'p_vector', 'vector3'),
    ('入射光线的余弦角', 'incident_angle', 'angle'),
    ('出射光线的余弦角', 'exit_angle', 'angle'),
    ('膜层', 'coating', 'text'),
    ('在膜层前面的E电场(xyz)', 'e_before_coating_xyz', 'complex3'),
    ('在膜层前面的E电场(s&p)', 'e_before_coating_sp', 'complex_vec'),
    ('在膜层后的电场', 'e_after_coating_sp', 'complex_vec'),
    ('E电场后', 'e_after_coating_xyz', 'complex3'),
    ('场振幅反射S极', 'field_amplitude_reflection_s', 'complex2'),
    ('场振幅反射P极', 'field_amplitude_reflection_p', 'complex2'),
    ('场振幅透射S极', 'field_amplitude_transmission_s', 'complex2'),
    ('场振幅透射P极', 'field_amplitude_transmission_p', 'complex2'),
    ('场反射相位', 'field_reflection_phase', 'pair'),
    ('场反射迟缓(P-S+pi)', 'field_reflection_retardance_pi', 'angle'),
    ('场反射迟缓(P-S)', 'field_reflection_retardance', 'angle'),
    ('场透射相位', 'field_transmission_phase', 'pair'),
    ('场透射迟缓(P-S+pi)', 'field_transmission_retardance_pi', 'angle'),
    ('场透射迟缓(P-S)', 'field_transmission_retardance', 'angle'),
    ('光线振幅反射S极', 'ray_amplitude_reflection_s', 'complex2'),
    ('光线振幅反射P极', 'ray_amplitude_reflection_p', 'complex2'),
    ('光线振幅透射S极', 'ray_amplitude_transmission_s', 'complex2'),
    ('光线振幅透射P极', 'ray_amplitude_transmission_p', 'complex2'),
    ('光线反射相位', 'ray_reflection_phase', 'pair'),
    ('光线反射延迟(P-S+pi)', 'ray_reflection_retardance_pi', 'angle'),
    ('光线反射延迟(P-S)', 'ray_reflection_retardance', 'angle'),
    ('光线透射相位', 'ray_transmission_phase', 'pair'),
    ('光线透射延迟(P-S+pi)', 'ray_transmission_retardance_pi', 'angle'),
    ('光线透射延迟(P-S)', 'ray_transmission_retardance', 'angle'),
    ('X,Y和Z方向的振幅', 'amplitude_xyz', 'vector3'),
    ('X,Y和Z方向的相位', 'phase_xyz', 'vector3'),
    ('XY偏振椭圆的角度', 'ellipse_angle', 'angle'),
    ('长，短半轴XY椭圆', 'ellipse_axes', 'pair'),
    ('输出光线强度', 'intensity_after', 'scalar'),
)
_RT_REQUIRED = ('internal_transmittance', 'intensity_before', 'intensity_after', 'transmittance', 'reflectance')


def parse_polarization_ray_trace_text(text, context=None):
    """Parse the native single-ray polarization report: header, per-surface data and total."""
    lines = text.splitlines()
    header = {}
    header_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('追迹光线到表面') or stripped.startswith('Ray trace to surface'):
            break
        match = re.match(r'^(透镜单位|Lens\s*units)\s*[:：]', stripped, re.I)
        if match:
            header['lens_units'] = _value_part(stripped).strip().rstrip('.')
            header_lines.append(stripped)
            continue
        match = re.match(r'^(波长|Wavelength)\s*[:：]', stripped, re.I)
        if match:
            header['wavelength_um'] = _exactly_one(_numbers(_value_part(stripped), where='wavelength'), 'wavelength')
            header_lines.append(stripped)
            continue
        match = re.match(r'^(?:归一化)?(X|Y)\s*(视场|光瞳)坐标\s*\((Hx|Hy|Px|Py)\)\s*[:：]', stripped, re.I)
        if match:
            header[match.group(3).lower()] = _exactly_one(_numbers(_value_part(stripped), where=match.group(3)), match.group(3))
            header_lines.append(stripped)
            continue
        match = re.match(r'^(X|Y)\s*[-－]?\s*(视场|相位)\s*[:：]', stripped)
        if match:
            key = ('jx' if match.group(2) == '视场' else 'x_phase') if match.group(1) == 'X' else ('jy' if match.group(2) == '视场' else 'y_phase')
            header[key] = _exactly_one(_numbers(_value_part(stripped), where=key), key)
            header_lines.append(stripped)
            continue
    for key in ('wavelength_um', 'jx', 'jy', 'x_phase', 'y_phase'):
        if key not in header:
            raise ZemaxError('INVALID_RESULT_DATA', '原生文本不是偏振光线追迹报告：缺少输入头字段。', missing=key, native_lines=lines[:18])

    blocks = []
    current = None
    previous = None
    for line in lines:
        stripped = line.strip()
        match = re.match(r'^追迹光线到表面\s*(\d+)\s*[:：]?', stripped)
        if match:
            current = dict(surface=int(match.group(1)), fields={}, raw_lines=[stripped])
            blocks.append(current)
            previous = None
            continue
        if current is None:
            continue
        if not stripped:
            continue
        if stripped.startswith('总结') or stripped.startswith('Summary'):
            break
        current['raw_lines'].append(stripped)
        label, _ = _label(line)
        if label is not None and (label == '' or (label.startswith('(') and label.endswith(')'))):
            # Native continuation lines carry only the bracketed abbreviation, e.g. "(Exi,Eyi,Ezi):".
            if previous is not None:
                _attach_continuation(current['fields'][previous], stripped)
            continue
        if label is None:
            continue
        name = _rt_field_name(label)
        if name is None:
            continue
        _store_rt_field(current['fields'], name, stripped)
        previous = name if name in ('e_before_coating_xyz', 'e_before_coating_sp', 'e_after_coating_xyz', 'e_after_coating_sp') else None

    if not blocks:
        raise ZemaxError('NO_RESULT_DATA', '偏振光线追迹报告没有表面数据块。', native_lines=lines[:18])
    surfaces = [block['surface'] for block in blocks]
    if len(set(surfaces)) != len(surfaces):
        raise ZemaxError('INVALID_RESULT_DATA', '偏振光线追迹报告表面编号重复。', surfaces=surfaces)
    if any(later <= earlier for earlier, later in zip(surfaces, surfaces[1:])):
        raise ZemaxError('INVALID_RESULT_DATA', '偏振光线追迹报告表面编号未递增。', surfaces=surfaces)
    for block in blocks:
        missing = [name for name in _RT_REQUIRED if name not in block['fields']]
        if missing:
            raise ZemaxError('INVALID_RESULT_DATA', '偏振光线追迹表面块缺少必要字段。', surface=block['surface'], missing=missing)

    total = None
    for line in lines:
        if '总透射强度' in line or 'Total transmitted intensity' in line:
            total = _exactly_one(_numbers(_value_part(line), where='total transmission'), 'total transmission')
            break
    if total is None:
        raise ZemaxError('NO_RESULT_DATA', '偏振光线追迹报告缺少总透射强度。', native_lines=lines[-8:])

    rows = [dict(index=index, surface=block['surface'], **block['fields'], raw_lines=block['raw_lines']) for index, block in enumerate(blocks)]
    return {
        'analysis_kind': 'polarization_ray_trace',
        'computation_method': 'native PolarizationRayTrace UTF-16 report (AS_Default settings, AR_Default results)',
        'input_header': dict(lens_units=header.get('lens_units'), wavelength_um=header['wavelength_um'],
                             pupil=dict(hx=header.get('hx'), hy=header.get('hy'), px=header.get('px'), py=header.get('py')),
                             jones=dict(jx=header['jx'], jy=header['jy'], x_phase_deg=header['x_phase'], y_phase_deg=header['y_phase']),
                             global_coordinates=False),
        'input_header_lines': header_lines,
        'input_header_source': 'native report header; the analysis settings object exposes no writable selectors',
        'coordinate_definition': 'surface local coordinates and direction cosines as printed; the report declares all coordinates and cosines local',
        'columns': ['surface', 'path_length']
                   + [name for name in ('internal_absorption', 'internal_transmittance', 'propagation_phase', 'surface_coordinates',
                                        'incident_direction', 'incident_angle', 'exit_angle', 'exit_direction', 'normal',
                                        's_vector', 'p_vector', 'e_before_coating_xyz', 'e_before_coating_sp', 'intensity_before',
                                        'coating', 'reflectance', 'transmittance', 'absorptance', 'diattenuation',
                                        'field_amplitude_reflection_s', 'field_amplitude_reflection_p',
                                        'field_amplitude_transmission_s', 'field_amplitude_transmission_p',
                                        'field_reflection_phase', 'field_reflection_retardance', 'field_reflection_retardance_pi',
                                        'field_transmission_phase', 'field_transmission_retardance', 'field_transmission_retardance_pi',
                                        'ray_amplitude_reflection_s', 'ray_amplitude_reflection_p',
                                        'ray_amplitude_transmission_s', 'ray_amplitude_transmission_p',
                                        'ray_reflection_phase', 'ray_reflection_retardance', 'ray_reflection_retardance_pi',
                                        'ray_transmission_phase', 'ray_transmission_retardance', 'ray_transmission_retardance_pi',
                                        'e_after_coating_sp', 'intensity_after', 'new_s_vector', 'new_p_vector',
                                        'e_after_coating_xyz', 'amplitude_xyz', 'phase_xyz', 'phase_difference_xy',
                                        'ellipse_axes', 'ellipse_angle')],
        'rows': rows,
        'total_transmission': total,
        'units': dict(path_length='lens units', internal_absorption='per lens unit', internal_transmittance='dimensionless fraction',
                      propagation_phase='native propagation phase pair (pc,ps) of the field factor', reflectance='intensity fraction',
                      transmittance='intensity fraction', absorptance='intensity fraction', diattenuation='dimensionless',
                      phase='radians unless the line prints a degree equivalent', angles='degrees in the parenthesised column',
                      field_amplitude='dimensionless complex field amplitude before/after coating', ray_amplitude='native ray amplitude',
                      ellipse='major/minor semi-axis amplitudes of the local XY electric-field projection', total_transmission='dimensionless intensity fraction'),
        'units_source': 'native line labels; degree equivalents are printed in parentheses',
        'phase_convention': 'native phase values are printed in radians with a degree equivalent where available; the absolute reference of each phase column is not labelled and is not verified',
        'selection': _selection(context, writable=[]),
        'structured_data_available': True,
    }


def _rt_field_name(label):
    """Resolve a native label to a result field.

    Chinese label prefixes win over bracketed abbreviations because several abbreviations
    repeat across labels: ``(Exr,Eyr,Ezr)`` appears both in the before-coating field and in
    the final ``E电场后`` field, and ``(Esr,Epr)`` appears both before and after the coating.
    """
    for prefix, name, _kind in _RT_PREFIXES:
        if label.startswith(prefix):
            return name
    for token, name in _RT_LABEL_RES:
        if name and token in label:
            return name
    return None


def _rt_field_kind(name):
    for prefix, candidate, kind in _RT_PREFIXES:
        if candidate == name:
            return kind
    return 'numbers'


def _store_rt_field(fields, name, line):
    kind = _rt_field_kind(name)
    values = _numbers(_value_part(line), where=name)
    if kind == 'text':
        fields[name] = _value_part(line).strip()
        return
    if not values:
        raise ZemaxError('INVALID_RESULT_DATA', '原生字段没有数值。', field=name, line=line.strip()[:200])
    if kind == 'complex3':
        if len(values) != 3:
            raise ZemaxError('INVALID_RESULT_DATA', '原生三元复场字段实部个数不符。', field=name, values=values)
        fields[name] = dict(real=values, imag=None)
        return
    if kind == 'complex_vec':
        # (s&p) fields print two real parts and a second line with the two imaginary parts.
        if len(values) != 2:
            raise ZemaxError('INVALID_RESULT_DATA', '原生 s&p 复场字段实部个数不符。', field=name, values=values)
        fields[name] = dict(real=values, imag=None)
        return
    if kind == 'complex2':
        if len(values) != 2:
            raise ZemaxError('INVALID_RESULT_DATA', '原生复振幅字段个数不符。', field=name, values=values)
        fields[name] = dict(real=values[0], imag=values[1])
        return
    if kind == 'angle':
        fields[name] = dict(value=values[0], deg=_degree(values, name))
        return
    if kind == 'vector3':
        if len(values) != 3:
            raise ZemaxError('INVALID_RESULT_DATA', '原生三元向量字段个数不符。', field=name, values=values)
        fields[name] = values
        return
    fields[name] = values[0] if len(values) == 1 else values


def _degree(values, name):
    for index in (1, 2, 3):
        if len(values) > index and abs(values[index]) > 180.000001:
            raise ZemaxError('INVALID_RESULT_DATA', '原生角度列超出 ±180 度。', field=name, values=values)
    return values[1] if len(values) > 1 else None


def _attach_continuation(field, line):
    if not isinstance(field, dict) or field.get('imag') is not None:
        raise ZemaxError('INVALID_RESULT_DATA', '原生复场续行没有对应的实部。', line=line.strip()[:200])
    values = _numbers(_value_part(line), where='complex imaginary part')
    if len(values) != len(field['real']):
        raise ZemaxError('INVALID_RESULT_DATA', '原生复场续行个数与实部不一致。', real=field['real'], imag=values)
    field['imag'] = values

# ---------------------------------------------------------------------------
# Polarization transmission
# ---------------------------------------------------------------------------

_TRANSMISSION_FIELD_RE = re.compile(r'^视场\s*Pos\s*[:：]', re.I)
_TRANSMISSION_AT_RE = re.compile(r'^透射\s*(?:at\s*)?(?=[-+.\d])', re.I)
_VIGNETTED_TAIL_RE = re.compile(r'\((?:渐晕|Vignetted)\s*[:：]?\s*('+NUMBER+r')\)\s*$', re.I)
_VIGNETTED_AREA_RE = re.compile(r'\((?:相对渐晕光瞳面积|Relative vignetted pupil area)\s*=\s*('+NUMBER+r')\)', re.I)
_TRANSMISSION_TOTAL_RE = re.compile(r'^总透射\s*[:：]?')
_CHEIF_SECTION_RE = re.compile(r'主光线逐面透过率|Chief ray transmission by surface', re.I)
_WAVELENGTH_ROW_RE = re.compile(r'^波长\s*(\d+)\s*[:：]', re.I)


def parse_polarization_transmission_text(text, context=None):
    """Parse the native transmission report: field/wavelength values, totals and chief-ray surfaces."""
    lines = text.splitlines()
    system_settings = (context or {}).get('system_settings')
    polarization_line = next((line.strip() for line in lines if re.match(r'^\s*场是(非)?偏振的', line)), None)
    jones = {}
    jones_lines = []
    labels = {'X-场': 'jx', 'Y-场': 'jy', 'X-相位': 'x_phase_deg', 'Y-相位': 'y_phase_deg'}
    for line in lines:
        if re.match(r'^\s*网格尺寸', line):
            break
        name, value = _label(line)
        if name in labels:
            key = labels[name]
            if key in jones:
                raise ZemaxError('INVALID_RESULT_DATA', '原生透射报告偏振头字段重复。', field=key)
            jones[key] = _one(value, key)
            jones_lines.append(line.strip())
    if polarization_line is None and set(jones) != set(labels.values()):
        raise ZemaxError('INVALID_RESULT_DATA', '原生文本不是偏振透射报告：缺少偏振状态说明。', native_lines=lines[:14])
    unpolarized = polarization_line is not None and '非偏振' in polarization_line
    if jones and (jones.get('jx', -1) < 0 or jones.get('jy', -1) < 0
                  or jones.get('jx') == jones.get('jy') == 0):
        raise ZemaxError('INVALID_RESULT_DATA', '原生透射报告Jones振幅无效。', jones=jones)
    grid_line = next((line.strip() for line in lines if re.match(r'^\s*网格尺寸', line)), None)
    if grid_line is None:
        raise ZemaxError('INVALID_RESULT_DATA', '原生文本缺少瞳面网格尺寸说明。', native_lines=lines[:14])
    grid_values = _numbers(grid_line, where='grid size')
    if len(grid_values) != 2 or any(value <= 0 or value != int(value) for value in grid_values):
        raise ZemaxError('INVALID_RESULT_DATA', '瞳面网格尺寸无法解释。', line=grid_line)
    effects_line = next((line.strip() for line in lines if line.strip().startswith('考虑了')), None)
    effects = [item.strip() for item in re.split(r'[,，]', re.sub(r'^考虑了|效应\.?$', '', effects_line or '')) if item.strip()]

    section_start = next((index for index, line in enumerate(lines) if _CHEIF_SECTION_RE.search(line)), None)
    if section_start is None:
        raise ZemaxError('NO_RESULT_DATA', '偏振透射报告缺少主光线逐面透过率。', native_lines=lines[-10:])

    fields = []
    current = None
    for line in lines[:section_start]:
        stripped = line.strip()
        if not stripped:
            continue
        if _TRANSMISSION_FIELD_RE.match(stripped):
            current = dict(**_field_identity(stripped, system_settings),
                           wavelengths=[], total_transmission=None, input_lines=[stripped])
            fields.append(current)
            continue
        if current is None:
            continue
        if _TRANSMISSION_AT_RE.match(stripped):
            # The wavelength precedes the colon: "透射 at    0.4800:     0.946229361".
            values = _numbers(_VIGNETTED_TAIL_RE.sub('',stripped), where='transmission')
            if len(values) != 2:
                raise ZemaxError('INVALID_RESULT_DATA', '透射行不是波长与数值两列。', line=stripped)
            item=dict(wavelength_um=values[0], transmission=values[1])
            vignetted=_VIGNETTED_TAIL_RE.search(stripped)
            if vignetted:
                value=float(vignetted.group(1))
                if not math.isfinite(value) or value<0:raise ZemaxError('INVALID_RESULT_DATA','渐晕透射值无效。',value=value)
                item['vignetted_transmission']=value
            current['wavelengths'].append(item)
            current['input_lines'].append(stripped)
            continue
        if _TRANSMISSION_TOTAL_RE.match(stripped):
            current['total_transmission'] = _exactly_one(_numbers(_value_part(_VIGNETTED_TAIL_RE.sub('',stripped)), where='total transmission'), 'total transmission')
            vignetted=_VIGNETTED_TAIL_RE.search(stripped)
            if vignetted:
                value=float(vignetted.group(1))
                if not math.isfinite(value) or value<0:raise ZemaxError('INVALID_RESULT_DATA','渐晕总透射值无效。',value=value)
                current['total_vignetted_transmission']=value
            current['input_lines'].append(stripped)
    if not fields:
        raise ZemaxError('NO_RESULT_DATA', '偏振透射报告没有视场透射数据。', native_lines=lines[:20])
    for field in fields:
        if not field['wavelengths']:
            raise ZemaxError('INVALID_RESULT_DATA', '视场缺少分波长透射值。', field_position_deg=field['field_position_deg'])
        if field['total_transmission'] is None:
            raise ZemaxError('INVALID_RESULT_DATA', '视场缺少总透射值。', field_position_deg=field['field_position_deg'])
        _check_fraction([item['transmission'] for item in field['wavelengths']] + [field['total_transmission']],
                        'transmission', field_position_deg=field['field_position_deg'])
        wavelengths = [item['wavelength_um'] for item in field['wavelengths']]
        if any(later <= earlier for earlier, later in zip(wavelengths, wavelengths[1:])):
            raise ZemaxError('INVALID_RESULT_DATA', '视场分波长透射未按波长递增。', wavelengths=wavelengths)
        field['aggregation'] = _aggregation_check(field, context)

    chief_ray = []
    current = None
    for line in lines[section_start + 1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if _TRANSMISSION_FIELD_RE.match(stripped):
            current = dict(**_field_identity(stripped, system_settings), wavelength_um=None,
                           wavelength_number=None, rows=[], input_lines=[stripped])
            chief_ray.append(current)
            continue
        if current is None:
            continue
        match = _WAVELENGTH_ROW_RE.match(stripped)
        if match:
            values = _numbers(_value_part(stripped), where='wavelength row')
            if not values:
                raise ZemaxError('INVALID_RESULT_DATA', '波长行没有数值。', line=stripped)
            current['wavelength_number'] = int(match.group(1))
            current['wavelength_um'] = values[0]
            current['input_lines'].append(stripped)
            continue
        values = _numbers(stripped, where='surface transmission')
        if len(values) != 3:
            continue
        surface = values[0]
        if surface != int(surface):
            raise ZemaxError('INVALID_RESULT_DATA', '逐面透射表面编号不是整数。', line=stripped)
        current['rows'].append(dict(surface=int(surface), total=values[1], relative=values[2], raw_line=stripped))
    if not chief_ray:
        raise ZemaxError('NO_RESULT_DATA', '偏振透射报告没有逐面主光线数据。', native_lines=lines[-10:])
    for block in chief_ray:
        if not block['rows']:
            raise ZemaxError('INVALID_RESULT_DATA', '主光线逐面数据缺少表面行。', field_position_deg=block['field_position_deg'])
        if block['wavelength_um'] is None:
            raise ZemaxError('INVALID_RESULT_DATA', '主光线逐面数据缺少波长行。', field_position_deg=block['field_position_deg'])
        surfaces = [row['surface'] for row in block['rows']]
        if any(later <= earlier for earlier, later in zip(surfaces, surfaces[1:])):
            raise ZemaxError('INVALID_RESULT_DATA', '主光线逐面表面编号未递增。', surfaces=surfaces)
        _check_fraction([row['total'] for row in block['rows']] + [row['relative'] for row in block['rows']], 'surface transmission',
                        field_position_deg=block['field_position_deg'], surfaces=surfaces)
        block['final_total'] = block['rows'][-1]['total']
        block['surface_totals_non_increasing'] = all(later <= earlier + 1e-9 for earlier, later in
                                                     zip([row['total'] for row in block['rows']], [row['total'] for row in block['rows']][1:]))

    rows = []
    for field in fields:
        for item in field['wavelengths']:
            rows.append(dict(index=len(rows), field_position_deg=field['field_position_deg'],
                             field_position_values=field['field_position_values'], field_unit=field['unit'],
                             wavelength_um=item['wavelength_um'], transmission=item['transmission'],
                             field_total_transmission=field['total_transmission']))
            if 'vignetted_transmission' in item:
                rows[-1]['vignetted_transmission']=item['vignetted_transmission']
                rows[-1]['field_total_vignetted_transmission']=field.get('total_vignetted_transmission')
                rows[-1]['relative_vignetted_pupil_area']=field.get('relative_vignetted_pupil_area')
    field_unit = fields[0]['unit']
    return {
        'analysis_kind': 'polarization_transmission',
        'computation_method': 'native Transmission UTF-16 report (AS_Default settings, AR_Default results)',
        'input_header': dict(unpolarized=unpolarized, grid=dict(nx=int(grid_values[0]), ny=int(grid_values[1])),
                             jones=jones or None,
                             effects=effects, effects_line=effects_line, polarization_line=polarization_line,
                             field_unit=field_unit, field_unit_source=fields[0]['unit_source'],
                             field_unit_raw=fields[0]['unit_raw']),
        'input_header_lines': jones_lines + [line for line in (polarization_line, grid_line, effects_line) if line],
        'input_header_source': 'native report header; the analysis settings object exposes no writable selectors',
        'fields': fields,
        'rows': rows,
        'chief_ray_surfaces': chief_ray,
        'units': dict(transmission='dimensionless fraction; the native scale is the fraction of the lossless throughput (manual p.901 defines 100% as no loss)',
                      field_position=field_unit, wavelength='micrometers'),
        'units_source': 'manual p.901 for the transmission fraction; native header parentheses for the field unit when printed, otherwise the system field type; micrometers from the native wavelength rows',
        'definition': dict(field_value='integrated transmission for each field and wavelength over the native pupil sampling grid, including apertures, coatings, vignetting and bulk absorption (manual p.901)',
                           field_value_verified=False,
                           chief_ray='per-surface total and relative transmission along the chief ray; relative covers the preceding material bulk plus the current surface coating (manual p.902)',
                           total='label printed by the native report for each field; not necessarily the mean of the listed wavelengths'),
        'selection': _selection(context, writable=[]),
        'structured_data_available': True,
    }


def _field_identity(line, system_settings):
    """Field coordinate values plus the unit resolved from the header, never assumed."""
    positions = _numbers(_value_part(_VIGNETTED_AREA_RE.sub('',line)), where='field position')
    if not positions:
        raise ZemaxError('INVALID_RESULT_DATA', '视场坐标行没有数值。', line=line.strip())
    unit_info = resolve_field_unit(line, system_settings)
    area=_VIGNETTED_AREA_RE.search(line)
    extra={}
    if area:
        value=float(area.group(1))
        if not math.isfinite(value) or value<0:raise ZemaxError('INVALID_RESULT_DATA','渐晕光瞳面积无效。',value=value)
        extra['relative_vignetted_pupil_area']=value
    return dict(**extra,field_position_values=positions,
                field_position=dict(x=positions[0] if len(positions) > 1 else None, y=positions[-1]),
                field_position_deg=positions[-1] if len(positions) == 1 and unit_info['unit'] == 'degrees' else None,
                **unit_info)


def _check_fraction(values, where, **details):
    for value in values:
        if not math.isfinite(value) or value < 0 or value > 1.000001:
            raise ZemaxError('INVALID_RESULT_DATA', '透射值超出 0..1 分数范围。', quantity=where, value=value, **details)


def _aggregation_check(field, context):
    """Compare the printed total with the weighted mean of the listed wavelengths.

    The weighted-mean rule was established offline on the stored 2026-11-08 report (three
    fields, residuals <= 4e-10) using the system wavelength weights. It is re-evaluated here
    whenever the caller supplies those weights, and never assumed when they are absent.
    """
    report = dict(method='weighted mean of the per-wavelength transmissions using system wavelength weights',
                  source='offline check on the stored 2026-11-08 native report (.local/evidence/development/NS-03/polarization-transmission-20261108), residuals <= 4e-10')
    wavelengths = (context or {}).get('system_settings', {}).get('wavelengths') if context else None
    if not wavelengths:
        return {**report, 'status': 'not_evaluated', 'reason': 'system wavelength weights are unavailable'}
    weights, matched = [], []
    for item in field['wavelengths']:
        candidates = [wave for wave in wavelengths if abs(float(wave['wavelength_um']) - item['wavelength_um']) <= 5e-5]
        if len(candidates) != 1:
            return {**report, 'status': 'not_evaluated', 'reason': 'report wavelength does not match one system wavelength',
                    'wavelength_um': item['wavelength_um'], 'matches': len(candidates)}
        weights.append(float(candidates[0]['weight']))
        matched.append(float(candidates[0]['wavelength_um']))
    total_weight = sum(weights)
    if total_weight <= 0:
        return {**report, 'status': 'not_evaluated', 'reason': 'system wavelength weights sum to zero'}
    expected = sum(weight * item['transmission'] for weight, item in zip(weights, field['wavelengths'])) / total_weight
    residual = field['total_transmission'] - expected
    return {**report, 'status': 'match' if abs(residual) <= 1e-8 else 'mismatch', 'weights': weights,
            'system_wavelengths_um': matched, 'expected': expected, 'reported': field['total_transmission'],
            'residual': residual, 'tolerance': 1e-8}

# ---------------------------------------------------------------------------
# Fiber coupling
# ---------------------------------------------------------------------------

_FIBER_FIELDS = (
    ('wavelength', re.compile(r'^(?:波长|Wavelength)\s*[:：]', re.I), 'micrometers'),
    ('field_type', re.compile(r'^(?:视场类型|Field\s*type)\s*[:：]', re.I), None),
    ('field_x', re.compile(r'^X\s*视场\s*坐标\s*[:：]', re.I), None),
    ('field_y', re.compile(r'^Y\s*视场\s*坐标\s*[:：]', re.I), None),
    ('position_units', re.compile(r'^位置单位\s*[:：]'), None),
    ('angle_units', re.compile(r'^角度单位\s*[:：]'), None),
    ('source_fiber', re.compile(r'^源光纤\s*[:：]'), None),
    ('receiver_na_x', re.compile(r'^接收光纤\s*NA\s*X-?方向\s*[:：]', re.I), None),
    ('receiver_na_y', re.compile(r'^接收光纤\s*NA\s*Y-?方向\s*[:：]', re.I), None),
    ('receiver_position_x', re.compile(r'^接收名义位置\s*X\s*[:：]', re.I), None),
    ('receiver_position_y', re.compile(r'^接收名义位置\s*Y\s*[:：]', re.I), None),
    ('receiver_decenter_x', re.compile(r'^接收偏心\s*X\s*[:：]', re.I), None),
    ('receiver_decenter_y', re.compile(r'^接收偏心\s*Y\s*[:：]', re.I), None),
    ('receiver_decenter_z', re.compile(r'^接收偏心\s*Z\s*[:：]', re.I), None),
    ('receiver_tilt_x_deg', re.compile(r'^接收关于\s*X\s*倾斜', re.I), None),
    ('receiver_tilt_y_deg', re.compile(r'^接收关于\s*Y\s*倾斜', re.I), None),
    ('system_efficiency', re.compile(r'^系统\s*效率\s*[:：]'), None),
    ('receiver_efficiency', re.compile(r'^接收\s*效率\s*[:：]'), None),
    ('total_coupling_efficiency', re.compile(r'^耦合效率\s*[:：]'), None),
)
_FIBER_TEXT_FIELDS = ('field_type', 'position_units', 'angle_units', 'source_fiber')
_FIBER_REQUIRED = ('wavelength', 'receiver_na_x', 'receiver_na_y', 'system_efficiency', 'receiver_efficiency', 'total_coupling_efficiency')


def parse_fiber_coupling_text(text, context=None):
    """Parse the native fiber-coupling report: declared inputs, efficiencies and definitions."""
    lines = text.splitlines()
    title = next((line.strip() for line in lines if line.strip()), '')
    if re.search(r'惠更斯|Huygens', title, re.I):
        integration_method = 'huygens'
    elif re.search(r'光线积分|ray[-\s]+based|ray[-\s]+integration', title, re.I):
        integration_method = 'ray_based'
    else:
        integration_method = None
    values = {}
    value_lines = []
    consumed = set()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        for name, pattern, _unit in _FIBER_FIELDS:
            if name in values or not pattern.match(stripped):
                continue
            raw = _value_part(stripped).strip()
            if name in _FIBER_TEXT_FIELDS:
                values[name] = raw
            else:
                numbers = _numbers(raw, where=name)
                if not numbers:
                    raise ZemaxError('INVALID_RESULT_DATA', '光纤耦合输入行没有数值。', field=name, line=stripped)
                values[name] = numbers[0] if len(numbers) == 1 else dict(value=numbers[0], degree=numbers[1])
                if name == 'total_coupling_efficiency' and len(numbers) > 1:
                    values[name] = dict(value=numbers[0], db=numbers[1])
            value_lines.append(stripped)
            consumed.add(index)
            break
    missing = [name for name in _FIBER_REQUIRED if name not in values]
    if missing:
        raise ZemaxError('INVALID_RESULT_DATA', '原生文本不是光纤耦合报告：缺少效率或接收光纤字段。', missing=missing, native_lines=lines[:16])

    efficiencies = {}
    for name in ('system_efficiency', 'receiver_efficiency', 'total_coupling_efficiency'):
        item = values[name]
        number = item['value'] if isinstance(item, dict) else item
        if not (0 <= number <= 1.000001):
            raise ZemaxError('INVALID_RESULT_DATA', '光纤耦合效率超出 0..1。', field=name, value=number)
        efficiencies[name] = number
    for name in ('receiver_na_x', 'receiver_na_y'):
        if values[name] <= 0:
            raise ZemaxError('INVALID_RESULT_DATA', '接收光纤 NA 必须为正。', field=name, value=values[name])

    total = efficiencies['total_coupling_efficiency']
    product = efficiencies['system_efficiency'] * efficiencies['receiver_efficiency']
    definitions = [line.strip() for index, line in enumerate(lines) if index not in consumed and line.strip()
                   and not line.strip().startswith(('文件', '题目', '日期'))]
    return {
        'analysis_kind': 'fiber_coupling_settings',
        'computation_method': 'native FiberCouplingSettings UTF-16 report (AS_Default settings, AR_Default results)',
        'integration_method': integration_method,
        'integration_method_source': dict(title=title, source='native report title',
                                          status='declared' if integration_method else 'not_declared'),
        'input_header': dict(wavelength_um=_scalar(values['wavelength']), field_type=values.get('field_type'),
                             field_position=dict(x=_scalar(values.get('field_x')), y=_scalar(values.get('field_y'))),
                             position_units=values.get('position_units'), angle_units=values.get('angle_units'),
                             source_fiber=values.get('source_fiber')),
        'input_header_lines': value_lines,
        'input_header_source': 'native report header; the analysis settings object exposes no writable selectors',
        'receiver': dict(na_x=values['receiver_na_x'], na_y=values['receiver_na_y'],
                         position_x=_scalar(values.get('receiver_position_x')), position_y=_scalar(values.get('receiver_position_y')),
                         decenter=dict(x=_scalar(values.get('receiver_decenter_x')), y=_scalar(values.get('receiver_decenter_y')),
                                       z=_scalar(values.get('receiver_decenter_z'))),
                         tilt_deg=dict(x=_scalar(values.get('receiver_tilt_x_deg')), y=_scalar(values.get('receiver_tilt_y_deg')))),
        'efficiencies': dict(system=efficiencies['system_efficiency'], receiver=efficiencies['receiver_efficiency'],
                             total_coupling=total), 
        'total_coupling_db': values['total_coupling_efficiency'].get('db') if isinstance(values['total_coupling_efficiency'], dict) else None,
        'consistency': dict(product=product, residual=total - product,
                            identity='total coupling efficiency equals system efficiency times receiver efficiency (native report statement)',
                            tolerance=1e-6, status='match' if abs(total - product) <= 1e-6 else 'mismatch'),
        'rows': [dict(index=index, quantity=name, value=number, unit='dimensionless fraction')
                 for index, (name, number) in enumerate((('system_efficiency', efficiencies['system_efficiency']),
                                                         ('receiver_efficiency', efficiencies['receiver_efficiency']),
                                                         ('total_coupling_efficiency', total)))],
        'units': dict(efficiency='dimensionless fraction', total_coupling_db='decibels',
                      na='dimensionless numerical aperture', position='native position units from the report header',
                      tilt='degrees', wavelength='micrometers'),
        'units_source': 'native report header names the position and angle units; efficiency and NA are dimensionless',
        'definition': dict(
            system='fraction of the source beam energy that remains inside the optical system; set by input NA, entrance-pupil size and position, apodization, element transmission and vignetting (native report text)',
            receiver='fraction of the transmitted energy at the exit pupil that couples into the receiver fiber; set by the receiver NA and the aberrations (native report text)',
            total_coupling='fraction of the source fiber energy coupled into the receiver fiber; the product of system and receiver efficiency (native report text)',
            definition_lines=definitions),
        'selection': _selection(context, writable=[]),
        'structured_data_available': True,
    }


def _scalar(value):
    if value is None:
        return None
    return value['value'] if isinstance(value, dict) else value

# ---------------------------------------------------------------------------
# Dispatch used by the shared analysis collector
# ---------------------------------------------------------------------------

TOPIC_PARSERS = {
    'phase_aberration': parse_phase_aberration_text,
    'polarization_ray_trace': parse_polarization_ray_trace_text,
    'polarization_transmission': parse_polarization_transmission_text,
    'fiber_coupling_settings': parse_fiber_coupling_text,
}


def parse_topic_text(kind, text, context=None):
    """Parse one of the four native topic reports; every result keeps the raw text artifact."""
    try:
        parser = TOPIC_PARSERS[kind]
    except KeyError:
        raise ZemaxError('INVALID_ARGUMENT', '未登记的原生专题报告类型。', kind=kind) from None
    return parser(text, context)
