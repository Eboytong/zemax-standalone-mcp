"""The same request validation is used by MCP and the private worker protocol."""

from typing import Annotated, Literal, Any

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from .schema import Index, PositiveIndex, Weight, Positive, Request


class Empty(Request):
    pass


class Capabilities(Request):
    topic: Literal["all", "settings", "tool", "merit_cells", "optimization_diagnostics", "index", "detail", "dependencies"] = "all"
    capability_id: str | None = None
    tool_name: str | None = None
    start: PositiveIndex = 1
    count: Annotated[int, Field(strict=True, ge=1, le=100)] = 20


class ToolResponse(BaseModel):
    ok: bool
    data: dict[str, Any] | None
    error: dict[str, Any] | None
    warnings: list[str]
    context: dict[str, Any]
    artifacts: list[dict[str, Any]]


class Connect(Request):
    install_dir: str | None = None


class OpenLens(Request):
    path: str


class SaveLens(Request):
    path: str
    overwrite: bool = False


class GetSurfaces(Request):
    start: Index = 0
    count: Annotated[int, Field(strict=True, ge=1, le=200)] = 50
    parameter_start: Annotated[int, Field(strict=True, ge=1, le=254)] = 1
    parameter_count: Annotated[int, Field(strict=True, ge=1, le=254)] = 20


class MeritRange(Request):
    start: PositiveIndex = 1
    count: Annotated[int, Field(strict=True, ge=1, le=500)] = 100


class FieldPoint(Request):
    vdx: FiniteFloat = 0
    vdy: FiniteFloat = 0
    vcx: FiniteFloat = 0
    vcy: FiniteFloat = 0
    van: FiniteFloat = 0
    x: FiniteFloat
    y: FiniteFloat
    weight: Weight = 1


class Wavelength(Request):
    wavelength_um: Positive
    weight: Weight = 1


class PolarizationPatch(Request):
    unpolarized: bool | None = None
    jx: Annotated[FiniteFloat, Field(ge=0)] | None = None
    jy: Annotated[FiniteFloat, Field(ge=0)] | None = None
    x_phase: FiniteFloat | None = None
    y_phase: FiniteFloat | None = None
    method: Literal["XAxisMethod", "YAxisMethod", "ZAxisMethod"] | None = None
    convert_thin_film_phase: bool | None = None


class RayAimingPatch(Request):
    mode: Literal["Off", "Paraxial", "Real"] | None = None
    method: Literal["Heuristic", "Optimize"] | None = None
    cache: bool | None = None
    robust: bool | None = None
    scale_pupil_shift_by_field: bool | None = None
    auto_pupil_shift: bool | None = None
    enhanced: bool | None = None
    advanced_convergence: bool | None = None
    fallback_search: bool | None = None
    pupil_shift_x: FiniteFloat | None = None
    pupil_shift_y: FiniteFloat | None = None
    pupil_shift_z: FiniteFloat | None = None
    pupil_compress_x: Annotated[FiniteFloat, Field(ge=0)] | None = None
    pupil_compress_y: Annotated[FiniteFloat, Field(ge=0)] | None = None
    cache_steps: Annotated[int, Field(strict=True, ge=1, le=10000)] | None = None


class FilesPatch(Request):
    coating_file: str | None = None
    scatter_profile: str | None = None
    abg_file: str | None = None
    gradium_profile: str | None = None


class FieldUpdate(Request):
    number: PositiveIndex
    vdx: FiniteFloat | None = None
    vdy: FiniteFloat | None = None
    vcx: FiniteFloat | None = None
    vcy: FiniteFloat | None = None
    van: FiniteFloat | None = None


class AperturePatch(Request):
    width_of_arms: Positive | None = None
    number_of_arms: Annotated[int, Field(strict=True, ge=1)] | None = None
    aperture_file: str | None = None
    uda_scale: Positive | None = None
    type: Literal["None", "CircularAperture", "CircularObscuration", "RectangularAperture", "RectangularObscuration", "EllipticalAperture", "EllipticalObscuration", "Spider", "UserAperture", "UserObscuration", "FloatingAperture"] | None = None
    pickup_from: Index | None = None
    minimum_radius: Annotated[FiniteFloat, Field(ge=0)] = 0
    maximum_radius: Positive | None = None
    x_half_width: Positive | None = None
    y_half_width: Positive | None = None
    x_decenter: FiniteFloat = 0
    y_decenter: FiniteFloat = 0
    replace_pickup: bool = False

    @model_validator(mode="after")
    def check(self):
        if (self.type is None) == (self.pickup_from is None):
            raise ValueError("孔径指定 type 或 pickup_from 之一。")
        if self.type == "Spider" and (self.width_of_arms is None or self.number_of_arms is None):
            raise ValueError("Spider需要臂宽和臂数。")
        if self.type in {"UserAperture","UserObscuration"} and not self.aperture_file:
            raise ValueError("用户孔径需要aperture_file。")
        circular={'minimum_radius','maximum_radius','x_decenter','y_decenter'}
        rectangular={'x_half_width','y_half_width','x_decenter','y_decenter'}
        specific={'minimum_radius','maximum_radius','x_half_width','y_half_width','x_decenter','y_decenter','width_of_arms','number_of_arms','aperture_file','uda_scale'}
        allowed = {'Spider':{'width_of_arms','number_of_arms','x_decenter','y_decenter'},
                   'UserAperture':{'aperture_file','uda_scale','x_decenter','y_decenter'},
                   'UserObscuration':{'aperture_file','uda_scale','x_decenter','y_decenter'}}.get(self.type,set())
        if self.type and self.type.startswith('Circular'):allowed=circular
        if self.type and self.type.startswith(('Rectangular','Elliptical')):allowed=rectangular
        if (self.model_fields_set & specific) - allowed:
            raise ValueError('孔径类型不支持此参数。')
        if self.type and self.type.startswith("Circular") and (self.maximum_radius is None or self.minimum_radius >= self.maximum_radius):
            raise ValueError("圆形孔径需要 maximum_radius > minimum_radius。")
        if self.type and self.type.startswith(("Rectangular", "Elliptical")) and (self.x_half_width is None or self.y_half_width is None):
            raise ValueError("需要两个正半宽。")
        return self


