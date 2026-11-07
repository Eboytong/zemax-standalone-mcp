from typing import Annotated,Literal
from pydantic import Field,FiniteFloat,model_validator
from .schema import Request,Index,PositiveIndex

class CadExport(Request):
    path: str
    overwrite: bool = False
    format: Literal["STEP","IGES","SAT","STL","SAB","ASAT","ASAB","MODEL","CATPART","CATPRODUCT","XCGM","ZMO","XT","XB","PRC","JT","N3MF","U3D","OBJ","VRML","VisualizationJSON"] = "STEP"
    start: PositiveIndex = 1
    end: PositiveIndex | None = None
    surfaces_as_solids: bool = True
    export_dummy_surfaces: bool = False
    number_of_rays: Annotated[int,Field(strict=True,ge=0,le=1000)] = 0
    field: Index = 0
    wavelength: Index = 0
    tolerance: str = "N_TenEMinus4"
    ray_pattern: Literal["XYFan","XFan","YFan","Ring","List","Random","Grid","SolidRing"] | None = None
    delete_vignetted: bool | None = None
    ray_layer: Index | None = None
    lens_layer: Index | None = None
    dummy_thickness: Annotated[FiniteFloat,Field(ge=0)] | None = None
    spline_segments: Literal["N_016","N_032","N_064","N_128","N_256","N_512"] | None = None
    angular_tolerance: Literal["Low","Medium","High","Presentation"] | None = None
    scatter_nsc_rays: bool | None = None
    split_nsc_rays: bool | None = None
    use_polarization: bool | None = None
    auto_name_faces: bool | None = None
    file_version: Literal["Current","V25","V26","V27","V28","V29","V30"] | None = None
    configuration: PositiveIndex | None = None
    configuration_mode: Literal["current","single","all_by_layer","all_by_file","all_at_once"] | None = None

    @model_validator(mode="after")
    def conditions(self):
        mode=self.configuration_mode
        if mode=='single' and self.configuration is None:raise ValueError('single configuration_mode requires configuration.')
        if mode is not None and mode!='single' and self.configuration is not None:raise ValueError('configuration requires single mode or omitted configuration_mode.')
        options=(self.ray_pattern,self.delete_vignetted,self.ray_layer,self.lens_layer,self.dummy_thickness,
                 self.spline_segments,self.angular_tolerance,self.scatter_nsc_rays,self.split_nsc_rays,
                 self.use_polarization,self.auto_name_faces,self.file_version,self.configuration,self.configuration_mode)
        if self.format=="VisualizationJSON" and any(v is not None for v in options):
            raise ValueError("VisualizationJSON does not expose CAD export settings.")
        if self.file_version is not None and self.format not in {'SAT','SAB','ASAT','ASAB'}:
            raise ValueError('file_version requires an ACIS format (SAT/SAB/ASAT/ASAB).')
        if self.angular_tolerance is not None and self.format!="STL":
            raise ValueError("angular_tolerance requires STL format.")
        if self.dummy_thickness is not None and not (self.export_dummy_surfaces and self.surfaces_as_solids):
            raise ValueError("dummy_thickness requires export_dummy_surfaces and surfaces_as_solids.")
        if self.ray_pattern=="SolidRing" and self.number_of_rays<8:
            raise ValueError("SolidRing requires at least eight rays.")
        return self


class LayoutExport(Request):
    path: str
    overwrite: bool = False
    kind: Literal["cross_section","viewer_3d","shaded_model","nsc_3d","nsc_shaded"] = "cross_section"
    width: Annotated[int,Field(strict=True,ge=64,le=4096)] = 1200
    height: Annotated[int,Field(strict=True,ge=64,le=4096)] = 800
    start: Index = 1
    end: Index | None = None
    number_of_rays: Annotated[int,Field(strict=True,ge=0,le=1000)] = 5
    field: Index = 0
    wavelength: Index = 0
    viewpoint: Literal["Isometric","XY","YZ","XZ"] = "Isometric"

    @model_validator(mode="after")
    def applicable(self):
        if self.kind.startswith("nsc_")and(self.start!=1 or self.end is not None or self.number_of_rays!=5 or self.field or self.wavelength):
            raise ValueError("非序列布局使用对象的布局光线设置，不接受顺序范围和光线选项。")
        if self.kind=="cross_section"and self.viewpoint!="Isometric":raise ValueError("截面图不提供相机视角设置。")
        return self

class AnalysisImage(Request):
    task_id: str
    path: str
    source: Literal["data_plot","native"] = "data_plot"
    overwrite: bool = False
    item: Index = 0
    width: Annotated[int,Field(strict=True,ge=64,le=4096)] = 1200
    height: Annotated[int,Field(strict=True,ge=64,le=4096)] = 800
