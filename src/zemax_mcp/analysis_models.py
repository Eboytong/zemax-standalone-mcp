"""Explicit settings models for the installed sequential analysis families."""
from typing import Annotated, Literal
from pydantic import Field,model_validator
from .schema import Request, Index, PositiveIndex, Positive, FiniteFloat
from .universal_grid import UniversalPlot2D
from .universal import UniversalPlot1D
from .coating_models import CoatingAngle, CoatingWavelength, CoatingListing
from .material_models import InternalTransmission
from .polarization_models import PolarizationPupilMap
from .comparator import FileComparator
from .system_check import SystemCheck, SystemDataReport
from .pupil_topics import PupilAberration
from .path_models import PathAnalysis,CriticalRayTrace,NscSingleRayTrace,NscGeometricMtf
from .sag_table import SagTable
from .test_plates import TestPlateList
from .power_maps import PowerFieldMap,PowerPupilMap
from .ima_viewer import ImaBimViewer
from .ray_database import RayDatabaseViewer
from .biocular_fov import BiocularFov
from .biocular import BiocularConvergence
from .ray_diagrams import YYbarDiagram,IncidentAngleVsImageHeight
from .gaussian_models import ParaxialGaussianBeam,SkewGaussianBeam
Sampling=Literal["S_32x32","S_64x64","S_128x128","S_256x256","S_512x512","S_1024x1024"]
SurfaceSampling=Literal["S_33x33","S_65x65","S_129x129","S_257x257","S_513x513","S_1025x1025"]
ContrastLossSampling=Literal["S_3x3","S_5x5","S_7x7","S_9x9","S_11x11","S_13x13","S_15x15","S_17x17","S_19x19","S_21x21","S_23x23","S_25x25","S_27x27","S_29x29","S_31x31","S_33x33","S_35x35","S_37x37","S_39x39","S_41x41","S_43x43","S_45x45","S_47x47","S_49x49","S_51x51","S_53x53","S_55x55","S_57x57","S_59x59","S_61x61","S_63x63","S_65x65","S_67x67","S_69x69","S_71x71","S_73x73","S_75x75","S_77x77","S_79x79","S_81x81","S_83x83"]

class Selection(Request):
    field: Index = 1
    wavelength: Index = 1

class MtfAnalysis(Selection):
    kind: Literal["huygens_mtf", "geometric_mtf"]
    sampling: Sampling = "S_64x64"
    image_sampling: Sampling = "S_64x64"
    maximum_frequency: Positive = 50
    use_polarization: bool = False
    image_delta: Annotated[FiniteFloat, Field(ge=0)] = 0
    multiply_by_diffraction_limit: bool = False

    @model_validator(mode="after")
    def applicable(self):
        if self.kind=="geometric_mtf"and (self.image_sampling!="S_64x64"or self.image_delta!=0):raise ValueError("几何 MTF 不使用像面网格采样和 ImageDelta。")
        if self.kind=="huygens_mtf"and self.multiply_by_diffraction_limit:raise ValueError("此选项适用于几何 MTF。")
        return self


ImageSampling = Literal["S_32x32", "S_64x64", "S_128x128", "S_256x256", "S_512x512", "S_1024x1024"]
ImageFlip = Literal["None", "TopBottom", "LeftRight", "TopBottomLeftRight"]
ImageRotation = Literal["Rotate_0", "Rotate_90", "Rotate_180", "Rotate_270"]
ImageOversampling = Literal["None", "X2", "X4", "X8", "X16", "X32", "X64"]
ImageAberrations = Literal["None", "Geometric", "Diffraction"]

class ImageSimulation(Request):
    field: PositiveIndex = 1
    wavelength: PositiveIndex | Literal["RGB", "1+2+3"] = "RGB"
    kind: Literal["image_simulation"]
    input_file: Annotated[str, Field(min_length=1,max_length=260)]
    field_height: Positive = 1.0
    flip_source: ImageFlip = "None"
    rotation_source: ImageRotation = "Rotate_0"
    oversampling: ImageOversampling = "X2"
    guard_band: ImageOversampling = "X2"
    pupil_sampling: ImageSampling = "S_64x64"
    image_sampling: ImageSampling = "S_64x64"
    aberrations: ImageAberrations = "Geometric"
    psf_x_points: Annotated[int, Field(strict=True, ge=1, le=4096)] = 5
    psf_y_points: Annotated[int, Field(strict=True, ge=1, le=4096)] = 5
    use_polarization: bool = False
    apply_fixed_apertures: bool = True
    use_relative_illumination: bool = True
    show_as: Literal["SimulatedImage", "SourceBitmap", "PSFGrid"] = "SimulatedImage"
    reference: Literal["ChiefRay", "Vertex", "PrimaryChief", "Centroid"] = "ChiefRay"
    flip_image: ImageFlip = "None"
    pixel_size: Annotated[FiniteFloat, Field(ge=0)] = 0
    x_pixels: Annotated[int, Field(strict=True, ge=0, le=16000)] = 0
    y_pixels: Annotated[int, Field(strict=True, ge=0, le=16000)] = 0
    suppress_frame: bool = False