class TiltPatch(Request):
    before_order: Literal["Decenter_Tilt", "Tilt_Decenter"] | None = None
    after_order: Literal["Decenter_Tilt", "Tilt_Decenter"] | None = None
    before_decenter_x: FiniteFloat | None = None
    before_decenter_y: FiniteFloat | None = None
    before_tilt_x: FiniteFloat | None = None
    before_tilt_y: FiniteFloat | None = None
    before_tilt_z: FiniteFloat | None = None
    after_decenter_x: FiniteFloat | None = None
    after_decenter_y: FiniteFloat | None = None
    after_tilt_x: FiniteFloat | None = None
    after_tilt_y: FiniteFloat | None = None
    after_tilt_z: FiniteFloat | None = None
    replace_pickup: bool = False


from .scattering_pages import Scattering
from .property_pages import ApertureOptions, Advanced, Drawing, TypeProperties, Composite, PhysicalOptics


class SystemPatch(Request):
    author: str | None = None
    afocal_mode_units: str | None = None
    aperture_options: ApertureOptions | None = None
    advanced: Advanced | None = None
    global_reference_surface: PositiveIndex | None = None
    source_units: str | None = None
    source_unit_prefix: str | None = None
    analysis_units: str | None = None
    analysis_unit_prefix: str | None = None
    vignetting_action: Literal["calculate", "clear"] | None = None
    material_catalogs: Annotated[list[str], Field(max_length=100)] | None = None
    polarization: PolarizationPatch | None = None
    ray_aiming: RayAimingPatch | None = None
    files: FilesPatch | None = None
    field_normalization: Literal["Radial", "Rectangular"] | None = None
    field_updates: Annotated[list[FieldUpdate], Field(min_length=1, max_length=100)] | None = None
    title: str | None = None
    notes: str | None = None
    lens_units: Literal["Millimeters", "Centimeters", "Inches", "Meters"] | None = None
    mtf_units: Literal["CyclesPerMillimeter", "CyclesPerMilliradian"] | None = None
    aperture_type: str | None = None
    aperture_value: Positive | None = None
    field_type: str | None = None
    fields: Annotated[list[FieldPoint], Field(min_length=1, max_length=100)] | None = None
    wavelengths: Annotated[list[Wavelength], Field(min_length=1, max_length=100)] | None = None
    primary_wavelength: PositiveIndex | None = None
    temperature_c: FiniteFloat | None = None
    pressure_atm: Annotated[FiniteFloat, Field(ge=0)] | None = None
    adjust_index_to_environment: bool | None = None

    @model_validator(mode="after")
    def check(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一个设置。")
        if self.fields is not None and self.field_updates is not None:
            raise ValueError("fields 与 field_updates 互斥。")
        if self.vignetting_action is not None and (self.fields is not None or self.field_updates is not None):
            raise ValueError("自动渐晕操作与视场编辑分别调用。")
        if self.field_updates and len({x.number for x in self.field_updates}) != len(self.field_updates):
            raise ValueError("重复的视场编号。")
        for collection in (self.fields, self.wavelengths):
            if collection is not None and not any(x.weight > 0 for x in collection):
                raise ValueError("至少有一个正权重。")
        if self.primary_wavelength and self.wavelengths and self.primary_wavelength > len(self.wavelengths):
            raise ValueError("主波长编号超出新波长列表。")
        if any(getattr(self, k) is None for k in self.model_fields_set):
            raise ValueError("省略不修改的字段，不使用 null。")
        return self


CellName = Literal["radius", "thickness", "material", "semi_diameter", "conic", "tce", "mechanical_semi_diameter", "chip_zone"] | Annotated[str, Field(pattern=r"^parameter_([1-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-4])$")]


class SolveSpec(Request):
    mode: Literal["fixed", "variable", "surface_pickup", "f_number", "marginal_ray_height", "chief_ray_height", "edge_thickness", "position", "pickup_chief_ray"]
    height: FiniteFloat | None = None
    pupil_zone: Annotated[FiniteFloat, Field(ge=-1, le=1)] = 0
    radial_height: Annotated[FiniteFloat, Field(ge=0)] = 0
    thickness: FiniteFloat | None = None
    length: FiniteFloat | None = None
    field: PositiveIndex = 1
    wavelength: PositiveIndex = 1
    source_surface: Index | None = None
    source_column: str | None = None
    scale: FiniteFloat = 1
    offset: FiniteFloat = 0
    f_number: Positive | None = None

    @model_validator(mode="after")
    def check(self):
        required = {"marginal_ray_height": "height", "chief_ray_height": "height", "edge_thickness": "thickness", "position": "length"}
        if self.mode in required and getattr(self, required[self.mode]) is None:
            raise ValueError("缺少 solve 参数：" + required[self.mode])
        if self.mode == "position" and self.source_surface is None:
            raise ValueError("position 需要 source_surface。")
        if self.mode == "surface_pickup" and self.source_surface is None:
            raise ValueError("surface_pickup 需要 source_surface。")
        if self.mode == "f_number" and self.f_number is None:
            raise ValueError("f_number solve 需要正的 f_number。")
        return self


class AngleSolve(Request):
    mode: Literal["marginal_ray_angle", "chief_ray_angle"]
    angle: FiniteFloat = Field(description="原生近轴光线斜率，无量纲。")


class ParameterlessSolve(Request):
    mode: Literal["marginal_ray_normal", "chief_ray_normal", "aplanatic", "pupil_position", "automatic", "maximum"]


class ElementPowerSolve(Request):
    mode: Literal["element_power"]
    power: FiniteFloat = Field(description="镜头单位的倒数。")


class ReferenceSolve(Request):
    mode: Literal["concentric_surface", "concentric_radius", "center_of_curvature"]
    source_surface: Index


class CompensatorSolve(Request):
    mode: Literal["compensator"]
    source_surface: Index
    sum: FiniteFloat = Field(description="本面与参考面厚度之和，镜头单位。")


class OPDSolve(Request):
    mode: Literal["optical_path_difference"]
    opd: FiniteFloat = Field(description="主波长下的 waves，出口瞳参考。")
    pupil_zone: Annotated[FiniteFloat, Field(ge=-1, le=1)] = 1


class MaterialModelSolve(Request):
    mode: Literal["material_model"]
    index_nd: Positive
    abbe_vd: Positive
    dpgf: FiniteFloat = 0
    vary_index: bool = False
    vary_abbe: bool = False
    vary_dpgf: bool = False


class MaterialOffsetSolve(Request):
    mode: Literal["material_offset"]
    nd_offset: FiniteFloat = 0
    vd_offset: FiniteFloat = 0


class MaterialSubstituteSolve(Request):
    mode: Literal["material_substitute"]
    catalog: str = ""


class MacroSolve(Request):
    mode: Literal["zpl_macro"]
    macro: Annotated[str, Field(min_length=1,max_length=31,description='Native macro stem; at most 31 UTF-16 code units, without .ZPL extension.')]

    @model_validator(mode='after')
    def native_macro_name_length(self):
        if len(self.macro.encode('utf-16-le'))//2>31:
            raise ValueError('本机 ZPL solve 宏名称最多31个UTF-16代码单元，不含.ZPL扩展名。')
        return self


SurfaceSolve = Annotated[SolveSpec | AngleSolve | ParameterlessSolve | ElementPowerSolve |
    ReferenceSolve | CompensatorSolve | OPDSolve | MaterialModelSolve | MaterialOffsetSolve |
    MaterialSubstituteSolve | MacroSolve, Field(discriminator="mode")]


class SurfacePatch(Request):
    scattering: Scattering | None = None
    drawing: Drawing | None = None
    type_properties: TypeProperties | None = None
    composite: Composite | None = None
    physical_optics: PhysicalOptics | None = None
    disable_clear_semi_diameter_margins: bool | None = None
    surface_file: str | None = None
    import_file: str | None = None
    is_stop: Literal[True] | None = None
    coating: str | None = None
    aperture: AperturePatch | None = None
    tilt_decenter: TiltPatch | None = None
    surface: Index
    radius: FiniteFloat | Literal["Infinity", "-Infinity"] | None = None
    thickness: FiniteFloat | None = None
    material: str | None = None
    semi_diameter: Annotated[FiniteFloat, Field(ge=0)] | None = None
    mechanical_semi_diameter: Annotated[FiniteFloat, Field(ge=0)] | None = None
    chip_zone: Annotated[FiniteFloat, Field(ge=0)] | None = None
    conic: FiniteFloat | None = None
    tce: FiniteFloat | None = None
    comment: str | None = None
    surface_type: str | None = None
    parameters: dict[Annotated[int, Field(ge=1, le=254)], FiniteFloat] = Field(default_factory=dict)
    solves: dict[CellName, SurfaceSolve] = Field(default_factory=dict)
    replace_solves: bool = False

    @model_validator(mode="after")
    def check(self):
        if any(getattr(self, k) is None for k in self.model_fields_set):
            raise ValueError("省略不修改的字段，不使用 null。")
        if not (self.model_fields_set - {"surface", "replace_solves"}):
            raise ValueError("没有曲面修改内容。")
        return self


class UpdateSurfaces(Request):
    changes: Annotated[list[SurfacePatch], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def check(self):
        if sum(bool(x.is_stop) for x in self.changes)>1:
            raise ValueError("同一批只能指定一个光阑。")
        ids = [x.surface for x in self.changes]
        if len(set(ids)) != len(ids):
            raise ValueError("同一批修改不能重复指定曲面。")
        return self


class InsertSurfaces(Request):
    at: PositiveIndex
    count: Annotated[int, Field(strict=True, ge=1, le=100)] = 1


class DeleteSurfaces(InsertSurfaces):
    pass


class Variable(Request):
    surface: Index
    cell: CellName
    variable: bool = True
    replace_solve: bool = False

class ConfigurationVariable(Request):
    operand: PositiveIndex
    configuration: PositiveIndex
    variable: bool = True
    replace_solve: bool = False


class ObjectVariable(Request):
    object: PositiveIndex
    cell: str
    variable: bool = True
    replace_solve: bool = False


class SetVariables(Request):
    variables: Annotated[list[Variable|ConfigurationVariable|ObjectVariable], Field(min_length=1, max_length=200)]


class Operand(Request):
    type: str
    target: FiniteFloat = 0
    weight: Weight = 1
    parameters: dict[Annotated[int, Field(ge=2, le=9)], FiniteFloat] = Field(default_factory=dict)


class OperandUpdate(Request):
    operand: PositiveIndex
    type: str | None = None
    target: FiniteFloat | None = None
    weight: Weight | None = None
    parameters: dict[Annotated[int, Field(ge=2, le=9)], FiniteFloat] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check(self):
        if not (self.model_fields_set - {"operand"}):
            raise ValueError("没有操作数修改内容。")
        if any(getattr(self, k) is None for k in self.model_fields_set):
            raise ValueError("省略不修改字段，不使用 null。")
        return self


class MeritPatch(Request):
    mode: Literal["replace", "append", "update", "delete", "rms_spot_wizard"]
    operands: list[Operand] = Field(default_factory=list, max_length=1000)
    updates: list[OperandUpdate] = Field(default_factory=list, max_length=1000)
    operand_numbers: list[PositiveIndex] = Field(default_factory=list, max_length=1000)
    reference: Literal["Centroid", "ChiefRay"] = "Centroid"
    rings: Annotated[int, Field(strict=True, ge=1, le=10)] = 3

    @model_validator(mode="after")
    def check(self):
        if self.mode == "update":
            if not self.updates or self.operands or self.operand_numbers:
                raise ValueError("update 模式使用非空 updates。")
        elif self.mode == "delete":
            if not self.operand_numbers or self.operands or self.updates:
                raise ValueError("delete 模式使用非空 operand_numbers。")
        elif self.updates or self.operand_numbers:
            raise ValueError("当前模式使用 operands，不使用 updates/operand_numbers。")
        ids = [x.operand for x in self.updates] + self.operand_numbers
        if len(ids) != len(set(ids)):
            raise ValueError("操作数编号不可重复。")
        return self


class QuickFocus(Request):
    criterion: Literal["SpotSizeRadial", "SpotSizeXOnly", "SpotSizeYOnly", "RMSWavefront"]
    use_centroid: bool
    replace_solve: bool = False


class Analysis(Request):
    field: Index = 0
    wavelength: Index = 0


class FftMtf(Analysis):
    maximum_frequency: Positive = 50
    sampling: Literal["S_32x32", "S_64x64", "S_128x128", "S_256x256", "S_512x512", "S_1024x1024"] = "S_128x128"
    frequency_unit: Literal["CyclesPerMillimeter", "CyclesPerMilliradian"] = "CyclesPerMillimeter"
    use_polarization: bool = False


class Spot(Analysis):
    reference: Literal["ChiefRay", "Centroid", "Middle", "Vertex"]
    pattern: Literal["Square", "Hexapolar"] = "Hexapolar"
    ray_density: Annotated[int, Field(strict=True, ge=1, le=100)] = 6
    use_polarization: bool = False




class LocalOptimization(Request):
    algorithm: Literal["DampedLeastSquares", "OrthogonalDescent"] = "DampedLeastSquares"
    cycles: Literal["Automatic", "Fixed_1_Cycle", "Fixed_5_Cycles", "Fixed_10_Cycles", "Fixed_50_Cycles"] = "Fixed_5_Cycles"
    number_of_cores: Annotated[int, Field(strict=True, ge=1)] = 1


class TaskRequest(Request):
    task_id: str


class TaskResult(TaskRequest):
    series: Index | None = None
    start: Index = 0
    count: Annotated[int, Field(strict=True, ge=1, le=1000)] = 200
    grid: Index | None = None
    x_start: Index = 0
    y_start: Index = 0
    width: Annotated[int, Field(strict=True, ge=1, le=1000)] = 32
    height: Annotated[int, Field(strict=True, ge=1, le=1000)] = 32

    @model_validator(mode="after")
    def region_limit(self):
        if self.grid is not None and self.series is not None:
            raise ValueError("grid 与 series 分页不可同时指定。")
        if self.grid is not None and self.width*self.height>10000:
            raise ValueError("网格区域每次最多 10000 个值。")
        return self


class Ray(Request):
    hx: FiniteFloat = 0
    hy: FiniteFloat = 0
    px: FiniteFloat = 0
    py: FiniteFloat = 0
    wavelength: PositiveIndex = 1

class DirectRay(Request):
    x: FiniteFloat
    y: FiniteFloat
    z: FiniteFloat
    l: FiniteFloat
    m: FiniteFloat
    n: FiniteFloat
    wavelength: PositiveIndex = 1

    @model_validator(mode="after")
    def check_direction(self):
        import math
        if not math.isclose(self.l*self.l+self.m*self.m+self.n*self.n,1,rel_tol=1e-7,abs_tol=1e-8):raise ValueError("方向余弦须为单位向量。")
        return self

class RayPolarization(Request):
    jx: Annotated[FiniteFloat,Field(ge=0)] = 1
    jy: Annotated[FiniteFloat,Field(ge=0)] = 0
    x_phase: FiniteFloat = 0
    y_phase: FiniteFloat = 0

    @model_validator(mode="after")
    def check(self):
        if self.jx==self.jy==0:raise ValueError("偏振两个分量不得同时为零。")
        return self


class BatchRays(Request):
    rays: Annotated[list[Ray|DirectRay], Field(min_length=1, max_length=10000)]
    input_mode: Literal["Normalized","Direct"] = "Normalized"
    start_surface: Index = 1
    polarization: RayPolarization | None = None
    target_surface: Index | None = None
    ray_type: Literal["Real", "Paraxial"] = "Real"
    opd: bool = False

    @model_validator(mode="after")
    def check(self):
        if any(not isinstance(r,DirectRay if self.input_mode=="Direct"else Ray) for r in self.rays):raise ValueError("光线字段须与 input_mode 一致。")
        if self.polarization is not None and self.ray_type!="Real":raise ValueError("偏振追迹适配真实光线。")
        if self.opd and (self.input_mode=="Direct"or self.polarization is not None):raise ValueError("OPD 只适配归一化非偏振模式。")
        return self

from .analysis_models import RunAnalysis, AnalysisRequest

class CurveSample(Request):
    kind: Literal["curve"]
    analysis: Index
    series: Index
    label: str
    x: FiniteFloat
    unit: str

class GridStatistic(Request):
    kind: Literal["grid"]
    analysis: Index
    grid: Index = 0
    statistic: Literal["minimum","maximum","mean"]
    unit: str

EvaluationMetric = Annotated[CurveSample|GridStatistic,Field(discriminator="kind")]


class Evaluation(Request):
    analyses: Annotated[list[AnalysisRequest],Field(max_length=30)] = Field(default_factory=list)
    analysis_metrics: Annotated[list[EvaluationMetric],Field(max_length=200)] = Field(default_factory=list)
    spot: Spot | None = None
    mtf: FftMtf | None = None
    merit: bool = False
    frequencies: list[Positive] = Field(default_factory=list, max_length=100)
    focus: QuickFocus | None = None

    @model_validator(mode="after")
    def check(self):
        if not (self.spot or self.mtf or self.merit or self.analyses):
            raise ValueError("至少选择一项分析。")
        if self.frequencies and not self.mtf:
            raise ValueError("频率取值需要 MTF。")
        if any(m.analysis>=len(self.analyses) for m in self.analysis_metrics):
            raise ValueError("analysis_metrics 的 analysis 编号越界。")
        return self


class ParameterScan(Request):
    surface: Index
    cell: CellName
    values: Annotated[list[FiniteFloat], Field(min_length=1, max_length=200)]
    evaluation: Evaluation
    replace_solve: bool = False

    @model_validator(mode="after")
    def check(self):
        if self.cell == "material":
            raise ValueError("扫描仅支持数值参数。")
        if self.cell == "semi_diameter" and any(v < 0 for v in self.values):
            raise ValueError("半口径不能为负。")
        return self


class BatchEvaluation(Request):
    paths: Annotated[list[str], Field(min_length=1, max_length=100)]
    evaluation: Evaluation


class CompareResults(Request):
    left_task_id: str
    right_task_id: str


class EvaluationReport(Request):
    task_ids: Annotated[list[str], Field(max_length=100)] = Field(default_factory=list)
    detector_files: Annotated[list[str],Field(max_length=100)] = Field(default_factory=list)
    title: str = "Zemax 设计评估"
    include_charts: bool = False
    formats: Annotated[list[Literal["markdown","pdf"]],Field(min_length=1,max_length=2)] = Field(default_factory=lambda:["markdown"])
    background: bool = False

    @model_validator(mode="after")
    def sources(self):
        if not self.task_ids and not self.detector_files:raise ValueError("需要task_ids或detector_files。")
        return self


class SystemResources(Request):
    extension_role: Literal["surface","source","object","surface_scatter","bulk_scatter","physical_optics","gradient_index","birefringence","diffractive","user_analysis","user_operand","extension","library","zpl"] | None = None
    scattering_type: str = "ABg"
    kind: Literal["catalogs", "materials", "coatings", "coating_files", "scatter_profiles", "abg_files", "gradium_profiles", "test_plate_files", "surface_types", "surface_files", "surface_import_files", "aperture_files", "scattering_files", "solve_macros", "image_simulation_files", "geometric_image_files", "extension_files"]
    cell: CellName = "thickness"
    surface_type: str | None = None
    catalog: str | None = None
    surface: Index = 1
    query: str = ""
    start: Index = 0
    count: Annotated[int, Field(strict=True, ge=1, le=1000)] = 200

    @model_validator(mode="after")
    def check(self):
        if self.kind == "extension_files" and self.extension_role is None:
            raise ValueError("extension_files requires extension_role.")
        if self.kind != "extension_files" and self.extension_role is not None:
            raise ValueError("extension_role applies to extension_files.")
        if self.kind == "materials" and not self.catalog:
            raise ValueError("materials 查询需要 catalog。")
        return self


class CopySurfaces(Request):
    start: PositiveIndex
    count: Annotated[int, Field(strict=True, ge=1, le=100)] = 1
    at: PositiveIndex


class GeometryPoint(Request):
    x: FiniteFloat
    y: FiniteFloat


class EngineeringBoundary(Request):
    id: str
    kind: Literal['min_center_thickness','min_thickness','min_gap','max_mechanical_radius',
                  'min_edge_thickness','min_wall_thickness','min_vertex_radius','max_curvature',
                  'max_surface_slope','max_aspheric_departure','min_clear_aperture','min_installation_margin']
    surface: PositiveIndex | None = None
    object: PositiveIndex | None = None
    other_surface: PositiveIndex | None = Field(default=None,description="min_gap的第二曲面；同轴径向面返回有符号轴向间隔，非共轴或非径向面返回有限曲面片的三维非负距离。")
    other_object: PositiveIndex | None = Field(default=None,description="三维min_gap的第二个NSC实体对象编号；返回实体间非负最短距离。")
    value_mm: Annotated[FiniteFloat, Field(ge=0)] | None = None
    value: Annotated[FiniteFloat, Field(ge=0)] | None = None
    unit: Literal['mm','rad','1/mm'] = 'mm'
    configurations: list[PositiveIndex] = Field(default_factory=list,max_length=100)
    temperature_c: FiniteFloat | None = None
    material: str | None = None
    process: str | None = None
    region: dict[str,FiniteFloat] = Field(default_factory=dict,description="曲面min_gap使用各面局部XY毫米坐标的环形或完整矩形范围；对象min_gap使用完整x/y/z全局毫米裁剪盒。")
    faces: list[PositiveIndex] = Field(default_factory=list,max_length=2)
    source: str
    reason: str

    @model_validator(mode='after')
    def applicable(self):
        if (self.surface is None)==(self.object is None):
            raise ValueError('加工边界需要一个surface或object。')
        if self.object is not None and (self.other_surface is not None or (self.kind=='min_gap' and self.other_object is None)):
            raise ValueError('对象间隙使用object和other_object；曲面编号与对象编号分开指定。')
        rectangle={f'{a}_{end}_mm'for a in 'xy'for end in ['min','max']}
        if self.kind=='min_gap' and self.surface is not None and set(self.region)&rectangle:
            if set(self.region)!=rectangle or any(self.region[f'{a}_min_mm']>=self.region[f'{a}_max_mm']for a in 'xy'):
                raise ValueError('曲面矩形区域需要完整且递增的x/y_min_mm与max_mm边界。')
        if self.other_object is not None:
            if self.object is None or self.kind!='min_gap' or self.object==self.other_object:
                raise ValueError('三维间隙需要两个不同的object编号。')
            if self.region:
                keys={f'{a}_{end}_mm'for a in 'xyz'for end in ['min','max']}
                if set(self.region)!=keys or any(self.region[f'{a}_min_mm']>=self.region[f'{a}_max_mm']for a in 'xyz'):
                    raise ValueError('对象间隙区域需要完整且递增的x/y/z_min_mm与max_mm边界。')
        if (self.value is None)==(self.value_mm is None):
            raise ValueError('数值使用value与unit，或旧版value_mm。')
        expected='rad' if self.kind=='max_surface_slope' else '1/mm' if self.kind=='max_curvature' else 'mm'
        if self.unit!=expected or (self.value_mm is not None and expected!='mm'):
            raise ValueError('加工边界数值单位与类型不符。')
        if len(set(self.configurations))!=len(self.configurations):
            raise ValueError('加工边界组态不能重复。')
        if self.kind=='min_wall_thickness' and (len(self.faces)!=2 or len(set(self.faces))!=2):
            raise ValueError('壁厚需要两个不同的相对实体面编号。')
        return self

    @property
    def limit(self):
        return self.value_mm if self.value_mm is not None else self.value


class EntityRelation(Request):
    id: str
    kind: Literal['contact','cemented','nested','intentional_overlap']
    entities: Annotated[list[str],Field(min_length=2,max_length=2)]
    source: str
    reason: str
    configurations: list[PositiveIndex] = Field(default_factory=list,max_length=100)

    @model_validator(mode='after')
    def identities(self):
        if self.entities[0]==self.entities[1]:raise ValueError('关系需要两个不同实体。')
        return self


class MechanicalExterior(Request):
    id: str
    surface: PositiveIndex
    outer_radius_mm: Positive
    edge_type: Literal['cylindrical'] = 'cylindrical'
    source: str
    reason: str


class EngineeringPolicy(Request):
    version: Annotated[int, Field(strict=True,ge=1)]
    constraints: Annotated[list[EngineeringBoundary],Field(min_length=1,max_length=500)]
    relations: list[EntityRelation] = Field(default_factory=list,max_length=500)
    mechanical_exteriors: list[MechanicalExterior] = Field(default_factory=list,max_length=500)

    @model_validator(mode='after')
    def unique_exteriors(self):
        for values in (self.constraints,self.relations):
            if len({r.id for r in values})!=len(values):
                raise ValueError('工程约束或关系编号不能重复。')
        if len({r.id for r in self.mechanical_exteriors})!=len(self.mechanical_exteriors) or len({r.surface for r in self.mechanical_exteriors})!=len(self.mechanical_exteriors):
            raise ValueError('机械外形编号和透镜前表面不能重复。')
        return self


class SurfaceGeometry(Request):
    scope: Literal['surface', 'system'] = 'surface'
    surface: Index | None = None
    points: Annotated[list[GeometryPoint], Field(max_length=200)] = Field(default_factory=list)
    check: Literal['quick', 'full'] = 'full'
    configurations: Annotated[list[PositiveIndex], Field(max_length=100)] = Field(default_factory=list)
    configuration_scope: Literal['current','required'] = 'current'
    budget_seconds: Annotated[float, Field(gt=0, le=120)] = 120
    representation_tolerance_mm: Annotated[FiniteFloat, Field(ge=1e-9, le=1e-3, description="system/full有界径向实体的目标表示误差，单位mm；结果保留实际误差界和内核容差。") ] = 1e-6
    engineering_policy: EngineeringPolicy | None = None

    @model_validator(mode='after')
    def scope_fields(self):
        if self.scope == 'surface' and self.surface is None:
            raise ValueError('surface范围需要surface编号。')
        if self.scope == 'system' and (self.surface is not None or self.points):
            raise ValueError('system范围使用完整模型，不接受单面点查询。')
        if len(set(self.configurations)) != len(self.configurations):
            raise ValueError('组态编号不能重复。')
        return self


class ArchiveSave(SaveLens):
    compression: bool = True


class ArchiveLoad(OpenLens):
    output_directory: str


class ProjectPatch(Request):
    operation: Literal["convert", "disable"]
    directory: str | None = None

    @model_validator(mode="after")
    def check(self):
        if (self.operation == "convert") != (self.directory is not None):
            raise ValueError("convert 需要 directory；disable 不使用 directory。")
        return self


class Dependencies(Request):
    start: Index = 0
    count: Annotated[int, Field(strict=True, ge=1, le=1000)] = 200

class ConfigurationEvaluation(Request):
    configurations: Annotated[list[PositiveIndex],Field(min_length=1,max_length=100)]
    evaluation: Evaluation

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.configurations))!=len(self.configurations): raise ValueError("结构编号不能重复。")
        return self

