"""Local stock lens catalog requests and baseline-controlled candidates."""
from typing import Annotated, Literal
from pydantic import Field, FiniteFloat, model_validator
from .schema import Request, Index, PositiveIndex

class CatalogRange(Request):
    minimum: FiniteFloat
    maximum: FiniteFloat
    @model_validator(mode='after')
    def bounds(self):
        if self.minimum>self.maximum:raise ValueError('minimum必须不大于maximum')
        return self

class CatalogFilter(Request):
    vendor: Annotated[str,Field(min_length=1)]
    efl_mm: CatalogRange | None = None
    epd_mm: CatalogRange | None = None
    number_of_elements: PositiveIndex | None = None
    equi: bool = True
    bi: bool = True
    plano: bool = True
    meniscus: bool = True
    spherical: bool = True
    grin: bool = True
    aspheric: bool = True
    toroidal: bool = True

class CatalogSearch(CatalogFilter):
    max_results: Annotated[int,Field(strict=True,ge=1,le=100000)] = 10000

class CatalogLens(Request):
    vendor: Annotated[str,Field(min_length=1)]
    lens_name: Annotated[str,Field(min_length=1)]
    action: Literal['load','insert'] = 'load'
    at_surface: PositiveIndex | None = None
    ignore_object: bool = True
    reverse_surface_geometry: bool = False
    @model_validator(mode='after')
    def destination(self):
        if self.action=='insert' and self.at_surface is None:raise ValueError('insert需要at_surface')
        if self.action=='load' and (self.at_surface is not None or 'ignore_object'in self.model_fields_set or 'reverse_surface_geometry'in self.model_fields_set):
            raise ValueError('load不使用插入位置或插入专属参数')
        return self

class MaterialReplacement(Request):
    surface: PositiveIndex
    material: Annotated[str,Field(min_length=1)]
    replace_solve: bool = False

class LensCandidate(Request):
    name: Annotated[str,Field(min_length=1)]
    lens: CatalogLens | None = None
    materials: Annotated[list[MaterialReplacement],Field(max_length=1000)] = Field(default_factory=list)
    @model_validator(mode='after')
    def changes(self):
        if self.lens is None and not self.materials:raise ValueError('候选需要目录镜头或材料替换')
        indices=[x.surface for x in self.materials]
        if len(indices)!=len(set(indices)):raise ValueError('同一候选不得重复替换同一曲面材料')
        return self