class GeometricImage(Selection):
    field: PositiveIndex = 1
    surface: PositiveIndex | None = None
    kind: Literal["geometric_image"]
    field_size: Positive = 1.0
    image_size: Positive = 1.0
    input_file: Annotated[str, Field(min_length=1,max_length=260)]
    rotation: FiniteFloat = 0
    rays_x1000: Annotated[int, Field(strict=True, ge=1, le=1000000)] = 1000
    show_as: Literal["Surface", "Contour", "GreyScale", "InverseGreyScale", "FalseColor", "InverseFalseColor", "SpotDiagram", "CrossX", "CrossY"] = "FalseColor"
    source: Literal["Uniform", "Lambertian"] = "Uniform"
    number_of_pixels: Annotated[int, Field(strict=True, ge=1, le=4096)] = 256
    na: Annotated[FiniteFloat, Field(ge=0, le=1)] = 0.0
    total_watts: Positive = 1.0
    parity: Literal["Even", "Odd"] = "Even"
    reference: Literal["ChiefRay", "Vertex", "PrimaryChief", "Centroid"] = "ChiefRay"
    use_symbols: bool = False
    use_polarization: bool = False
    remove_vignetting_factors: bool = True
    scatter_rays: bool = False
    delete_vignetted: bool = True
    use_pixel_interpolation: bool = True

    row_column_number: Annotated[int, Field(strict=True, ge=0, le=4096)] = 0

    @model_validator(mode="after")
    def row_selection(self):
        if self.row_column_number and self.show_as not in {"CrossX", "CrossY"}:
            raise ValueError("显式行列编号适用于 CrossX/CrossY。")
        if self.row_column_number > self.number_of_pixels:
            raise ValueError("行列编号超出像素数量。")
        return self

class GeometricBitmapImage(GeometricImage):
    kind: Literal["geometric_bitmap_image"]

class FftLineEdge(Selection):
    kind: Literal["fft_line_edge_spread"]
    sampling: Sampling = "S_64x64"
    spread: Literal["Line", "Edge"] = "Line"
    data_type: Literal["X_Linear", "Y_Linear", "X_Logarithmic", "Y_Logarithmic", "X_Phase", "Y_Phase", "X_RealPart", "Y_RealPart", "X_ImaginaryPart", "Y_ImaginaryPart"] = "X_Linear"
    use_coherent_psf: bool = False
    use_polarization: bool = False
    plot_scale: Annotated[FiniteFloat, Field(ge=0)] = 0


class GeometricLineEdge(Selection):
    kind: Literal["geometric_line_edge_spread"]
    surface: PositiveIndex | None = None
    sampling: Sampling = "S_64x64"
    data_type: Literal["LineEdge", "Line", "Edge"] = "LineEdge"
    use_polarization: bool = False
    radius_maximum: Annotated[FiniteFloat, Field(ge=0)] = 0


class ExtendedSourceEnergy(Selection):
    kind: Literal["extended_source_encircled_energy"]
    surface: PositiveIndex | None = None
    image_name: Annotated[str, Field(min_length=1,max_length=260)]
    data_type: Literal["Encircled", "X_Only", "Y_Only", "Ensquared", "X_Distrib", "Y_Distrib"] = "Encircled"
    reference: Literal["ChiefRay", "Centroid", "Vertex"] = "Centroid"
    rays_x1000: Annotated[int, Field(strict=True, ge=1, le=1000000)] = 100
    multiply_by_diffraction_limit: bool = False
    remove_vignetting_factors: bool = True
    use_dashes: bool = False
    use_polarization: bool = False
    maximum_distance: Annotated[FiniteFloat, Field(ge=0)] = 0
    field_size: Positive = 1
    rotation: FiniteFloat = 0


    @model_validator(mode="after")
    def diffraction_condition(self):
        if self.multiply_by_diffraction_limit and self.data_type != "Encircled":
            raise ValueError("扩展源衍射极限修正适用于 Encircled。")
        return self


class ThroughFocus(Selection):
    kind: Literal["fft_through_focus_mtf", "huygens_through_focus_mtf", "geometric_through_focus_mtf"]
    sampling: Sampling = "S_64x64"
    frequency: Positive = 50
    delta_focus: Positive = .1
    number_of_steps: Annotated[int, Field(strict=True, ge=3, le=1001)] = 11
    use_polarization: bool = False
    multiply_by_diffraction_limit: bool | None = None

    @model_validator(mode="after")
    def applicable(self):
        if self.kind!="geometric_through_focus_mtf"and self.multiply_by_diffraction_limit is not None:
            raise ValueError("衍射修正开关适用于几何离焦 MTF。")
        return self

class PsfAnalysis(Selection):
    kind: Literal["fft_psf", "fft_psf_cross", "huygens_psf", "huygens_psf_cross"]
    sampling: Sampling = "S_64x64"
    image_sampling: Sampling = "S_64x64"
    image_delta: Annotated[FiniteFloat, Field(ge=0)] = 0
    normalize: bool = True
    use_polarization: bool = False

    @model_validator(mode="after")
    def applicable(self):
        if self.kind=="fft_psf_cross"and(self.image_delta!=0 or self.image_sampling!="S_64x64"):raise ValueError("FFT PSF 截面不提供这两个像面网格设置。")
        return self

class EnergyAnalysis(Selection):
    kind: Literal["diffraction_encircled_energy", "geometric_encircled_energy"]
    sampling: Sampling = "S_64x64"
    reference: Literal["ChiefRay", "Centroid", "Vertex"] = "Centroid"
    maximum_radius: Positive = 100
    use_polarization: bool = False
    multiply_by_diffraction_limit: bool | None = None

    @model_validator(mode="after")
    def applicable(self):
        if self.kind!="geometric_encircled_energy"and self.multiply_by_diffraction_limit is not None:
            raise ValueError("衍射修正开关适用于几何圈入能量。")
        return self

