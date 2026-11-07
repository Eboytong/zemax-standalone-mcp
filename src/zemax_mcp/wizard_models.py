"""Typed fields from installed 2024 R2 wizard interfaces."""
from typing import Annotated, Literal
from pydantic import Field, FiniteFloat, model_validator
from .schema import Request, Index, PositiveIndex

class WizardBase(Request):
    apply: bool = False
    reset: bool = True

    @model_validator(mode="after")
    def explicit_values(self):
        if any(getattr(self, k) is None for k in self.model_fields_set):
            raise ValueError("省略保持原值的字段；显式设置不得为空")
        return self

class SequentialWizard(WizardBase):
    kind: Literal['sequential']
    criterion: Literal['Wavefront', 'Contrast', 'Spot', 'Angular'] | None = None
    spatial_frequency: FiniteFloat | None = None
    xs_weight: FiniteFloat | None = None
    yt_weight: FiniteFloat | None = None
    type: Literal['RMS', 'PTV'] | None = None
    reference: Literal['Centroid', 'ChiefRay', 'Unreferenced'] | None = None
    use_gaussian_quadrature: bool | None = None
    use_rectangular_array: bool | None = None
    rings: PositiveIndex | None = None
    arms: Literal['Arms_6', 'Arms_8', 'Arms_10', 'Arms_12'] | None = None
    obscuration: FiniteFloat | None = None
    grid_size_nx_n: PositiveIndex | None = None
    delete_vignetted: bool | None = None
    use_glass_boundary_values: bool | None = None
    glass_min: FiniteFloat | None = None
    glass_max: FiniteFloat | None = None
    glass_edge_thickness: FiniteFloat | None = None
    use_air_boundary_values: bool | None = None
    air_min: FiniteFloat | None = None
    air_max: FiniteFloat | None = None
    air_edge_thickness: FiniteFloat | None = None
    start_at: PositiveIndex | None = None
    overall_weight: FiniteFloat | None = None
    configuration_number: PositiveIndex | None = None
    use_all_configurations: bool | None = None
    field_number: PositiveIndex | None = None
    use_all_fields: bool | None = None
    assume_axial_symmetry: bool | None = None
    ignore_lateral_color: bool | None = None
    add_favorite_operands: bool | None = None
    optimize_for_best_nominal_performance: bool | None = None
    optimize_for_manufacturing_yield: bool | None = None
    manufacturing_yield_weight: FiniteFloat | None = None
    use_maximum_distortion: bool | None = None
    max_distortion_pct: FiniteFloat | None = None

class NscOptimizationWizard(WizardBase):
    kind: Literal['nsc']
    is_clear_data_settings_used: bool | None = None
    is_raytrace_settings_used: bool | None = None
    is_split_rays_used: bool | None = None
    is_use_polarization_used: bool | None = None
    is_scatter_rays_used: bool | None = None
    is_ignore_errors_used: bool | None = None
    is_use_lightning_trace_used: bool | None = None
    is_criterion_settings_used: bool | None = None
    is_minimum_flux_used: bool | None = None
    is_overwrite_used: bool | None = None
    is_target_settings_used: bool | None = None
    is_color_targets_used: bool | None = None
    is_resample_detector_used: bool | None = None
    clear_detector: Index | None = None
    criterion: Index | None = None
    use_source: Index | None = None
    use_detector: Index | None = None
    boundary: Index | None = None
    start_at: PositiveIndex | None = None
    configuration: Index | None = None
    bitmap_file: Index | None = None
    ray_sampling: Index | None = None
    edge_sampling: Index | None = None
    target: FiniteFloat | None = None
    minimum_flux: FiniteFloat | None = None
    overall_weight: FiniteFloat | None = None
    total_flux: FiniteFloat | None = None

class NscBitmapWizard(WizardBase):
    kind: Literal['bitmap']
    is_clear_data_settings_used: bool | None = None
    is_raytrace_settings_used: bool | None = None
    is_split_rays_used: bool | None = None
    is_use_polarization_used: bool | None = None
    is_scatter_rays_used: bool | None = None
    is_ignore_errors_used: bool | None = None
    is_use_lightning_trace_used: bool | None = None
    is_criterion_settings_used: bool | None = None
    is_minimum_flux_used: bool | None = None
    is_overwrite_used: bool | None = None
    is_target_settings_used: bool | None = None
    is_color_targets_used: bool | None = None
    is_resample_detector_used: bool | None = None
    clear_detector: Index | None = None
    criterion: Index | None = None
    use_source: Index | None = None
    use_detector: Index | None = None
    boundary: Index | None = None
    start_at: PositiveIndex | None = None
    configuration: Index | None = None
    bitmap_file: Index | None = None
    ray_sampling: Index | None = None
    edge_sampling: Index | None = None
    target: FiniteFloat | None = None
    minimum_flux: FiniteFloat | None = None
    overall_weight: FiniteFloat | None = None
    total_flux: FiniteFloat | None = None

class NscRoadwayWizard(WizardBase):
    kind: Literal['roadway']
    is_split_rays_used: bool | None = None
    is_scatter_rays_used: bool | None = None
    is_use_polarization_used: bool | None = None
    is_ignore_errors_used: bool | None = None
    arrangement: Index | None = None
    origin: Index | None = None
    number_of_lanes: PositiveIndex | None = None
    surface_classification: Index | None = None
    road_class: Index | None = None
    start_at: PositiveIndex | None = None
    configuration: Index | None = None
    mounting_height: FiniteFloat | None = None
    longitudinal_spacing: FiniteFloat | None = None
    lateral_offset: FiniteFloat | None = None
    lane_width: FiniteFloat | None = None
    overall_weight: FiniteFloat | None = None

