"""Typed current-configuration polarization pupil maps."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .schema import Request, PositiveIndex, FiniteFloat

class PolarizationPupilMap(Request):
    kind: Literal['polarization_pupil_map']
    surface: PositiveIndex
    field: PositiveIndex = 1
    wavelength: PositiveIndex = 1
    sampling: Annotated[int, Field(strict=True, ge=3, le=101)] = 5
    jx: Annotated[FiniteFloat, Field(ge=0)] = 1
    jy: Annotated[FiniteFloat, Field(ge=0)] = 0
    x_phase: FiniteFloat = 0
    y_phase: FiniteFloat = 0

    @model_validator(mode='after')
    def valid(self):
        if self.sampling % 2 != 1:
            raise ValueError('偏振瞳图 sampling 须为奇数，表示瞳直径上的方格采样点数。')
        if self.jx == self.jy == 0:
            raise ValueError('偏振两个分量不得同时为零。')
        return self