class WavefrontAnalysis(Selection):
    kind: Literal["wavefront"]
    sampling: Sampling = "S_64x64"
    remove_tilt: bool = True
    use_exit_pupil: bool = True
    include_pupil_mapping: bool = False

class ZernikeAnalysis(Selection):
    kind: Literal["zernike_standard", "zernike_fringe", "zernike_annular"]
    sampling: Sampling = "S_64x64"
    maximum_terms: Annotated[int, Field(strict=True, ge=1, le=231)] = 22
    obscuration: Annotated[FiniteFloat, Field(ge=0, lt=1)] = 0

    @model_validator(mode="after")
    def applicable(self):
        if self.kind=="zernike_fringe"and self.obscuration!=0:raise ValueError("Fringe 系数不使用环形遮挡参数。")
        if self.kind=="zernike_fringe"and self.maximum_terms>37:raise ValueError("Fringe 最大项数为 37。")
        return self

class FanAnalysis(Selection):
    kind: Literal["ray_fan", "opd_fan"]
    number_of_rays: Annotated[int, Field(strict=True, ge=3, le=10001)] = 101
    check_apertures: bool = True
    vignetted_pupil: bool = True

class FieldAnalysis(Request):
    kind: Literal["field_curvature_distortion"]
    wavelength: Index = 0
    ignore_vignette: bool = False

class Foucault(Request):
    kind: Literal["foucault"]
    field: Index = 1
    wavelength: Index = 1
    sampling: Sampling = "S_64x64"
    intensity_scale: Literal["Linear", "Log_Minus_3", "Log_Minus_6", "Log_Minus_9", "Log_Minus_12", "Log_Minus_15", "Log_Minus_18"] = "Linear"
    show_as: Literal["Surface", "Contour", "GreyScale", "InverseGreyScale", "FalseColor", "InverseFalseColor", "X_CrossSection", "Y_CrossSection"] = "FalseColor"
    knife: Literal["Horiz_Above", "Horiz_Below", "Vert_Right", "Vert_Left"] = "Horiz_Above"
    data: Literal["Computed", "Reference", "Difference"] = "Computed"
    row_column: Annotated[int, Field(strict=True, ge=0, le=16383)] = 0
    use_polarization: bool = False
    y_position: FiniteFloat = 0
    decenter_x: FiniteFloat = 0
    decenter_y: FiniteFloat = 0
    scale_x: Positive = 1
    scale_y: Positive = 1
    source: Annotated[str, Field(min_length=1)] | None = None

    @model_validator(mode="after")
    def reference_source(self):
        if self.data in {"Reference", "Difference"} and self.source is None:
            raise ValueError("Reference 和 Difference 需要 source BMP 文件。")
        return self

class FullFieldAberration(Request):
    kind: Literal["full_field_aberration"]
    field: Index = 1
    wavelength: Index = 1
    field_shape: Literal["Rectangular", "Elliptical"] = "Rectangular"
    x_field_width: Positive = 1
    y_field_width: Positive = 1
    decomposition: Literal["ZernikeTerms"] = "ZernikeTerms"
    aberration_type: Literal["Defocus", "PrimaryAstigmatism", "PrimaryComa", "SpecifiedTerm"] = "Defocus"
    aberration_number: Annotated[int, Field(strict=True, ge=1, le=100)] | None = None
    maximum_term: Annotated[int, Field(strict=True, ge=1, le=100)] = 15
    x_field_sampling: Annotated[int, Field(strict=True, ge=2, le=100)] = 11
    y_field_sampling: Annotated[int, Field(strict=True, ge=2, le=100)] = 11
    pupil_sampling: Literal["S_32x32", "S_64x64", "S_128x128", "S_256x256", "S_512x512", "S_1024x1024"] = "S_64x64"
    show_as: Literal["GreyScale", "GreyScaleInverted", "FalseColor", "FalseColorInverted", "Icons"] = "FalseColor"
    display: Literal["Absolute", "Relative", "Average"] = "Absolute"

    @model_validator(mode="after")
    def aberration_selection(self):
        if self.aberration_type == "SpecifiedTerm" and self.aberration_number is None:
            raise ValueError("SpecifiedTerm 必须提供 aberration_number。")
        if self.aberration_type != "SpecifiedTerm" and self.aberration_number is not None:
            raise ValueError("aberration_number 仅适用于 SpecifiedTerm。")
        return self
class ColorAnalysis(Request):
    kind: Literal["longitudinal_aberration", "lateral_color", "focal_shift"]

class SurfaceAnalysis(Request):
    kind: Literal["surface_sag", "surface_curvature", "surface_phase", "surface_sag_cross", "surface_curvature_cross", "surface_phase_cross"]
    surface: PositiveIndex
    sampling: SurfaceSampling = "S_65x65"
    angle: FiniteFloat = 0

    @model_validator(mode="after")
    def applicable(self):
        if not self.kind.endswith("_cross")and self.angle!=0:raise ValueError("Angle 用于曲面截面分析。")
        return self

class SlopeSettings(Request):
    surface: PositiveIndex
    remove_option: Literal["None","BaseROC","BestFitSphere","BaseSag","CompositeSag"] = "None"
    best_fit_sphere: Literal["MinimumVolume","MinimumRMS","MinimumRMSWithOffset"] | None = None
    reverse_direction: bool | None = None
    consider_off_axis_aperture: bool = False

    @model_validator(mode="after")
    def applicable_removal(self):
        if self.remove_option != "BestFitSphere" and (self.best_fit_sphere is not None or self.reverse_direction is not None):
            raise ValueError("Best-fit criterion and reverse direction require BestFitSphere removal.")
        if self.reverse_direction is not None and self.best_fit_sphere not in {None,"MinimumVolume"}:
            raise ValueError("Reverse direction requires MinimumVolume criterion.")
        return self