from .pareto import ParetoSettings

class Multistart(Request):
    starts: Annotated[list[Annotated[list[SurfacePatch],Field(min_length=1,max_length=100)]],Field(min_length=1,max_length=100)]
    optimization: LocalOptimization = Field(default_factory=LocalOptimization)
    evaluation: Evaluation
    pareto: ParetoSettings | None = None


COMMAND_MODELS = {
    "copy_system": SaveLens, "create_archive": ArchiveSave, "load_archive": ArchiveLoad,
    "get_project_settings": Empty, "update_project_settings": ProjectPatch,
    "get_external_dependencies": Dependencies, "load_merit_function": OpenLens,
    "save_merit_function": SaveLens,
    "get_system_resources": SystemResources, "copy_surfaces": CopySurfaces, "get_surface_geometry": SurfaceGeometry,
    "connect": Connect, "get_status": Empty, "get_capabilities": Capabilities,
    "new_system": Empty, "open_lens": OpenLens, "save_lens_as": SaveLens,
    "disconnect": Empty, "get_system_summary": Empty, "get_system_settings": Empty,
    "update_system_settings": SystemPatch, "get_surfaces": GetSurfaces,
    "update_surfaces": UpdateSurfaces, "insert_surfaces": InsertSurfaces,
    "delete_surfaces": DeleteSurfaces, "get_variables": Empty, "set_variables": SetVariables,
    "get_merit_function": MeritRange, "update_merit_function": MeritPatch,
    "evaluate_merit_function": Empty, "run_quick_focus": QuickFocus,
    "run_fft_mtf": FftMtf, "run_spot_analysis": Spot,
    "run_local_optimization": LocalOptimization, "get_task_status": TaskRequest,
    "get_task_result": TaskResult, "cancel_task": TaskRequest,
    "run_batch_ray_trace": BatchRays, "run_parameter_scan": ParameterScan,
    "run_batch_evaluation": BatchEvaluation, "compare_results": CompareResults,
    "export_evaluation_report": EvaluationReport,
    "run_configuration_evaluation":ConfigurationEvaluation,"run_multistart_optimization":Multistart,
}

