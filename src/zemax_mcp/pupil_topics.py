"""Dedicated pupil-aberration settings and percent-stop-radius curves."""
from typing import Annotated, Literal
from pydantic import Field
from .schema import Request, Index, FiniteFloat
from .errors import ZemaxError


class PupilAberration(Request):
    kind: Literal['pupil_aberration_fan']
    field: Index = 0
    wavelength: Index = 0
    number_of_rays: Annotated[int, Field(strict=True, ge=3, le=10001)] = 101
    plot_scale: Annotated[FiniteFloat, Field(ge=0)] = 0
    check_apertures: bool = True
    vignetted_pupil: bool = True
    use_dashes: bool = False


def configure(q, write):
    # These enum values are inherited fan-axis selectors; the pupil metric is scalar.
    values = dict(NumberOfRays=q.number_of_rays, PlotScale=q.plot_scale, CheckApertures=q.check_apertures,
        VignettedPupil=q.vignetted_pupil, UseDashes=q.use_dashes, Tangential='Aberration_Y', Sagittal='Aberration_X')
    for name, value in values.items():write(name, value)
    return values


def run_pupil(backend, q):
    from .data import unwrap
    from .analyses import scalar_settings
    from .imaging import new_analysis, checked, check, select
    from .detectors import check_setting_value
    backend._require_sequential();backend._require_work()
    if q.field > backend.system.SystemData.Fields.NumberOfFields or q.wavelength > backend.system.SystemData.Wavelengths.NumberOfWavelengths:
        raise ZemaxError('INDEX_OUT_OF_RANGE', '瞳像差视场或波长编号越界。')
    tool = new_analysis(backend, 'PupilAberrationFan')
    if tool is None:raise ZemaxError('NATIVE_INTERFACE_UNAVAILABLE', '瞳像差工厂返回空对象。')
    try:
        s = unwrap(tool.GetSettings())
        select(s.Field, 'Field', q.field);select(s.Wavelength, 'Wavelength', q.wavelength)
        s.Surface.UseImageSurface()
        values = configure(q, lambda name, value: checked(backend.native, s, name, value))
        for name, value in values.items():check(backend.native, s, name, value)
        check_setting_value('Field',q.field,int(s.Field.GetFieldNumber()))
        check_setting_value('Wavelength',q.wavelength,int(s.Wavelength.GetWavelengthNumber()))
        check_setting_value('Surface',0,int(s.Surface.GetSurfaceNumber()))
        actual = scalar_settings(s)
        if actual.get('unavailable_fields'):raise ZemaxError('SETTING_UNAVAILABLE', '瞳像差设置回读失败。', details=actual['unavailable_fields'])
        settings = dict(kind=q.kind, requested=q.model_dump(), native=actual, stop_surface=int(backend.system.LDE.StopSurface))
    except Exception as exc:
        owner = dict(native=tool)
        if not backend._close_task_native(owner) and isinstance(exc, ZemaxError):exc.details['cleanup_warnings']=owner.get('cleanup_warnings',[])
        raise
    def collect(task):
        result=backend._collect_general_analysis(task)
        if not result['series']:raise ZemaxError('NO_RESULT_DATA', '瞳像差未返回曲线。', artifacts=result['artifacts'], native_messages=result['native_messages'])
        for curve in result['series']:
            curve.update(x_unit='normalized pupil', value_units=['percent of paraxial stop radius']*len(curve['labels']))
        result.update(analysis_kind=q.kind, stop_surface=settings['stop_surface'],
            definition='100 * (on-axis primary-wavelength paraxial stop intercept - real stop intercept) / paraxial stop radius',
            definition_source='Installed v242 English manual page732; sign confirmed against native paraxial/real stop ray traces',
            surface_selection='native Image selector; metric evaluated at stop')
        return result
    return backend._start_task(q.kind, tool, settings, analysis=True, collector=collect)