class SurfaceSlope(SlopeSettings):
    kind: Literal["surface_slope"]
    sampling: SurfaceSampling = "S_65x65"
    data_type: Literal["TangentialSlope","SagittalSlope","XSlope","YSlope","SlopeModulus"] = "TangentialSlope"
    show_as: Literal["Surface","Contour","GreyScale","InverseGreyScale","FalseColor","InverseFalseColor"] = "FalseColor"
    contour_format: str | None = None

class SurfaceSlopeCross(SlopeSettings):
    kind: Literal["surface_slope_cross"]
    sampling: Literal["S_33","S_65","S_129","S_257","S_513","S_1025","S_2049","S_4097","S_8193"] = "S_65"
    data_type: Literal["TangentialSlope","SagittalSlope","XSlope","YSlope","SlopeModulus"] = "TangentialSlope"
    angle: FiniteFloat = 0

class PhaseSlopeSettings(Request):
    surface: PositiveIndex
    data_type: Literal["PhaseSlopeTangential","PhaseSlopeSagittal","PhaseSlopeX","PhaseSlopeY","PhaseSlopeModulus"] = "PhaseSlopeTangential"
    remove_piston: bool = False
    remove_tilt_x: bool = False
    remove_tilt_y: bool = False
    remove_power: bool = False

class SurfacePhaseSlope(PhaseSlopeSettings):
    kind: Literal["surface_phase_slope"]
    sampling: SurfaceSampling = "S_65x65"
    show_as: Literal["Surface","Contour","GreyScale","InverseGreyScale","FalseColor","InverseFalseColor"] = "FalseColor"
    contour_format: str | None = None

class SurfacePhaseSlopeCross(PhaseSlopeSettings):
    kind: Literal["surface_phase_slope_cross"]
    sampling: Literal["S_33","S_65","S_129","S_257","S_513","S_1025","S_2049","S_4097","S_8193"] = "S_65"
    angle: FiniteFloat = 0

class ZernikeField(Request):
    kind: Literal["zernike_coefficients_vs_field"]
    wavelength: PositiveIndex = 1
    sampling: Sampling = "S_64x64"
    coefficient_type: Literal["Fringe","Standard","Annular"] = "Standard"
    coefficients: Annotated[list[Annotated[int,Field(strict=True,ge=0,le=231)]],Field(min_length=1,max_length=231)] = Field(default_factory=lambda: [4,5,6])
    field_scan: Literal["Plus_Y","Plus_X","Minus_Y","Minus_X"] = "Plus_Y"
    field_density: Annotated[int,Field(strict=True,ge=2,le=1001)] = 21
    obscuration: Annotated[FiniteFloat,Field(ge=0,lt=1)] = 0
    scale_minimum: FiniteFloat = 0
    scale_maximum: FiniteFloat = 0

    @model_validator(mode="after")
    def valid_coefficients(self):
        if self.coefficients != sorted(set(self.coefficients)):
            raise ValueError("Coefficients must be strictly increasing.")
        if 0 in self.coefficients and self.coefficients != [0]:
            raise ValueError("Zero selects all coefficients and must appear alone.")
        if self.coefficient_type == "Fringe" and max(self.coefficients)>37:
            raise ValueError("Fringe supports at most term 37.")
        if self.coefficient_type != "Annular" and self.obscuration != 0:
            raise ValueError("Nonzero obscuration requires Annular coefficients.")
        if self.scale_minimum != 0 and self.scale_maximum != 0 and self.scale_minimum >= self.scale_maximum:
            raise ValueError("Manual scale limits must increase.")
        return self

InterferogramBeam = Literal["Reference", *(f"Configuration_{i}" for i in range(1,21))]

class Interferogram(Request):
    kind: Literal["interferogram"]
    field: PositiveIndex = 1
    wavelength: PositiveIndex = 1
    surface: PositiveIndex | None = None
    sampling: Sampling = "S_64x64"
    show_as: Literal["Surface","Contour","GreyScale","InverseGreyScale","FalseColor","InverseFalseColor"] = "FalseColor"
    beam_1: InterferogramBeam = "Reference"
    beam_2: InterferogramBeam = "Configuration_1"
    ref_beam_1_to_vertex: bool = False
    ref_beam_2_to_vertex: bool = False
    use_exit_pupil: bool = True
    consider_opl: bool = False
    scale_factor: Positive = 1
    x_tilt: FiniteFloat = 0
    y_tilt: FiniteFloat = 0
    subaperture_x: Annotated[FiniteFloat,Field(ge=-1,le=1)] = 0
    subaperture_y: Annotated[FiniteFloat,Field(ge=-1,le=1)] = 0
    subaperture_radius: Annotated[FiniteFloat,Field(gt=0,le=1)] = 1
    contour_format: str | None = None

    @model_validator(mode="after")
    def vertex_reference_scale(self):
        if (self.ref_beam_1_to_vertex or self.ref_beam_2_to_vertex) and self.scale_factor != 1:
            raise ValueError("Vertex referencing requires scale_factor=1.")
        return self

