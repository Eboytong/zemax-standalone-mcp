"""Native current-accumulation viewer and shared ZRD display controls."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .schema import Request, PositiveIndex
from .data import unwrap
from .detectors import check_setting_readback
from .errors import ZemaxError
from .zrd_replay import check_replay_enum, replay_text_summary

ShowAs = Literal['GreyScale', 'GreyScale_Inverted', 'FalseColor', 'FalseColor_Inverted',
                 'CrossSection_Row', 'CrossSection_Column', 'Text_CrossSection_Row',
                 'Text_CrossSection_Column', 'FullListing', 'AzimuthCrossSection',
                 'FluxVsWaveLength', 'TrueColor', 'CrossSection', 'Color_CrossSection_Row',
                 'Color_CrossSection_Column', 'Color_FluxVsWavelength', 'Directivity_Full',
                 'Directivity_Half', 'GeometricMtf']
DataType = Literal['IncoherentIrradiance', 'IncoherentFluence', 'CoherentIrradiance',
                   'CoherentPhase', 'IncidentFlux', 'AbsorbedFlux', 'RadiantIntensity',
                   'AngleSpace', 'PositionSpace', 'IncoherentIlluminance', 'CoherentFluence',
                   'CoherentIlluminance', 'AbsorbedFluxVolume', 'LuminousIntensity',
                   'LuminancePositionSpace', 'RadiancePositionSpace', 'LuminanceAngleSpace',
                   'RadianceAngleSpace', 'Polar_AngleSpace']
Scale = Literal['Linear', 'Normalized', 'Log_Minus_5', 'Log_Minus_10', 'Log_Minus_15']


class DetectorViewer(Request):
    kind: Literal['detector_viewer']
    source: Literal['current_detector', 'zrd'] = 'current_detector'
    detector: PositiveIndex
    path: str | None = None
    filter: str = ''
    show_as: ShowAs = 'FalseColor'
    data_type: DataType = 'IncoherentIrradiance'
    scale: Scale = 'Linear'
    smoothing: Annotated[int, Field(strict=True, ge=0, le=10)] = 0
    row_col: Annotated[int, Field(strict=True, ge=0)] = 0

    @model_validator(mode='after')
    def source_contract(self):
        if (self.source == 'zrd') != (self.path is not None):
            raise ValueError('zrd来源需要path；current_detector采用当前累积结果。')
        if self.source == 'current_detector' and self.filter:
            raise ValueError('Filter需要ZRD来源。')
        return self


def configure_display(native, settings, request):
    """Enums are checked by native value to allow the installed contextual aliases."""
    for field, value in [('DataType', request.data_type), ('ShowAs', request.show_as),
                         ('Scale', request.scale)]:
        if value is not None:
            native.set_enum(settings, field, value)
            check_replay_enum(native, settings, field, value)
    for field, value in [('Smoothing', request.smoothing), ('RowCol', request.row_col)]:
        if value is not None:
            setattr(settings, field, value)
            check_setting_readback(settings, field, value)


def describe_result(result, request, detector_type=None, lens_unit=None):
    result['analysis_kind'] = 'detector_viewer'
    result['detector_viewer'] = dict(source=request.source, detector=request.detector,
        show_as=request.show_as, data_type=request.data_type, scale=request.scale,
        smoothing=request.smoothing, row_col=request.row_col,
        values_source='native DataGrid/DataSeries, labels and axes retained',
        display_settings='Scale/Smoothing are native display settings; numerical export follows native result',
        raw_data_tool='get_detector_data', detector_type=detector_type)
    result['native_detector_summary'] = replay_text_summary(result.get('native_preamble', []))
    for grid in result.get('grids', []):
        if len(grid['values']) != grid['ny'] or any(len(row) != grid['nx'] for row in grid['values']):
            raise ZemaxError('INVALID_RESULT_DATA', 'Detector Viewer网格维度与原生尺寸不符。',
                             grid=grid.get('grid'), nx=grid['nx'], ny=grid['ny'])
        grid['array_order'] = 'values[y][x]; native Values dimension 0=y, dimension 1=x'
        grid['native_axes'] = {key: grid[key] for key in ('min_x','min_y','dx','dy','x_label','y_label','value_label') if key in grid}
        if detector_type == 'DetectorRectangle' and request.data_type in {
                'IncoherentIrradiance','IncoherentFluence','CoherentIrradiance','CoherentPhase',
                'PositionSpace','IncoherentIlluminance','CoherentIlluminance','CoherentFluence'}:
            grid['x_coordinates'] = [grid['min_x']+(i+.5)*grid['dx'] for i in range(grid['nx'])]
            grid['y_coordinates'] = [grid['min_y']+(i+.5)*grid['dy'] for i in range(grid['ny'])]
            grid['coordinate_definition'] = 'detector-local pixel centers; native MinX/MinY are lower edges'
            grid['coordinate_unit'] = lens_unit
    return result


def collect_detector_result(backend, task):
    result = backend._collect_general_analysis(task, optional_native_text=True)
    if not result.get('structured_data_available'):
        result.update(empty_result=True, result_status='native_empty_result')
    return result



def run_detector_viewer(backend, request):
    backend._require_nsc()
    detector = backend._object(request.detector)
    detector_type = str(getattr(detector, 'Type', 'unknown'))
    lens_unit = str(backend.system.SystemData.Units.LensUnits) if detector_type == 'DetectorRectangle' else None
    if request.source == 'zrd':
        from .nsc_models import ZrdReplay
        return backend.run_zrd_replay(ZrdReplay(path=request.path, detector=request.detector,
            filter=request.filter, data_type=request.data_type, show_as=request.show_as,
            scale=request.scale, smoothing=request.smoothing, row_col=request.row_col))
    tool = backend.system.Analyses.New_Analysis(backend.native.api.Analysis.AnalysisIDM.DetectorViewer)
    try:
        settings = unwrap(tool.GetSettings())
        if hasattr(settings, 'IsValidDetector') and not settings.IsValidDetector(request.detector):
            raise ZemaxError('INVALID_DETECTOR', '指定对象不是原生Viewer可选择的探测器。', detector=request.detector)
        settings.Detector.SetDetectorNumber(request.detector)
        if int(settings.Detector.GetDetectorNumber()) != request.detector:
            raise ZemaxError('SETTING_REJECTED', '原生Viewer未采用探测器编号。', detector=request.detector)
        settings.RayDatabaseFilename = ''
        check_setting_readback(settings, 'RayDatabaseFilename', '')
        settings.Filter = ''
        check_setting_readback(settings, 'Filter', '')
        configure_display(backend.native, settings, request)
        from .analyses import scalar_settings
        actual = dict(kind='detector_viewer', requested=request.model_dump(), native=scalar_settings(settings),
                      detector=request.detector, source='current_detector')
    except Exception:
        backend._release_owned(tool)
        raise
    def collect(task):
        return describe_result(collect_detector_result(backend, task), request, detector_type, lens_unit)
    return backend._start_task('analysis', tool, actual, analysis=True, collector=collect)
