from typing import Annotated,Literal
from pydantic import Field,FiniteFloat,model_validator
from .schema import Request,Index,PositiveIndex
from .source_spectrum import SourceSpectrum

class NewSystem(Request):
    mode: Literal["Sequential","NonSequential"] = "Sequential"

class ObjectRequest(Request):
    nsc_surface: PositiveIndex | None = None

class ObjectRange(ObjectRequest):
    start: PositiveIndex = 1
    count: Annotated[int,Field(strict=True,ge=1,le=200)] = 50
    parameter_start: Annotated[int,Field(strict=True,ge=1,le=250)] = 1
    parameter_count: Annotated[int,Field(strict=True,ge=1,le=250)] = 20

class ObjectInsert(ObjectRequest):
    at: PositiveIndex
    count: Annotated[int,Field(strict=True,ge=1,le=100)] = 1

class ObjectCopy(ObjectRequest):
    start: PositiveIndex
    count: Annotated[int,Field(strict=True,ge=1,le=100)] = 1
    at: PositiveIndex

ScalarValue=bool|FiniteFloat|str

class ObjectFace(Request):
    face: Index
    coating: str | None = None
    scatter_model: str | None = None
    settings: dict[str,ScalarValue] = Field(default_factory=dict,max_length=50)
    number_of_rays: Annotated[int,Field(strict=True,ge=1,le=10000)] | None = None

class ObjectVolume(Request):
    model: Literal["None","AngleScattering","DLLDefinedScattering","PhotoluminescenceModel"]
    settings: dict[str,ScalarValue] = Field(default_factory=dict,max_length=50)
    parameters: dict[Annotated[int,Field(ge=0,le=1000)],FiniteFloat] = Field(default_factory=dict,max_length=100)

    @model_validator(mode="after")
    def parameter_mode(self):
        if self.parameters and self.model!="DLLDefinedScattering":raise ValueError("parameters仅用于DLLDefinedScattering。")
        return self

class ObjectPatch(Request):
    faces: Annotated[list[ObjectFace],Field(max_length=100)] = Field(default_factory=list)
    volume: ObjectVolume | None = None
    spectrum: SourceSpectrum | None = None
    diffraction: dict[str,ScalarValue] = Field(default_factory=dict,max_length=30)
    object: PositiveIndex
    object_type: str | None = None
    file1: str | None = None
    file2: str | None = None
    x: FiniteFloat | None = None
    y: FiniteFloat | None = None
    z: FiniteFloat | None = None
    tilt_x: FiniteFloat | None = None
    tilt_y: FiniteFloat | None = None
    tilt_z: FiniteFloat | None = None
    ref_object: Index | None = None
    inside_of: Index | None = None
    material: str | None = None
    comment: str | None = None
    data: dict[str,bool|FiniteFloat|str] = Field(default_factory=dict,max_length=100)
    parameters: dict[Annotated[int,Field(ge=1,le=250)],FiniteFloat] = Field(default_factory=dict,max_length=250)
    sources: dict[str,bool|FiniteFloat|str] = Field(default_factory=dict,max_length=50)
    type_settings: dict[str,bool|FiniteFloat|str] = Field(default_factory=dict,max_length=50)
    replace_solves: bool = False

class ObjectUpdates(ObjectRequest):
    changes: Annotated[list[ObjectPatch],Field(min_length=1,max_length=100)]
    @model_validator(mode="after")
    def unique(self):
        if len({p.object for p in self.changes})!=len(self.changes):raise ValueError("对象编号重复。")
        return self

class DetectorClear(Request):
    detector: Index = 0

class DetectorRead(Request):
    read_mode: Literal['full','region'] = 'full'
    detector: PositiveIndex
    include_geometry: bool = False
    geometry_frame: Literal['local','global'] = 'local'
    kind: Literal["flux","irradiance","intensity","coherent","absorbed_flux","absorbed_density","spectral"] = "flux"
    coherent_type: str | None = None
    x_start: Index = 0
    y_start: Index = 0
    width: Annotated[int,Field(strict=True,ge=1,le=10000)] = 32
    height: Annotated[int,Field(strict=True,ge=1,le=10000)] = 32
    z_start: Index = 0
    depth: Annotated[int,Field(strict=True,ge=1,le=10000)] = 1
    color_channel: Literal["radiometric_flux","radiometric_density","photometric_flux","photometric_density","chromaticity_x","chromaticity_y","u_prime","v_prime","tristimulus_x","tristimulus_y","tristimulus_z"] | None = None
    angle_space: bool = False
    spectral_wavelengths_um: Annotated[list[Annotated[FiniteFloat,Field(gt=0)]],Field(max_length=200)] = Field(default_factory=list)
    start: Index = 0
    count: Annotated[int,Field(strict=True,ge=1,le=1000)] = 200

    @model_validator(mode="after")
    def region(self):
        limit=100000 if self.read_mode=='region' else 10000
        if self.read_mode=='full' and max(self.width,self.height,self.depth)>100:raise ValueError('full读取沿用各轴最多100个样本。')
        if self.width*self.height*self.depth>limit:raise ValueError(f'单次区域最多{limit}个样本。')
        if (self.kind=="spectral") != bool(self.spectral_wavelengths_um):raise ValueError("spectral需要显式的spectral_wavelengths_um；其他kind不接受该参数。")
        if self.kind=="spectral" and(self.color_channel is not None or self.angle_space or self.x_start or self.y_start or self.z_start or self.start or self.width!=32 or self.height!=32 or self.depth!=1 or self.count!=200):
            raise ValueError("spectral返回所选波长箱的空间统计，不接受颜色通道、角空间或区域分页。")
        return self


class DetectorSave(Request):
    detector: PositiveIndex
    path: str
    overwrite: bool = False

class DetectorLoad(Request):
    detector: PositiveIndex
    path: str
    mode: Literal["replace","accumulate"] = "replace"

from .hpc_models import HpcSelection

class NscTrace(Request):
    hpc: HpcSelection | None = None
    detector_policy: Literal["clear","accumulate"] = "clear"
    use_polarization: bool = False
    split_rays: bool = False
    scatter_rays: bool = False
    ignore_errors: bool = False
    number_of_cores: Annotated[int,Field(strict=True,ge=1,le=64)] = 1
    random_seed: Annotated[int,Field(strict=True,ge=0,le=2147483647)] | None = None
    save_zrd: str | None = None
    filter: str = ""

    @model_validator(mode="after")
    def check(self):
        if self.split_rays and not self.use_polarization:raise ValueError("分裂追迹需要 use_polarization=true。")
        return self

class ZrdRead(Request):
    path: str
    filter: str = ""
    start_ray: Index = 0
    start_segment: Index = 0
    max_segments: Annotated[int,Field(strict=True,ge=1,le=100000)] = 10000

class ZrdReplay(Request):
    path: str
    detector: PositiveIndex
    filter: str = ""
    data_type: Literal["IncoherentIrradiance","IncoherentFluence","CoherentIrradiance","CoherentPhase","IncidentFlux","AbsorbedFlux","RadiantIntensity"] = "IncoherentIrradiance"


class ObjectGeometry(ObjectRequest):
    object: PositiveIndex
    start: Index = 0
    count: Annotated[int,Field(strict=True,ge=1,le=1000)] = 100
    frame: Literal['local','global'] = 'local'
    include_radiometry: bool = False