class GrinProfile(Request):
    kind: Literal["grin_profile"]
    surface: PositiveIndex
    wavelength: Index = 1
    show_index_vs: Literal["X","Y","Z"] = Field(description="Surface-local scan axis. Supply bounds only for this axis and fixed coordinates only for the other two axes; lengths use current lens units.")
    minimum_x: FiniteFloat | None = None
    maximum_x: FiniteFloat | None = None
    minimum_y: FiniteFloat | None = None
    maximum_y: FiniteFloat | None = None
    minimum_z: FiniteFloat | None = None
    maximum_z: FiniteFloat | None = None
    x_value: FiniteFloat | None = None
    y_value: FiniteFloat | None = None
    z_value: FiniteFloat | None = None
    minimum_index: FiniteFloat | None = None
    maximum_index: FiniteFloat | None = None

    @model_validator(mode="after")
    def valid_ranges(self):
        for axis in ('x','y','z'):
            if axis.upper()!=self.show_index_vs and any(getattr(self,key+'_'+axis) is not None for key in ('minimum','maximum')):
                raise ValueError('GRIN bounds must select the show_index_vs axis.')
            if axis.upper()==self.show_index_vs and getattr(self,axis+'_value') is not None:
                raise ValueError('GRIN fixed coordinates must select the other two axes.')
        for low, high, name in ((self.minimum_x,self.maximum_x,"X"),(self.minimum_y,self.maximum_y,"Y"),
                                (self.minimum_z,self.maximum_z,"Z"),(self.minimum_index,self.maximum_index,"index")):
            if (low is None) != (high is None) or low is not None and high <= low:
                raise ValueError(f"GRIN {name} bounds must be supplied together and increasing.")
        return self

class NscSurfaceSag(Request):
    kind: Literal["nsc_surface_sag"]
    object_number: PositiveIndex
    face_number: Index
    sampling: Literal["S_33x33","S_65x65","S_129x129","S_257x257","S_513x513","S_1025x1025","S_2049x2049","S_4097x4097","S_8193x8193"] = "S_65x65"
    data: Literal["SurfaceSag"] = "SurfaceSag"
    show_as: Literal["Surface","Contour","GreyScale","InverseGreyScale","FalseColor","InverseFalseColor","X_CrossSection","Y_CrossSection"] = "Surface"
    offset: FiniteFloat | None = None
    width: Positive | None = None
    rotation: FiniteFloat | None = None
    decenter_x: FiniteFloat | None = None
    decenter_y: FiniteFloat | None = None
    contour_format: str | None = None
    remove_option: Literal["None","BaseROC","BestFitSphere","AverageSag","MinimumSag"] = "None"
    best_fit_sphere_option: Literal["MinimumVolume","MinimumRMS","MinimumRMSWithOffset"] = "MinimumRMS"
    bfs_reverse_direction: bool | None = None
    keep_object_tilts: bool | None = None
    probe_ray_offset: FiniteFloat | None = None
    keep_zrd: bool = False
    zrd_filename: str | None = None

    @model_validator(mode="after")
    def valid_output(self):
        if self.contour_format is not None and ("\n" in self.contour_format or "\r" in self.contour_format):
            raise ValueError("ContourFormat must be a single line.")
        if self.keep_zrd != (self.zrd_filename is not None):
            raise ValueError("keep_zrd and zrd_filename must be supplied together.")
        if self.zrd_filename is not None and ("/" in self.zrd_filename or chr(92) in self.zrd_filename or not self.zrd_filename.casefold().endswith(".zrd")):
            raise ValueError("zrd_filename must be a local .zrd filename without a directory.")
        return self

DiffEfficiency2DSampling = Literal["S_32x32","S_64x64","S_128x128","S_256x256","S_512x512","S_1024x1024","S_2048x2048","S_4096x4096","S_8192x8192","S_16384x16384"]
DiffEfficiencyLineSampling = Literal["S_33","S_65","S_129","S_257","S_513","S_1025","S_2049","S_4097","S_8193"]

class DiffEfficiencyBase(Request):
    field: Index = 1
    wavelength: Index = 1
    surface: PositiveIndex | None = None
    hologram_object: PositiveIndex | None = None
    ambient_object: PositiveIndex | None = None
    detector_object: PositiveIndex | None = None
    source_position_x: FiniteFloat | None = None
    source_position_y: FiniteFloat | None = None
    source_position_z: FiniteFloat | None = None
    source_unpolarized: bool | None = None
    source_x_tilted: bool | None = None
    source_polarization_jx: FiniteFloat | None = None
    source_polarization_jy: FiniteFloat | None = None
    source_pre_propagation: FiniteFloat | None = None
    inside_of_object: Index | None = None

class DiffEfficiency2D(DiffEfficiencyBase):
    kind: Literal["diff_efficiency_2d"]
    sample_size: DiffEfficiency2DSampling = "S_64x64"
    min_wavelength: Positive | None = None
    max_wavelength: Positive | None = None
    min_angle: FiniteFloat | None = None
    max_angle: FiniteFloat | None = None

    @model_validator(mode="after")
    def valid_ranges(self):
        for low, high, label in ((self.min_wavelength,self.max_wavelength,"wavelength"),(self.min_angle,self.max_angle,"angle")):
            if (low is None) != (high is None) or low is not None and high <= low:
                raise ValueError(f"DiffEfficiency2D {label} bounds must be supplied together and increasing.")
        return self