COMMAND_MODELS["run_analysis"] = RunAnalysis
from .macro_models import StandaloneMacro
COMMAND_MODELS["run_standalone_macro"] = StandaloneMacro
from .configuration_models import ConfigurationRange, ConfigurationSelect, ConfigurationPatch, GlobalOptimization
COMMAND_MODELS.update(get_configurations=ConfigurationRange,set_configuration=ConfigurationSelect,update_configurations=ConfigurationPatch,get_constraint_coverage=Empty,run_global_optimization=GlobalOptimization,run_hammer_optimization=GlobalOptimization)
from .tolerance_models import ToleranceRange,TolerancePatch,ToleranceWizard,ToleranceAnalysis,ToleranceSummary
COMMAND_MODELS.update(get_tolerances=ToleranceRange,update_tolerances=TolerancePatch,generate_tolerances=ToleranceWizard,run_tolerance_analysis=ToleranceAnalysis,summarize_tolerance_results=ToleranceSummary)
from .nsc_models import NewSystem,ObjectRange,ObjectInsert,ObjectCopy,ObjectUpdates,DetectorClear,DetectorRead,NscTrace,ZrdRead,ZrdReplay
COMMAND_MODELS.update(new_system=NewSystem,get_nsc_objects=ObjectRange,insert_nsc_objects=ObjectInsert,delete_nsc_objects=ObjectInsert,copy_nsc_objects=ObjectCopy,update_nsc_objects=ObjectUpdates,clear_detectors=DetectorClear,get_detector_data=DetectorRead,run_nsc_ray_trace=NscTrace,read_zrd=ZrdRead)
from .pop_models import Pop,BeamRead,PopConvergence
COMMAND_MODELS.update(run_pop=Pop,get_beam_file=BeamRead,run_pop_convergence=PopConvergence)
from .export_models import CadExport,LayoutExport
COMMAND_MODELS["run_cad_export"]=CadExport
COMMAND_MODELS["run_layout_export"]=LayoutExport
COMMAND_MODELS["run_zrd_replay"]=ZrdReplay
from .nsc_models import DetectorSave,DetectorLoad
from .export_models import AnalysisImage
COMMAND_MODELS.update(save_detector_data=DetectorSave,load_detector_data=DetectorLoad,export_analysis_image=AnalysisImage)

