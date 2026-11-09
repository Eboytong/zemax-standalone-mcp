"""Native phase-aberration selection on a task-owned, frozen-geometry system."""
import math

from .errors import ZemaxError
from .speos import OwnedCopyTool

FIELD_ATTRIBUTES = ('X', 'Y', 'Weight', 'VDX', 'VDY', 'VCX', 'VCY', 'VAN')
SELECTORS = frozenset(('field', 'wavelength', 'polarization'))


class PhaseCopyOwner(OwnedCopyTool):
    def __init__(self, system, receipt):
        super().__init__(system)
        self.receipt = receipt

    def Close(self):
        try:
            return super().Close()
        finally:
            self.receipt.update(analysis_closed=self.tool_closed, system_closed=self.system_closed)


def uses_copy(request):
    explicit = request.model_fields_set & SELECTORS
    if request.method == 'native' and explicit:
        raise ZemaxError('UNSUPPORTED_SETTING', '原生相位专题没有可回读的直接选择设置。', settings=sorted(explicit))
    return request.method == 'system_copy' or request.method == 'auto' and bool(explicit)


def optical_cells(backend, system):
    rows = []
    for index in range(int(system.LDE.NumberOfSurfaces)):
        row = system.LDE.GetSurfaceAt(index)
        rows.append(dict(surface=index, surface_type=str(row.Type),
            cells={name: dict(value=backend._cell_value(cell), data_type=str(cell.DataType))
                   for name, cell in backend._cells(row) if name != 'comment'}))
    return rows


def check_optical_cells(expected, actual):
    """Keep numerical write rounding separate from a changed optical model."""
    if len(expected) != len(actual):
        raise ZemaxError('SETTING_REJECTED', '相位副本曲面数量发生变化。')
    maximum = 0.
    for source, adopted in zip(expected, actual, strict=True):
        if source['surface_type'] != adopted['surface_type'] or source['cells'].keys() != adopted['cells'].keys():
            raise ZemaxError('SETTING_REJECTED', '相位副本面型或活动单元格发生变化。', surface=source['surface'])
        for name, cell in source['cells'].items():
            value = adopted['cells'][name]['value']
            wanted = cell['value']
            if cell['data_type'] == 'Double' and math.isfinite(wanted) and math.isfinite(value):
                error = abs(value - wanted)
                maximum = max(maximum, error)
                equal = error <= 1e-12 + 1e-12 * abs(wanted)
            else:
                equal = value == wanted
            if not equal:
                raise ZemaxError('SETTING_REJECTED', '相位副本输入选择改变了源模型的光学单元格。',
                    surface=source['surface'], cell=name, expected=str(wanted), actual=str(value))
    return dict(passed=True, maximum_absolute_difference=maximum, absolute_tolerance=1e-12, relative_tolerance=1e-12)


def freeze_geometry(backend, system):
    adopted = []
    for index in range(int(system.LDE.NumberOfSurfaces)):
        row = system.LDE.GetSurfaceAt(index)
        for name, cell in backend._cells(row):
            kind, mode = str(cell.DataType), str(cell.Solve)
            if name in ('chip_zone', 'mechanical_semi_diameter') or kind not in ('Double', 'Integer') or mode in ('Fixed', 'Variable'):
                continue
            value = backend._cell_value(cell)
            if cell.IsReadOnly:
                continue
            if not cell.MakeSolveFixed() or str(cell.Solve) != 'Fixed':
                raise ZemaxError('SETTING_REJECTED', '相位分析副本不能固定依赖单元格。',
                    surface=index, cell=name, previous_solve=mode)
            if kind == 'Double':
                cell.DoubleValue = value
            else:
                cell.IntegerValue = value
            adopted.append(dict(surface=index, cell=name, previous_solve=mode,
                                value=value, actual=backend._cell_value(cell)))
    return adopted


def check_header(parsed, field, wavelength, polarization):
    actual = parsed['input_header']
    # A one-coordinate native header identifies a Y-axis field only.
    position = actual['field_position']
    x = position['x']
    if x is None:
        if field['x'] != 0:
            raise ZemaxError('SETTING_UNCONFIRMED', '相位报告单坐标视场不能确认非零X输入。',
                requested=field, actual=position)
        x = 0.
    if abs(x - field['x']) > .0051 or abs(position['y'] - field['y']) > .0051:
        raise ZemaxError('SETTING_REJECTED', '相位报告视场未采用所选输入。', requested=field, actual=position)
    if abs(actual['wavelength_um'] - wavelength['wavelength_um']) > .000051:
        raise ZemaxError('SETTING_REJECTED', '相位报告波长未采用所选输入。', requested=wavelength, actual=actual['wavelength_um'])
    for name, requested in polarization.items():
        key = name + '_deg' if name.endswith('phase') else name
        tolerance = .0051 if name.endswith('phase') else .000051
        difference = actual['jones'][key] - requested
        if name.endswith('phase'):
            difference = (difference + 180.) % 360. - 180.
        if abs(difference) > tolerance:
            raise ZemaxError('SETTING_REJECTED', '相位报告Jones输入未采用。', setting=name, expected=requested, actual=actual['jones'][key])
    return actual