class DiffEfficiencyAngular(DiffEfficiencyBase):
    kind: Literal["diff_efficiency_angular"]
    sample_size: DiffEfficiencyLineSampling = "S_65"
    min_angle: FiniteFloat | None = None
    max_angle: FiniteFloat | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if (self.min_angle is None) != (self.max_angle is None) or self.min_angle is not None and self.max_angle <= self.min_angle:
            raise ValueError("Angular bounds must be supplied together and increasing.")
        return self

class DiffEfficiencyChromatic(DiffEfficiencyBase):
    kind: Literal["diff_efficiency_chromatic"]
    sample_size: DiffEfficiencyLineSampling = "S_65"
    min_wavelength: Positive | None = None
    max_wavelength: Positive | None = None

    @model_validator(mode="after")
    def valid_range(self):
        if (self.min_wavelength is None) != (self.max_wavelength is None) or self.min_wavelength is not None and self.max_wavelength <= self.min_wavelength:
            raise ValueError("Wavelength bounds must be supplied together and increasing.")
        return self


ScanType = Literal["Plus_Y", "Plus_X", "Minus_Y", "Minus_X"]
AnalysisMethod = Literal["auto", "native", "ray_trace"]

class RelativeIllumination(Request):
    kind: Literal["relative_illumination"]
    wavelength: PositiveIndex = 1
    scan_type: ScanType = "Plus_Y"
    ray_density: Annotated[int, Field(strict=True, ge=5, le=200)] = 10
    field_density: Annotated[int, Field(strict=True, ge=2, le=100)] = 21
    use_polarization: bool = False
    remove_vignetting_factors: bool = True
    log_scale: bool = False

class FieldMtf(Request):
    kind: Literal["fft_mtf_vs_field"]
    wavelength: Index = 1
    frequencies: Annotated[list[Positive], Field(min_length=1, max_length=6)] = Field(default_factory=lambda: [10,30,50])
    sampling: Sampling = "S_64x64"
    scan_type: ScanType = "Plus_Y"
    field_density: Annotated[int, Field(strict=True, ge=2, le=100)] = 21
    use_polarization: bool = False
    remove_vignetting_factors: bool = True

    @model_validator(mode="after")
    def distinct_frequencies(self):
        if len(set(self.frequencies)) != len(self.frequencies):
            raise ValueError("频率不得重复。")
        return self

class FftSurfaceMtf(Request):
    kind: Literal["fft_surface_mtf"]
    field: Index = 1
    wavelength: Index = 1
    mtf_type: Literal["MTF_Incoherent", "Real_Incoherent", "Imaginary_Incoherent", "MTF_Coherent", "Real_Coherent", "Imaginary_Coherent"] = "MTF_Incoherent"
    rotation: Literal["Rotate_0", "Rotate_90", "Rotate_180", "Rotate_270"] = "Rotate_0"
    sampling: Sampling = "S_64x64"
    show_as: Literal["Surface", "Contour", "GreyScale", "InverseGreyScale", "FalseColor", "InverseFalseColor"] = "FalseColor"
    use_polarization: bool = False
    scale_factor: Positive = 1

class HuygensSurfaceMtf(Request):
    kind: Literal["huygens_surface_mtf"]
    field: Index = 1
    wavelength: Index = 1
    sampling: Sampling = "S_64x64"
    image_sampling: Sampling = "S_64x64"
    mtf_type: Literal["MTF_Incoherent", "Real_Incoherent", "Imaginary_Incoherent", "MTF_Coherent", "Real_Coherent", "Imaginary_Coherent"] = "MTF_Incoherent"
    show_as: Literal["GreyScale", "InverseGreyScale", "FalseColor", "InverseFalseColor"] = "FalseColor"
    use_polarization: bool = False
    image_delta: Annotated[FiniteFloat, Field(ge=0)] = 0
class ConfigurationMatrixSpot(Request):
    kind: Literal["matrix_spot", "configuration_matrix_spot"]
    pattern: Literal["Square", "Hexapolar", "Dithered"] = "Hexapolar"
    reference: Literal["ChiefRay", "Centroid", "Middle", "Vertex"] = "Centroid"
    show_scale: Literal["ScaleBar", "Box", "Cross", "Circle"] = "ScaleBar"
    color_rays_by: Literal["Fields", "Waves", "Config", "Wavelength"] = "Config"
    ray_density: Annotated[int, Field(strict=True, ge=1, le=100)] = 6
    direction_cosines: bool = False
    use_symbols: bool = False
    use_polarization: bool = False
    scatter_rays: bool = False
    show_airy_disk: bool = False
    ignore_lateral_color: bool = False

class FullFieldSpot(ConfigurationMatrixSpot):
    kind: Literal['full_field_spot']
    field: Index = 0
    wavelength: Index = 0
    surface: PositiveIndex | None = None
    color_rays_by: Literal['Fields', 'Waves', 'Config', 'Wavelength'] = 'Fields'
    plot_scale: Annotated[FiniteFloat, Field(ge=0)] = 0
    exaggerate: Positive = 1
class GeometricFieldMtf(FieldMtf):
    kind: Literal["geometric_mtf_vs_field"]
    multiply_by_diffraction_limit: bool = False
    scatter_rays: bool = False

class HuygensFieldMtf(FieldMtf):
    kind: Literal["huygens_mtf_vs_field"]
    image_delta: Annotated[FiniteFloat, Field(ge=0)] = 0

