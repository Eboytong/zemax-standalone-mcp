"""Typed operations against the installed sequential STAR interfaces."""
from typing import Annotated, Literal
from pydantic import Field, FiniteFloat, model_validator
from .schema import Request, PositiveIndex, Index

StarDataKind = Literal['deformation', 'temperature', 'direct_index']


class StarPoint(Request):
    x: FiniteFloat
    y: FiniteFloat
    z: FiniteFloat = 0


class StarRead(Request):
    surface: PositiveIndex
    data_kind: StarDataKind = 'deformation'
    include_points: bool = False
    start: Index = 0
    count: Annotated[int, Field(strict=True, ge=1, le=1000)] = 100
    sample_points: Annotated[list[StarPoint], Field(max_length=1000)] = Field(default_factory=list)
    remove_rigid_body: bool = False

    @model_validator(mode='after')
    def applicable_samples(self):
        if self.remove_rigid_body and self.data_kind != 'deformation':
            raise ValueError('Rigid-body removal applies to deformation samples.')
        if self.data_kind == 'deformation' and any(point.z != 0 for point in self.sample_points):
            raise ValueError('Deformation fit samples use native X/Y coordinates only.')
        return self


class StarImport(Request):
    kind: Literal['import_deformation', 'import_temperature', 'import_direct_index']
    surface: PositiveIndex
    path: Annotated[str, Field(min_length=1)]
    coordinate_system: Literal['local', 'global']
    length_unit: Literal['Millimeters', 'Centimeters', 'Inches', 'Meters']


class StarUnload(Request):
    kind: Literal['unload_deformation', 'unload_temperature', 'unload_direct_index']
    surface: PositiveIndex


class StarFitSettings(Request):
    grid_1: Annotated[int, Field(strict=True, ge=1)] | None = None
    grid_2: Annotated[int, Field(strict=True, ge=1)] | None = None
    grid_3: Annotated[int, Field(strict=True, ge=1)] | None = None
    mba_max_level: Annotated[int, Field(strict=True, ge=1)] | None = None
    mba_tolerance: Annotated[FiniteFloat, Field(ge=0)] | None = None
    mba_min_fill: Annotated[FiniteFloat, Field(ge=0, le=1)] | None = None

    @model_validator(mode='after')
    def nonempty(self):
        if not any(value is not None for value in self.model_dump().values()):
            raise ValueError('Fit settings require at least one non-null value.')
        return self


class StarFit(Request):
    kind: Literal['fit_deformation', 'fit_temperature', 'fit_direct_index']
    surface: PositiveIndex
    settings: StarFitSettings | None = None
    apply: Literal['keep', 'enable', 'disable'] = 'keep'
    deformation_option: Literal['DeformationWithRBMs', 'DeformationWithoutRBMs', 'OnlyRBMs', 'NoDeformation'] | None = None

    @model_validator(mode='after')
    def applicable(self):
        if self.deformation_option is not None and self.kind != 'fit_deformation':
            raise ValueError('deformation_option applies to deformation fits.')
        if self.deformation_option == 'NoDeformation' and self.apply == 'enable':
            raise ValueError('NoDeformation conflicts with apply=enable.')
        if self.deformation_option not in {None, 'NoDeformation'} and self.apply == 'disable':
            raise ValueError('Disabling deformations conflicts with an active deformation option.')
        return self


class StarRigidBody(Request):
    kind: Literal['rigid_body']
    surface: PositiveIndex
    enabled: bool | None = None
    reference_point: StarPoint | None = None

    @model_validator(mode='after')
    def nonempty(self):
        if self.enabled is None and self.reference_point is None:
            raise ValueError('Provide enabled or reference_point.')
        return self


class StarCoordinateTransform(Request):
    kind: Literal['coordinate_transform']
    surface: PositiveIndex
    data_kind: StarDataKind = 'deformation'
    enabled: bool | None = None
    offset: StarPoint | None = None
    rotation_matrix: Annotated[list[FiniteFloat], Field(min_length=9, max_length=9)] | None = None
    reset: bool = False

    @model_validator(mode='after')
    def valid_transform(self):
        if self.enabled is None and self.offset is None and self.rotation_matrix is None and not self.reset:
            raise ValueError('Provide a transform change.')
        if self.reset and (self.offset is not None or self.rotation_matrix is not None):
            raise ValueError('Reset and explicit transform values are separate operations.')
        if self.rotation_matrix is not None:
            m = self.rotation_matrix
            for i in range(3):
                for j in range(3):
                    if abs(sum(m[3*i+k]*m[3*j+k] for k in range(3)) - (1 if i == j else 0)) > 1e-6:
                        raise ValueError('Rotation matrix rows must be orthonormal.')
            determinant = m[0]*(m[4]*m[8]-m[5]*m[7])-m[1]*(m[3]*m[8]-m[5]*m[6])+m[2]*(m[3]*m[7]-m[4]*m[6])
            if abs(determinant-1)>1e-6:
                raise ValueError('Rotation matrix determinant must be +1.')
        return self


class StarDefineComponent(Request):
    kind: Literal['define_component']
    first_surface: PositiveIndex
    last_surface: PositiveIndex
    adjust_index_data_with_rbm: bool | None = None

    @model_validator(mode='after')
    def ordered(self):
        if self.first_surface > self.last_surface:
            raise ValueError('Component surface range must increase.')
        return self


class StarRemoveComponent(Request):
    kind: Literal['remove_component']
    first_surface: PositiveIndex


class StarComponentRbm(Request):
    kind: Literal['component_rbm']
    surface: PositiveIndex
    action: Literal['configure', 'remove_from_fea', 'add_coordinate_breaks']
    adjust_index_data_with_rbm: bool | None = None

    @model_validator(mode='after')
    def nonempty(self):
        if self.action == 'configure' and self.adjust_index_data_with_rbm is None:
            raise ValueError('Configure requires adjust_index_data_with_rbm.')
        return self


class StarThermalControls(Request):
    kind: Literal['thermal_controls']
    surface: PositiveIndex
    fit_type: Annotated[int, Field(strict=True, ge=0)] | None = None
    working_wavelength: PositiveIndex | None = None

    @model_validator(mode='after')
    def nonempty(self):
        if self.fit_type is None and self.working_wavelength is None:
            raise ValueError('Provide fit_type or working_wavelength.')
        return self


class StarVolumeControls(Request):
    kind: Literal['volume_controls']
    surface: PositiveIndex
    data_kind: Literal['temperature','direct_index']
    grin_step: Annotated[FiniteFloat,Field(gt=0)] | None = None
    fit_grin_step: Annotated[FiniteFloat,Field(gt=0)] | None = None

    @model_validator(mode='after')
    def nonempty(self):
        if self.grin_step is None and self.fit_grin_step is None:
            raise ValueError('Provide a GRIN step setting.')
        return self


class StarUpdateMode(Request):
    kind: Literal['update_mode']
    mode: Literal['Normal','Suspended'] | None = None
    manual_update: bool = False

    @model_validator(mode='after')
    def nonempty(self):
        if self.mode is None and not self.manual_update:
            raise ValueError('Provide mode or manual_update=true.')
        return self


StarOperation = Annotated[StarImport | StarFit | StarUnload | StarRigidBody | StarCoordinateTransform |
    StarDefineComponent | StarRemoveComponent | StarComponentRbm | StarThermalControls |
    StarVolumeControls | StarUpdateMode, Field(discriminator='kind')]


class RunStar(Request):
    request: StarOperation
