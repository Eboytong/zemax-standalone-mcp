"""Typed requests for installed design tools, with native range discovery."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .schema import Request, Index, PositiveIndex, Positive

class ScaleFactor(Request):
    kind: Literal['scale_factor']
    factor: Positive
    first_component: Index | None = None
    last_component: Index | None = None

    @model_validator(mode='after')
    def bounds(self):
        if self.first_component is not None and self.last_component is not None and self.first_component > self.last_component:
            raise ValueError('first_component必须不大于last_component')
        return self

class ScaleUnits(Request):
    kind: Literal['scale_units']
    unit: Literal['Millimeters', 'Centimeters', 'Inches', 'Meters']

class QuickAdjust(Request):
    kind: Literal['quick_adjust']
    surface: PositiveIndex
    parameter: Literal['Radius', 'Thickness'] = 'Thickness'
    criterion: Literal['SpotSizeRadial', 'SpotSizeXOnly', 'SpotSizeYOnly', 'AngularRadial', 'AngularXOnly', 'AngularYOnly'] = 'SpotSizeRadial'
    evaluate_surface: PositiveIndex | None = None
    replace_solve: bool = False

class FindBestAsphere(Request):
    kind: Literal['find_best_asphere']
    first_surface: PositiveIndex
    last_surface: PositiveIndex
    asphere_type: Literal['Conic', 'Polynomial_4thOrder', 'Polynomial_6thOrder', 'Polynomial_8thOrder', 'Polynomial_10thOrder', 'Polynomial_12thOrder'] = 'Conic'

    @model_validator(mode='after')
    def bounds(self):
        if self.first_surface > self.last_surface:
            raise ValueError('first_surface必须不大于last_surface')
        return self

class ConvertAsphere(Request):
    kind: Literal['convert_asphere']
    surface: PositiveIndex
    asphere_type: Literal['EvenAsphere', 'ExtendedAsphere', 'QTypeAsphereType0', 'QTypeAsphereType1']
    number_of_terms: Annotated[int, Field(strict=True, ge=1, le=1000)] | None = None
    exclude_second_order_term: bool = False
    allow_radius_variation: bool = False
    allow_conic_variation: bool = False

class RayAimingWizard(Request):
    kind: Literal['ray_aiming_wizard']
    apply: bool = False

DesignRequest = Annotated[ScaleFactor | ScaleUnits | QuickAdjust | FindBestAsphere | ConvertAsphere | RayAimingWizard, Field(discriminator='kind')]

class DesignTool(Request):
    request: DesignRequest

class DesignToolOptions(Request):
    kind: Literal['scale_factor', 'scale_units', 'quick_adjust', 'find_best_asphere', 'convert_asphere', 'ray_aiming_wizard']