class MtfMap(Request):
    kind: Literal["fft_mtf_map"]
    x_field_width: Positive
    y_field_width: Positive
    frequency: Positive = 50
    reference_field: Index = 0
    wavelength: Index = 1
    sampling: Sampling = "S_64x64"
    x_pixels: Annotated[int, Field(strict=True,ge=3,le=100)] = 11
    y_pixels: Annotated[int, Field(strict=True,ge=3,le=100)] = 11
    data_type: Literal["Average","Tangential","Sagittal"] = "Average"
    use_polarization: bool = False
    remove_vignetting_factors: bool = True

class GeometricMtfMap(MtfMap):
    kind: Literal["geometric_mtf_map"]
    scatter_rays: bool = False

class Vignetting(Request):
    kind: Literal["vignetting"]
    ray_density: Annotated[int, Field(strict=True, ge=5, le=200)] = 10
    field_density: Annotated[int, Field(strict=True, ge=2, le=100)] = 21
    remove_vignetting_factors: bool = True
    method: AnalysisMethod = "auto"

class Footprint(Request):
    kind: Literal["footprint"]
    surface: PositiveIndex
    field: Index = 0
    wavelength: Index = 0
    ray_density: Annotated[int, Field(strict=True, ge=1, le=200)] = 10
    delete_vignetted: bool = True
    method: AnalysisMethod = "auto"

class SingleRayTrace(Request):
    kind: Literal["single_ray_trace"]
    wavelength: PositiveIndex = 1
    hx: Annotated[FiniteFloat,Field(ge=-1,le=1)] = 0
    hy: Annotated[FiniteFloat,Field(ge=-1,le=1)] = 0
    px: Annotated[FiniteFloat,Field(ge=-1,le=1)] = 0
    py: Annotated[FiniteFloat,Field(ge=-1,le=1)] = 0
    use_global: bool = False
    ray_type: Literal["DirectionCosines","TangentAngle","YmUmYcUc"] = "DirectionCosines"

class CardinalPoints(Request):
    kind: Literal["cardinal_points"]
    wavelength: PositiveIndex = 1
    start_surface: PositiveIndex = 1
    end_surface: PositiveIndex | None = None
    orientation: Literal["YZ","XZ","both"] = "both"

class SeidelCoefficients(Request):
    kind: Literal["seidel_coefficients"]
    wavelength: PositiveIndex = 1

class SeidelDiagram(Request):
    kind: Literal["seidel_diagram"]
    ignore_chromatic: bool = False
    ignore_distortion: bool = False
    suppress_frame: bool = False
    plot_scale: Annotated[FiniteFloat,Field(ge=0)] = 0

class GridDistortion(Request):
    kind: Literal["grid_distortion"]
    field_width: Positive
    wavelength: PositiveIndex = 1
    reference_field: PositiveIndex = 1
    aspect: Positive = 1
    scale_factor: FiniteFloat = 1
    symmetric_magnification: bool = True
    grid_number: Annotated[int,Field(strict=True,ge=0)] | None = None

class RmsBase(Request):
    wavelength: Index = 1
    data_type: Literal["Wavefront","SpotRadius","Spot_X","Spot_Y","StrehlRatio"] = "SpotRadius"
    reference: Literal["Centroid","ChiefRay"] = "Centroid"
    method: Literal["RectArray","GaussQuad"] = "RectArray"
    sampling: Sampling | None = None
    rings: Annotated[int,Field(strict=True,ge=1,le=20)] | None = None
    use_polarization: bool = False
    show_diffraction_limit: bool = False

    @model_validator(mode="after")
    def applicable_rms(self):
        if self.method=='RectArray' and self.rings is not None:raise ValueError('RectArray使用sampling。')
        if self.method=='GaussQuad' and self.sampling is not None:raise ValueError('GaussQuad使用rings。')
        if self.data_type=='StrehlRatio' and self.wavelength==0:raise ValueError('StrehlRatio需要单色波长。')
        return self

class RmsField(RmsBase):
    kind: Literal["rms_vs_field"]
    field_density: Annotated[int,Field(strict=True,ge=5,le=100,multiple_of=5)] = 20
    orientation: ScanType = "Plus_Y"
    remove_vignetting_factors: bool = True

class RmsFieldMap(RmsBase):
    kind: Literal["rms_field_map"]
    field: PositiveIndex = 1
    surface: PositiveIndex | None = None
    x_field_sampling: Annotated[int,Field(strict=True,ge=5,le=101)] = 11
    y_field_sampling: Annotated[int,Field(strict=True,ge=5,le=101)] = 11
    x_field_size: Positive = 1
    y_field_size: Positive = 1
    show_as: Literal["Surface","Contour","GreyScale","InverseGreyScale","FalseColor","InverseFalseColor"] = "FalseColor"
    remove_vignetting_factors: bool = True

    @model_validator(mode="after")
    def rms_map_conditions(self):
        if self.show_diffraction_limit:
            raise ValueError('RMS Field Map has no diffraction-limit auxiliary line setting.')
        if self.data_type == "StrehlRatio" and self.wavelength == 0:
            raise ValueError("StrehlRatio requires a monochromatic wavelength.")
        return self

