"""Explicit local material identities and native internal-transmittance settings."""
from typing import Annotated, Literal
from pydantic import Field,model_validator
from .schema import Request,FiniteFloat,Positive,Index

class StarMaterialSample(Request):
    wavelength_um: Positive
    environment_pressure_atm: Annotated[FiniteFloat,Field(ge=0)] = 1
    environment_temperature_c: Annotated[FiniteFloat,Field(gt=-273.15)] = 20
    material_pressure_atm: Annotated[FiniteFloat,Field(ge=0)] = 1
    material_temperature_c: Annotated[FiniteFloat,Field(gt=-273.15)] = 20
    delta_temperature_c: Positive = .01


class MaterialProperties(Request):
    catalog: Annotated[str,Field(min_length=1,max_length=260)]
    material: Annotated[str,Field(min_length=1,max_length=260)]
    table_start: Index = 0
    table_count: Annotated[int,Field(strict=True,ge=1,le=1000)] = 200
    include_internal_transmission: bool = True
    include_birefringence: bool = True
    star_samples: Annotated[list[StarMaterialSample],Field(max_length=100)] = Field(default_factory=list)

class InternalTransmission(Request):
    kind: Literal['internal_transmission_vs_wavelength']
    catalog: Annotated[str,Field(min_length=1,max_length=260)]
    glasses: Annotated[list[Annotated[str,Field(min_length=1,max_length=260)]],Field(min_length=1,max_length=4)]
    minimum_wavelength_um: Annotated[FiniteFloat,Field(ge=0)] = .4
    maximum_wavelength_um: Annotated[FiniteFloat,Field(ge=0)] = .7
    minimum_transmission: Annotated[FiniteFloat,Field(ge=0,le=1)] = 0
    maximum_transmission: Annotated[FiniteFloat,Field(ge=0,le=1)] = 1
    thickness_mm: Positive = 10
    @model_validator(mode='after')
    def limits(self):
        a,b=self.minimum_wavelength_um,self.maximum_wavelength_um
        if (a,b)!=(0,0) and (a<=0 or b<=a):raise ValueError('波长范围须同时为0（自动）或正数递增。')
        if self.minimum_transmission>=self.maximum_transmission:raise ValueError('透过率显示下限必须小于上限。')
        if len(set(x.casefold()for x in self.glasses))!=len(self.glasses):raise ValueError('玻璃名称不能重复。')
        return self