from .editor_models import EditorMetadata,EditorInsert,EditorCopy
COMMAND_MODELS.update(get_editor_metadata=EditorMetadata,insert_editor_rows=EditorInsert,copy_editor_rows=EditorCopy,
    load_tolerance_file=OpenLens,save_tolerance_file=SaveLens)

from .design_models import DesignTool, DesignToolOptions
COMMAND_MODELS.update(run_design_tool=DesignTool, get_design_tool_options=DesignToolOptions)

from .wizard_models import OptimizationWizard, WizardOptions
COMMAND_MODELS.update(run_optimization_wizard=OptimizationWizard, get_optimization_wizard_options=WizardOptions)

from .catalog_models import CatalogSearch, CatalogLens, LensCandidate

class CatalogEvaluation(Request):
    common_settings: SystemPatch | None = None
    candidates: Annotated[list[LensCandidate], Field(min_length=1, max_length=100)]
    evaluation: Evaluation
    save_candidates: bool = True

COMMAND_MODELS.update(get_lens_catalogs=Empty, run_lens_catalog_search=CatalogSearch, run_catalog_lens=CatalogLens, run_catalog_evaluation=CatalogEvaluation)

from .history_models import TaskHistory, HistoricalResult, RequestStatus
COMMAND_MODELS.update(list_task_history=TaskHistory, get_historical_result=HistoricalResult, get_request_status=RequestStatus)

