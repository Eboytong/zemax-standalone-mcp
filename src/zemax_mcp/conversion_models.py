"""Sequential group conversion uses the installed native conversion tool."""
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .schema import Request,PositiveIndex,Positive

class NscConversion(Request):
    first_surface: PositiveIndex = 1
    last_surface: PositiveIndex | None = None
    mode: Literal['group','pure'] = 'group'
    ignore_errors: bool = False
    create_sources_and_detectors: bool = False
    convert_to_global_coordinates: bool = False
    convert_stop_to_nsc_aperture: bool = True
    stop_mechanical_half_width: Positive | None = None
    overfill_factor: Positive | None = None
    @model_validator(mode='after')
    def conditions(self):
        if self.last_surface is not None and self.last_surface<self.first_surface:raise ValueError('转换曲面范围须递增。')
        if self.create_sources_and_detectors and self.mode!='pure':raise ValueError('自动光源与探测器生成适用于pure转换。')
        if self.overfill_factor is not None and not self.create_sources_and_detectors:raise ValueError('overfill_factor需要启用光源与探测器生成。')
        if self.stop_mechanical_half_width is not None and not self.convert_stop_to_nsc_aperture:raise ValueError('光阑机械半宽需要启用光阑孔径转换。')
        return self
