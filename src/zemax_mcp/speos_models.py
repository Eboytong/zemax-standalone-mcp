"""Typed settings for the installed Speos export tools."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .schema import Request, Positive, Index

NativeCount = Annotated[int,Field(strict=True,ge=1,le=2147483647)]


class SpeosLensSystem(Request):
    kind: Literal['lens_system']
    path: str
    overwrite: bool = False
    sensor_width: Positive
    sensor_height: Positive
    configuration: Index = 0
    skip_system_reversal: bool = False
    assume_radial_symmetry: bool = False
    sample_points: NativeCount | None = None
    x_sampling: NativeCount | None = None
    y_sampling: NativeCount | None = None
    sampling: Literal['S_32x32','S_64x64','S_128x128','S_256x256','S_512x512','S_1024x1024',
                      'S_2048x2048','S_4096x4096','S_8192x8192','S_16384x16384'] = 'S_64x64'

    @model_validator(mode='after')
    def applicable_sampling(self):
        if self.assume_radial_symmetry and (self.x_sampling is not None or self.y_sampling is not None):
            raise ValueError('Radial symmetry uses sample_points.')
        if not self.assume_radial_symmetry and self.sample_points is not None:
            raise ValueError('Cartesian sampling uses x_sampling/y_sampling.')
        return self


class SpeosWhitebox(Request):
    kind: Literal['whitebox']
    output_directory: str


SpeosExport = Annotated[SpeosLensSystem | SpeosWhitebox,Field(discriminator='kind')]


class RunSpeosExport(Request):
    request: SpeosExport