from .coating_models import CoatingLayerRange,CoatingLayerUpdate,CoatingRta
COMMAND_MODELS.update(get_coating_layers=CoatingLayerRange,update_coating_layers=CoatingLayerUpdate)
COMMAND_MODELS['get_coating_rta'] = CoatingRta

from .material_models import MaterialProperties
COMMAND_MODELS["get_material_properties"]=MaterialProperties

from .conversion_models import NscConversion
COMMAND_MODELS["run_nsc_conversion"]=NscConversion

from .nsc_models import ObjectGeometry
COMMAND_MODELS['get_nsc_object_geometry']=ObjectGeometry

from .star_models import StarRead, RunStar
COMMAND_MODELS.update(get_star_data=StarRead, run_star_operation=RunStar)

from .hpc_models import HpcSettingsQuery
COMMAND_MODELS['get_hpc_settings'] = HpcSettingsQuery

from .speos_models import RunSpeosExport
COMMAND_MODELS['run_speos_export'] = RunSpeosExport

from .point_cloud import PointCloudExport
COMMAND_MODELS['export_point_cloud'] = PointCloudExport

from .capability_index import CapabilitySearch
COMMAND_MODELS['search_capabilities'] = CapabilitySearch

CandidateId = Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')]
Label = Annotated[str, Field(min_length=1, max_length=200)]


