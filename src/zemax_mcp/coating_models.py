"""Coating analysis requests and local layer edits."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .schema import Request, PositiveIndex, Index, FiniteFloat, Positive

CoatingMetric=Literal['reflection','transmission','absorption','diattenuation','phase','retardance']
class CoatingTarget(Request):
    nsc_object: PositiveIndex | None = Field(default=None,description='NSC object number, one-based; requires nsc_face. Pure NSC uses surface=0; mixed mode uses its component surface.')
    nsc_face: Index | None = Field(default=None,description='Native zero-based optical face-group number, discovered from get_nsc_objects; requires nsc_object.')
    @model_validator(mode='after')
    def paired_target(self):
        if self.surface==0 and self.nsc_object is None:raise ValueError('surface=0需要显式NSC对象和面。')
        if (self.nsc_object is None)!=(self.nsc_face is None):raise ValueError('nsc_object与nsc_face需要同时提供。')
        return self

class CoatingAngle(CoatingTarget):
    kind: Literal['reflection_vs_angle','transmission_vs_angle','absorption_vs_angle','diattenuation_vs_angle','phase_vs_angle','retardance_vs_angle']
    surface: Index = Field(description="Sequential surface number; pure NSC uses 0 with explicit nsc_object and nsc_face.")
    wavelength: PositiveIndex = Field(default=1,description='System wavelength number, one-based; mapped to the installed coating selector zero-based index.')
    minimum_angle: Annotated[FiniteFloat,Field(ge=0,le=90)] = 0
    maximum_angle: Annotated[FiniteFloat,Field(ge=0,le=90)] = 89
    reverse_direction: bool = Field(default=False,description='Native reverse media option for pure NSC or NonSequential component surfaces; ordinary sequential surfaces reject true.')
    minimum_y: FiniteFloat | None = None
    maximum_y: FiniteFloat | None = None
    @model_validator(mode='after')
    def bounds(self):
        if self.minimum_angle>=self.maximum_angle:raise ValueError('minimum_angle必须小于maximum_angle。')
        check_y(self)
        return self

class CoatingWavelength(CoatingTarget):
    kind: Literal['reflection_vs_wavelength','transmission_vs_wavelength','absorption_vs_wavelength','diattenuation_vs_wavelength','phase_vs_wavelength','retardance_vs_wavelength']
    surface: Index = Field(description="Sequential surface number; pure NSC uses 0 with explicit nsc_object and nsc_face.")
    angle: Annotated[FiniteFloat,Field(ge=0,le=90)] = 0
    minimum_wavelength_um: Positive = .4
    maximum_wavelength_um: Positive = .7
    reverse_direction: bool = Field(default=False,description='Native reverse media option for pure NSC or NonSequential component surfaces; ordinary sequential surfaces reject true.')
    minimum_y: FiniteFloat | None = None
    maximum_y: FiniteFloat | None = None
    @model_validator(mode='after')
    def bounds(self):
        if self.minimum_wavelength_um>=self.maximum_wavelength_um:raise ValueError('波长下限必须小于上限。')
        check_y(self)
        return self

def check_y(q):
    if (q.minimum_y is None)!=(q.maximum_y is None):raise ValueError('纵轴范围须同时提供上下限。')
    if q.minimum_y is not None and q.minimum_y>=q.maximum_y:raise ValueError('纵轴下限必须小于上限。')

class CoatingListing(Request):
    kind: Literal['coating_listing']

class CoatingLayerRange(Request):
    surface: PositiveIndex
    start: PositiveIndex = 1
    count: Annotated[int,Field(strict=True,ge=1,le=1000)] = 100

class CoatingFixed(Request):
    mode: Literal['Fixed','Variable']
class CoatingPickup(Request):
    mode: Literal['Pickup']
    layer: PositiveIndex
CoatingSolve=Annotated[CoatingFixed|CoatingPickup,Field(discriminator='mode')]

class CoatingLayerPatch(Request):
    layer: PositiveIndex
    thickness_multiplier: Annotated[FiniteFloat,Field(ge=0)] | None = None
    index_offset: FiniteFloat | None = None
    extinction_offset: FiniteFloat | None = None
    thickness_status: CoatingSolve | None = None
    index_status: CoatingSolve | None = None
    extinction_status: CoatingSolve | None = None
    @model_validator(mode='after')
    def nonempty(self):
        if not any(getattr(self,k)is not None for k in type(self).model_fields if k!='layer'):raise ValueError('每层至少提供一个修改。')
        for value_key, status_key in [('thickness_multiplier','thickness_status'),('index_offset','index_status'),('extinction_offset','extinction_status')]:
            mode=getattr(self,status_key)
            if getattr(self,value_key) is not None and mode is not None and mode.mode=='Pickup':raise ValueError('拾取状态与同一属性的显式数值不能同时指定。')
        for k in ['thickness_status','index_status','extinction_status']:
            q=getattr(self,k)
            if q and q.mode=='Pickup' and q.layer==self.layer:raise ValueError('镀膜层不能拾取自身。')
        return self

class CoatingLayerUpdate(Request):
    surface: PositiveIndex
    use_layer_multiplier_and_offsets: bool | None = None
    layers: Annotated[list[CoatingLayerPatch],Field(max_length=1000)] = Field(default_factory=list)
    @model_validator(mode='after')
    def nonempty(self):
        if not self.layers and self.use_layer_multiplier_and_offsets is None:raise ValueError('至少提供启用标志或层修改。')
        if len({q.layer for q in self.layers})!=len(self.layers):raise ValueError('镀膜层编号不能重复。')
        return self
