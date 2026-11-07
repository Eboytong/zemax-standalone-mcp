from typing import Annotated,Literal
from pydantic import Field,FiniteFloat,model_validator
from .schema import Request,Index,PositiveIndex,Positive
ParameterIndex=Annotated[int,Field(ge=0,le=1000)]
Sampling=Literal["S_32x32","S_64x64","S_128x128","S_256x256","S_512x512","S_1024x1024"]

class Pop(Request):
    start_surface: PositiveIndex = 1
    end_surface: PositiveIndex | None = None
    field: PositiveIndex = 1
    wavelength: PositiveIndex = 1
    beam_type: Literal["GaussianWaist","GaussianAngle","GaussianSizeAngle","TopHat","File","DLL","Multimode","AstigmaticGaussian"] = "GaussianWaist"
    beam_parameters: dict[ParameterIndex,FiniteFloat] = Field(default_factory=lambda:{0:1,1:1})
    beam_file: str | None = None
    x_sampling: Literal["S_32x32","S_64x64","S_128x128","S_256x256","S_512x512","S_1024x1024"] = "S_128x128"
    y_sampling: Literal["S_32x32","S_64x64","S_128x128","S_256x256","S_512x512","S_1024x1024"] = "S_128x128"
    x_width: Positive = 8
    y_width: Positive = 8
    surface_to_beam: FiniteFloat = 0
    total_power: Positive = 1
    use_polarization: bool = False
    separate_xy: bool = True
    data_type: Literal["Irradiance","Phase","EXIrradiance","EYIrradiance","EXPhase","EYPhase"] = "Irradiance"
    save_output_beam: bool = True
    save_all_surfaces: bool = False
    fiber_type: Literal["GaussianWaist","GaussianAngle","GaussianSizeAngle","TopHat","File","DLL","AstigmaticGaussian"] | None = None
    fiber_parameters: dict[ParameterIndex,FiniteFloat] = Field(default_factory=lambda:{0:1,1:1})
    fiber_file: str | None = None
    fiber_position: Literal["ChiefRay","SurfaceVertex"] = "ChiefRay"
    fiber_tilt_x: FiniteFloat = 0
    fiber_tilt_y: FiniteFloat = 0
    ignore_fiber_polarization: bool = False

    @model_validator(mode="after")
    def beam_outputs(self):
        if self.save_all_surfaces and not self.save_output_beam:
            raise ValueError("save_all_surfaces 需要 save_output_beam=true。")
        return self

class BeamRead(Request):
    include_coordinates: bool = False
    path: str
    start: Index = 0
    count: Annotated[int,Field(strict=True,ge=1,le=1000)] = 200

class PopConvergence(Request):
    settings: Pop
    samplings: Annotated[list[Sampling],Field(min_length=1,max_length=6)] | None = None
    sampling_pairs: Annotated[list[tuple[Sampling,Sampling]],Field(min_length=1,max_length=36)] | None = None
    widths: Annotated[list[tuple[Positive,Positive]],Field(min_length=1,max_length=10)]
    metric: Literal["integrated_power","peak_irradiance","receiver_efficiency","system_efficiency","total_coupling_efficiency"]
    relative_tolerance: Annotated[FiniteFloat,Field(ge=0)]
    absolute_tolerance: Annotated[FiniteFloat,Field(ge=0)]

    @model_validator(mode="after")
    def sampling_choice(self):
        if (self.samplings is None)==(self.sampling_pairs is None):
            raise ValueError("选择 samplings 或 sampling_pairs，二者互斥。")
        if len(self.samplings or self.sampling_pairs)*len(self.widths)<2:
            raise ValueError("收敛检查需要至少两个采样/窗口组合。")
        return self