WizardRequest = Annotated[SequentialWizard | NscOptimizationWizard | NscBitmapWizard | NscRoadwayWizard, Field(discriminator="kind")]

class OptimizationWizard(Request):
    request: WizardRequest

class WizardOptions(Request):
    kind: Literal['sequential', 'nsc', 'bitmap', 'roadway']

WIZARD_FIELDS = {'sequential': {'criterion': 'Criterion', 'spatial_frequency': 'SpatialFrequency', 'xs_weight': 'XSWeight', 'yt_weight': 'YTWeight', 'type': 'Type', 'reference': 'Reference', 'use_gaussian_quadrature': 'UseGaussianQuadrature', 'use_rectangular_array': 'UseRectangularArray', 'rings': 'Rings', 'arms': 'Arms', 'obscuration': 'Obscuration', 'grid_size_nx_n': 'GridSizeNxN', 'delete_vignetted': 'DeleteVignetted', 'use_glass_boundary_values': 'UseGlassBoundaryValues', 'glass_min': 'GlassMin', 'glass_max': 'GlassMax', 'glass_edge_thickness': 'GlassEdgeThickness', 'use_air_boundary_values': 'UseAirBoundaryValues', 'air_min': 'AirMin', 'air_max': 'AirMax', 'air_edge_thickness': 'AirEdgeThickness', 'start_at': 'StartAt', 'overall_weight': 'OverallWeight', 'configuration_number': 'ConfigurationNumber', 'use_all_configurations': 'UseAllConfigurations', 'field_number': 'FieldNumber', 'use_all_fields': 'UseAllFields', 'assume_axial_symmetry': 'AssumeAxialSymmetry', 'ignore_lateral_color': 'IgnoreLateralColor', 'add_favorite_operands': 'AddFavoriteOperands', 'optimize_for_best_nominal_performance': 'OptimizeForBestNominalPerformance', 'optimize_for_manufacturing_yield': 'OptimizeForManufacturingYield', 'manufacturing_yield_weight': 'ManufacturingYieldWeight', 'use_maximum_distortion': 'UseMaximumDistortion', 'max_distortion_pct': 'MaxDistortionPct'}, 'nsc': {'is_clear_data_settings_used': 'IsClearDataSettingsUsed', 'is_raytrace_settings_used': 'IsRaytraceSettingsUsed', 'is_split_rays_used': 'IsSplitRaysUsed', 'is_use_polarization_used': 'IsUsePolarizationUsed', 'is_scatter_rays_used': 'IsScatterRaysUsed', 'is_ignore_errors_used': 'IsIgnoreErrorsUsed', 'is_use_lightning_trace_used': 'IsUseLightningTraceUsed', 'is_criterion_settings_used': 'IsCriterionSettingsUsed', 'is_minimum_flux_used': 'IsMinimumFluxUsed', 'is_overwrite_used': 'IsOverwriteUsed', 'is_target_settings_used': 'IsTargetSettingsUsed', 'is_color_targets_used': 'IsColorTargetsUsed', 'is_resample_detector_used': 'IsResampleDetectorUsed', 'clear_detector': 'ClearDetector', 'criterion': 'Criterion', 'use_source': 'UseSource', 'use_detector': 'UseDetector', 'boundary': 'Boundary', 'start_at': 'StartAt', 'configuration': 'Configuration', 'bitmap_file': 'BitmapFile', 'ray_sampling': 'RaySampling', 'edge_sampling': 'EdgeSampling', 'target': 'Target', 'minimum_flux': 'MinimumFlux', 'overall_weight': 'OverallWeight', 'total_flux': 'TotalFlux'}, 'bitmap': {'is_clear_data_settings_used': 'IsClearDataSettingsUsed', 'is_raytrace_settings_used': 'IsRaytraceSettingsUsed', 'is_split_rays_used': 'IsSplitRaysUsed', 'is_use_polarization_used': 'IsUsePolarizationUsed', 'is_scatter_rays_used': 'IsScatterRaysUsed', 'is_ignore_errors_used': 'IsIgnoreErrorsUsed', 'is_use_lightning_trace_used': 'IsUseLightningTraceUsed', 'is_criterion_settings_used': 'IsCriterionSettingsUsed', 'is_minimum_flux_used': 'IsMinimumFluxUsed', 'is_overwrite_used': 'IsOverwriteUsed', 'is_target_settings_used': 'IsTargetSettingsUsed', 'is_color_targets_used': 'IsColorTargetsUsed', 'is_resample_detector_used': 'IsResampleDetectorUsed', 'clear_detector': 'ClearDetector', 'criterion': 'Criterion', 'use_source': 'UseSource', 'use_detector': 'UseDetector', 'boundary': 'Boundary', 'start_at': 'StartAt', 'configuration': 'Configuration', 'bitmap_file': 'BitmapFile', 'ray_sampling': 'RaySampling', 'edge_sampling': 'EdgeSampling', 'target': 'Target', 'minimum_flux': 'MinimumFlux', 'overall_weight': 'OverallWeight', 'total_flux': 'TotalFlux'}, 'roadway': {'is_split_rays_used': 'IsSplitRaysUsed', 'is_scatter_rays_used': 'IsScatterRaysUsed', 'is_use_polarization_used': 'IsUsePolarizationUsed', 'is_ignore_errors_used': 'IsIgnoreErrorsUsed', 'arrangement': 'Arrangement', 'origin': 'Origin', 'number_of_lanes': 'NumberOfLanes', 'surface_classification': 'SurfaceClassification', 'road_class': 'RoadClass', 'start_at': 'StartAt', 'configuration': 'Configuration', 'mounting_height': 'MountingHeight', 'longitudinal_spacing': 'LongitudinalSpacing', 'lateral_offset': 'LateralOffset', 'lane_width': 'LaneWidth', 'overall_weight': 'OverallWeight'}}
