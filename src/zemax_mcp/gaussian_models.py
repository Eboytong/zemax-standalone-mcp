"""Requests for native Gaussian merit-operand propagation."""
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .schema import Request,PositiveIndex,Positive,FiniteFloat


class ParaxialGaussianBeam(Request):
    kind: Literal['paraxial_gaussian_beam']
    wavelength: PositiveIndex = 1
    waist_radius: Positive = .05
    surface_1_to_waist: FiniteFloat = 0
    m2: Annotated[FiniteFloat,Field(ge=1)] = 1
    orientation: Literal['X','Y','Both'] = 'Both'
    surface_start: PositiveIndex = 1
    surface_end: PositiveIndex | None = None

    @model_validator(mode='after')
    def ordered(self):
        if self.surface_end is not None and self.surface_end<self.surface_start:
            raise ValueError('surface_end 必须不早于 surface_start。')
        return self


class SkewGaussianBeam(Request):
    kind: Literal['skew_gaussian_beam']
    wavelength: PositiveIndex = 1
    field: PositiveIndex = 1
    waist_radius_x: Positive = .05
    waist_radius_y: Positive = .05
    start_surface_to_waist: FiniteFloat = 0
    start_surface: PositiveIndex = 1
    end_surface: PositiveIndex | None = None
    orientation: Literal['X','Y','Both'] = 'Both'

    @model_validator(mode='after')
    def ordered(self):
        if self.end_surface is not None and self.end_surface<self.start_surface:
            raise ValueError('end_surface 必须不早于 start_surface。')
        return self