def trace_witnesses(backend, system, field, wavelength):
    from System import Double, Int32
    from .field_analyses import normalized_field
    hx, hy = normalized_field(field['table'], field['selected'], field['normalization'])
    points = ((0., 0.), (.3, .4), (-.4, -.2))
    tool = system.Tools.OpenBatchRayTrace()
    try:
        data = tool.CreateNormUnpol(len(points), backend.native.api.Tools.RayTrace.RaysType.Real,
                                   int(system.LDE.NumberOfSurfaces) - 1)
        opd = backend.native.enum(backend.native.api.Tools.RayTrace.OPDMode, 'None')
        for px, py in points:
            if not data.AddRay(wavelength, hx, hy, px, py, opd):
                raise ZemaxError('RAY_REJECTED', '相位副本光线见证被拒绝。', pupil=[px, py])
        if not tool.Run():
            raise ZemaxError('TASK_START_FAILED', str(tool.ErrorMessage))
        tool.WaitForCompletion()
        if not tool.Succeeded:
            raise ZemaxError('TASK_FAILED', str(tool.ErrorMessage))
        data.StartReadingResults()
        rows = []
        while True:
            result = data.ReadNextResult(*([Int32(0)] * 3 + [Double(0)] * 11))
            if not result[0]:
                break
            rows.append(dict(ray=int(result[1]), error=int(result[2]), vignette=int(result[3]),
                             position_direction=[float(v) for v in result[4:10]] if not result[2] else None))
        if [r['ray'] for r in rows] != [1, 2, 3]:
            raise ZemaxError('INVALID_RESULT_DATA', '相位光线见证编号或数量不符。', rows=rows)
        return rows
    finally:
        backend._release_owned(tool)


def check_trace_witnesses(source, actual):
    comparisons = []
    for expected, adopted in zip(source, actual, strict=True):
        if (expected['error'], expected['vignette']) != (adopted['error'], adopted['vignette']):
            raise ZemaxError('SETTING_REJECTED', '相位副本改变了代表光线状态。', source=source, actual=actual)
        if expected['position_direction'] is None:
            continue
        for a, b in zip(expected['position_direction'], adopted['position_direction'], strict=True):
            tolerance = 1e-9 + 1e-9 * abs(a)
            passed = math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance
            comparisons.append(dict(error=abs(a - b), tolerance=tolerance, passed=passed))
    if not comparisons or not all(c['passed'] for c in comparisons):
        raise ZemaxError('SETTING_REJECTED', '相位副本切换输入后光线瞄准或瞳映射不一致。',
                         source=source, actual=actual, comparisons=comparisons)
    return dict(source=source, actual=actual, comparisons=comparisons, passed=True)


