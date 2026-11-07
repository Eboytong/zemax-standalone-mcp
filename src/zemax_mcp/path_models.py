"""Native NSC path-analysis settings; database files are explicit local inputs."""
from pathlib import Path
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .schema import Request,FiniteFloat,PositiveIndex,Index,Positive

class PathAnalysis(Request):
    kind: Literal['path_analysis']
    path: Annotated[str,Field(min_length=1,max_length=32767)]
    first_ray: PositiveIndex = 1
    last_ray: Annotated[int,Field(strict=True,ge=-1)] = -1
    filter: Annotated[str,Field(max_length=4096)] = ''
    generate_path_filters: bool = False
    relative_minimum_flux: Annotated[FiniteFloat,Field(ge=0,le=1)] = 0
    sort_by: Literal['TotalEndingFlux','NumberOfObjectsStruck','NumberOfBranches','LastObjectStruck','NumberOfUniqueObjectsStruck','AverageOpticalPathLength','NumberOfDiffractionEvents'] = 'TotalEndingFlux'
    @model_validator(mode='after')
    def conditions(self):
        if self.last_ray!=-1 and self.last_ray<self.first_ray:raise ValueError('last_ray须为-1（全部剩余光线）或不小于first_ray。')
        if Path(self.path).suffix.lower()=='.paf' and self.filter:raise ValueError('PAF筛选须在追迹时设置，路径分析不接受追加filter。')
        return self


class CriticalRayTrace(Request):
    kind: Literal['critical_ray_trace']
    path: Annotated[str,Field(min_length=1,max_length=32767)]
    position_tolerance: Positive = .01
    angle_tolerance_deg: Annotated[Positive,Field(le=180)] = .01
    rays_to_display: Literal['AllRays','FailedRays','PassedRays'] = 'AllRays'
    display_xyz: bool = True
    display_lmn: bool = True
    display_actual_end_data: bool = True
    display_target_end_data: bool = True
    display_start_data: bool = True

class NscSingleRayTrace(Request):
    kind: Literal['nsc_single_ray_trace']
    wavelength: PositiveIndex = 1
    x: FiniteFloat = 0
    y: FiniteFloat = 0
    z: FiniteFloat = 0
    l: FiniteFloat = 0
    m: FiniteFloat = 0
    n: FiniteFloat = 1
    reference_object: Index = 0
    split_rays: bool = False
    scatter_rays: bool = False
    use_polarization: bool = False
    show_xyz: bool = True
    show_lmn: bool = True
    show_path: bool = True
    show_normal: bool = True
    show_electric_field: bool = True
    expand_into_branches: bool = False
    decimal_precision: Annotated[int,Field(strict=True,ge=0,le=15)] = 6
    max_segments: Annotated[int,Field(strict=True,ge=1,le=100000)] = 100000
    @model_validator(mode='after')
    def conditions(self):
        if abs(self.l*self.l+self.m*self.m+self.n*self.n-1)>1e-10:raise ValueError('l/m/n须为单位方向余弦。')
        if self.split_rays and not self.use_polarization:raise ValueError('原生分裂追迹需要use_polarization=true。')
        return self


class NscGeometricMtf(Request):
    kind: Literal['nsc_geometric_mtf']
    detector: PositiveIndex
    path: Annotated[str,Field(min_length=1,max_length=32767)] | None = None
    filter: Annotated[str,Field(max_length=4096)] = ''
    maximum_frequency: Annotated[FiniteFloat,Field(ge=0)] = 0
    frequencies: Annotated[list[Annotated[FiniteFloat,Field(ge=0)]],Field(min_length=1,max_length=301)] | None = None
    minimum_plot_scale: FiniteFloat = 0
    maximum_plot_scale: FiniteFloat = 1
    @model_validator(mode='after')
    def conditions(self):
        if self.filter and self.path is None:raise ValueError('filter需要显式ZRD输入。')
        if self.minimum_plot_scale>=self.maximum_plot_scale:raise ValueError('MTF显示范围须递增。')
        if self.frequencies is not None:
            if self.maximum_frequency!=0:raise ValueError('frequencies与非零maximum_frequency分别选择逐点查询和原生显示曲线，须单独使用。')
            if any(right<=left for left,right in zip(self.frequencies,self.frequencies[1:])):
                raise ValueError('frequencies须严格递增。')
        return self