class CandidateExternalMetric(Request):
    key: Annotated[str, Field(min_length=1, max_length=100)]
    value: FiniteFloat
    unit: Annotated[str, Field(min_length=1, max_length=100)]
    source: Annotated[str, Field(min_length=1, max_length=500)]


class CandidateCreate(Request):
    action: Literal['create']
    label: Label
    evaluation: Evaluation
    external_metrics: list[CandidateExternalMetric] = Field(default_factory=list, max_length=100)


class CandidateList(Request):
    action: Literal['list']
    design_id: CandidateId | None = None


class CandidateBranch(Request):
    action: Literal['branch']
    design_id: CandidateId
    parent_candidate_id: CandidateId
    label: Label


class CandidateSelect(Request):
    action: Literal['select', 'restore']
    design_id: CandidateId
    candidate_id: CandidateId


class CandidateCheckpoint(Request):
    action: Literal['checkpoint']
    design_id: CandidateId
    candidate_id: CandidateId
    label: Label
    modification_summary: Annotated[str, Field(min_length=1, max_length=4000)]
    external_metrics: list[CandidateExternalMetric] = Field(default_factory=list, max_length=100)


class CandidateCompare(Request):
    action: Literal['compare']
    design_id: CandidateId
    left_candidate_id: CandidateId
    right_candidate_id: CandidateId


CandidateAction = Annotated[CandidateCreate | CandidateList | CandidateBranch | CandidateSelect |
                            CandidateCheckpoint | CandidateCompare, Field(discriminator='action')]


class ManageCandidates(Request):
    request: CandidateAction


class CandidateEvaluation(Request):
    design_id: CandidateId
    candidate_ids: Annotated[list[CandidateId], Field(min_length=1, max_length=100)]

COMMAND_MODELS.update(manage_candidates=ManageCandidates, run_candidate_evaluation=CandidateEvaluation)
COMMAND_MODELS['get_glass_slots'] = Empty

from .merit_program import MeritProgram
COMMAND_MODELS['run_merit_program'] = MeritProgram