def run_phase_copy(backend, request):
    backend._require_sequential()
    source = backend.get_system_settings(None)
    field_number = request.field or 1
    wave_number = request.wavelength or next(w['number'] for w in source['wavelengths'] if w['primary'])
    if field_number > len(source['fields']) or wave_number > len(source['wavelengths']):
        raise ZemaxError('INDEX_OUT_OF_RANGE', '相位分析视场或波长编号越界。')
    field, wave = source['fields'][field_number - 1], source['wavelengths'][wave_number - 1]
    polarization = (request.polarization.model_dump() if request.polarization is not None else
                    {k: source['polarization'][k] for k in ('jx', 'jy', 'x_phase', 'y_phase')})
    before = optical_cells(backend, backend.system)
    owned = None
    settings = dict(kind=request.kind, requested=request.model_dump(exclude_unset=True),
        method='system_copy', field=field_number, wavelength=wave_number,
        source_primary_wavelength=next(w['number'] for w in source['wavelengths'] if w['primary']),
        actual_field=field, actual_wavelength=wave, polarization=polarization,
        geometry_policy='freeze evaluated numeric solves in the owned copy; retain source model and source solves',
        primary_policy='selected wavelength becomes primary in the analysis copy; source primary unchanged')
    settings['resource_close'] = dict(analysis_closed=False, system_closed=False)
    try:
        copy = backend.system.CopySystem()
        if copy is None:
            raise ZemaxError('COPY_FAILED', '无法创建相位分析副本。')
        owned = PhaseCopyOwner(copy, settings['resource_close'])
        settings.update(source_system_id=int(backend.system.SystemID), analysis_system_id=int(copy.SystemID))
        if int(copy.MCE.CurrentConfiguration) != source['configuration']:
            raise ZemaxError('SETTING_REJECTED', '相位副本当前配置不一致。')
        settings['configuration'] = int(copy.MCE.CurrentConfiguration)
        settings['frozen_cells'] = freeze_geometry(backend, copy)
        fields = copy.SystemData.Fields
        first = {k: float(getattr(fields.GetField(1), k)) for k in FIELD_ATTRIBUTES}
        selected = {k: float(getattr(fields.GetField(field_number), k)) for k in FIELD_ATTRIBUTES}
        for index, values in ((field_number, first), (1, selected)):
            for attr, value in values.items():
                setattr(fields.GetField(index), attr, value)
        if any(float(getattr(fields.GetField(1), k)) != v for k, v in selected.items()):
            raise ZemaxError('SETTING_REJECTED', '相位副本视场表采用失败。')
        waves = copy.SystemData.Wavelengths
        waves.GetWavelength(wave_number).MakePrimary()
        if not waves.GetWavelength(wave_number).IsPrimary:
            raise ZemaxError('SETTING_REJECTED', '相位副本主波长采用失败。')
        pol = copy.SystemData.Polarization
        pol.Unpolarized = False
        if pol.Unpolarized:
            raise ZemaxError('SETTING_REJECTED', '相位副本未启用Jones输入。')
        for attr, key in (('Jx', 'jx'), ('Jy', 'jy'), ('XPhase', 'x_phase'), ('YPhase', 'y_phase')):
            setattr(pol, attr, polarization[key])
            if float(getattr(pol, attr)) != polarization[key]:
                raise ZemaxError('SETTING_REJECTED', '相位副本Jones设置回读不符。', setting=key)
        settings['geometry_before_analysis'] = check_optical_cells(before, optical_cells(backend, copy))
        settings['aperture'] = dict(type=str(copy.SystemData.Aperture.ApertureType),
                                    value=float(copy.SystemData.Aperture.ApertureValue))
        settings['ray_aiming'] = dict(mode=str(copy.SystemData.RayAiming.RayAiming),
                                      method=str(copy.SystemData.RayAiming.Method),
                                      use_cache=bool(copy.SystemData.RayAiming.UseRayAimingCache))
        witness_field = dict(table=source['fields'], selected=field, normalization=source['field_normalization'])
        settings['ray_mapping_check'] = check_trace_witnesses(
            trace_witnesses(backend, backend.system, witness_field, wave_number),
            trace_witnesses(backend, copy, witness_field, wave_number))
        owned.tool = copy.Analyses.New_Analysis_SettingsFirst(backend.native.enum(backend.native.api.Analysis.AnalysisIDM, 'PhaseAberration'))
        if owned.tool is None:
            raise ZemaxError('UNSUPPORTED_INTERFACE', '原生相位专题工厂返回空对象。')

        def collect(task):
            result = backend._collect_general_analysis(task)
            result['actual_settings'] = settings
            result['computation_method'] = 'native PhaseAberration on a frozen-geometry owned system copy'
            result['selection'] = dict(method='system_copy', field=field_number, wavelength=wave_number,
                source='formal system table readback and native report header', requested_method=request.method)
            try:
                if int(copy.MCE.CurrentConfiguration) != settings['configuration']:
                    raise ZemaxError('SETTING_REJECTED', '相位执行改变了副本当前配置。')
                settings['geometry_after_analysis'] = check_optical_cells(before, optical_cells(backend, copy))
                settings['actual_report_header'] = check_header(result, field, wave, polarization)
                settings['source_geometry_after_analysis'] = check_optical_cells(before, optical_cells(backend, backend.system))
            except ZemaxError as exc:
                exc.details.update(native_artifacts=result.get('artifacts', []),
                                   native_messages=result.get('native_messages', []), actual_settings=settings)
                raise
            return result

        return backend._start_task('analysis', owned, settings, analysis=True, collector=collect)
    except Exception as original:
        if isinstance(original, ZemaxError):
            original.details.setdefault('actual_settings', settings)
        if owned is not None:
            try:
                backend._release_owned(owned)
            except Exception as cleanup:
                if isinstance(original, ZemaxError):
                    original.details['cleanup_error'] = str(cleanup)
                else:
                    raise ZemaxError('CLEANUP_FAILED', '相位副本关闭失败。',
                        original_error=dict(type=type(original).__name__, message=str(original)),
                        cleanup_error=str(cleanup)) from original
        raise