class RmsWavelength(Request):
    kind: Literal["rms_vs_wavelength"]
    field: Index = 0
    data_type: Literal["Wavefront","SpotRadius","Spot_X","Spot_Y","StrehlRatio"] = "SpotRadius"
    reference: Literal["Centroid","ChiefRay"] = "Centroid"
    method: Literal["RectArray","GaussQuad"] = "RectArray"
    sampling: Sampling | None = None
    rings: Annotated[int,Field(strict=True,ge=1,le=20)] | None = None
    wavelength_density: Annotated[int,Field(strict=True,ge=5,le=100,multiple_of=5)] = 20
    use_polarization: bool = False
    show_diffraction_limit: bool = False
    use_dashes: bool = False
    plot_scale: Annotated[FiniteFloat,Field(ge=0)] = 0

    @model_validator(mode="after")
    def applicable_sampling(self):
        if self.method == "RectArray" and self.rings is not None:
            raise ValueError("RectArray uses sampling.")
        if self.method == "GaussQuad" and self.sampling is not None:
            raise ValueError("GaussQuad uses rings.")
        return self


class ContrastLoss(Request):
    kind: Literal["contrast_loss"]
    field: PositiveIndex = 1
    wavelength: PositiveIndex = 1
    sampling: ContrastLossSampling = "S_41x41"
    frequency: Annotated[FiniteFloat,Field(ge=0)] = 50
    normalize: bool = True
    show_opd: bool = False

class RmsFocus(RmsBase):
    kind: Literal["rms_vs_focus"]
    minimum_focus: FiniteFloat = -.1
    maximum_focus: FiniteFloat = .1
    focus_density: Annotated[int,Field(strict=True,ge=5,le=100,multiple_of=5)] = 20

    @model_validator(mode="after")
    def ordered_focus(self):
        if self.minimum_focus>=self.maximum_focus:raise ValueError('焦移范围必须递增。')
        return self

class ThroughFocusSpot(Request):
    kind: Literal["through_focus_spot"]
    field: Index = 0
    wavelength: Index = 0
    reference: Literal["ChiefRay","Centroid","Middle","Vertex"] = "Centroid"
    pattern: Literal["Square","Hexapolar"] = "Hexapolar"
    ray_density: Annotated[int,Field(strict=True,ge=1,le=100)] = 6
    delta_focus_um: Positive = 100
    use_polarization: bool = False


class QuickYield(Request):
    kind: Literal["quick_yield"]
    field: PositiveIndex = 1
    wavelength: PositiveIndex = 1
    configuration: Annotated[int, Field(strict=True, ge=0, le=10000)] = 0
    monte_carlo_samples: Annotated[int, Field(strict=True, ge=1000, le=100000)] = 1000
    pupil_sampling: Annotated[int, Field(strict=True, ge=1, le=10)] = 3
    statistic: Literal["Normal", "Uniform", "Parabolic"] = "Normal"
    precision: Literal["Standard", "High", "VeryHigh"] = "Standard"
    compensation: Literal["Standard", "High", "VeryHigh"] = "Standard"
    field_mode: Literal["UserDefined"] = "UserDefined"
    compensator_strategy: Literal["OptimizeAllDampedLeastSquares", "ParaxialFocus", "Ignore", "OptimizeAllOrthogonalDescent"] = "OptimizeAllDampedLeastSquares"


class ToleranceYield(Request):
    kind: Literal["tolerance_yield"]
    operand: Index = 0
    tolerance_file: str | None = None


class ToleranceHistogram(Request):
    kind: Literal["tolerance_histogram"]
    operand: Index = 0
    tolerance_file: str | None = None
    minimum: FiniteFloat = 0
    maximum: FiniteFloat = 1
    bins: Annotated[int, Field(strict=True, ge=1, le=1000)] = 20

    @model_validator(mode="after")
    def valid_range(self):
        if self.maximum <= self.minimum:
            raise ValueError("直方图最大值必须大于最小值。")
        return self

AnalysisRequest = Annotated[RayDatabaseViewer|ImaBimViewer|PowerFieldMap|PowerPupilMap|TestPlateList|BiocularFov|BiocularConvergence|YYbarDiagram|IncidentAngleVsImageHeight|SagTable|ParaxialGaussianBeam|SkewGaussianBeam|UniversalPlot2D|UniversalPlot1D|SystemDataReport|SystemCheck|FullFieldSpot|PupilAberration|FileComparator|PolarizationPupilMap|NscGeometricMtf|CriticalRayTrace|NscSingleRayTrace|PathAnalysis|InternalTransmission|CoatingAngle|CoatingWavelength|CoatingListing|FftLineEdge|GeometricLineEdge|ExtendedSourceEnergy|ImageSimulation|GeometricImage|GeometricBitmapImage|RmsField|RmsFieldMap|RmsFocus|RmsWavelength|ContrastLoss|ThroughFocusSpot|QuickYield|ToleranceYield|ToleranceHistogram|SingleRayTrace|CardinalPoints|SeidelCoefficients|SeidelDiagram|GridDistortion|GeometricFieldMtf|HuygensFieldMtf|MtfMap|GeometricMtfMap|RelativeIllumination|FieldMtf|FftSurfaceMtf|HuygensSurfaceMtf|ConfigurationMatrixSpot|Vignetting|Footprint|DiffEfficiency2D|DiffEfficiencyAngular|DiffEfficiencyChromatic|GrinProfile|NscSurfaceSag|MtfAnalysis|ThroughFocus|PsfAnalysis|EnergyAnalysis|WavefrontAnalysis|ZernikeAnalysis|ZernikeField|Interferogram|FanAnalysis|FieldAnalysis|ColorAnalysis|SurfaceAnalysis|SurfaceSlope|SurfaceSlopeCross|SurfacePhaseSlope|SurfacePhaseSlopeCross|Foucault|FullFieldAberration, Field(discriminator="kind")]

class RunAnalysis(Request):
    request: AnalysisRequest
