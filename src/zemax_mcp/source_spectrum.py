"""Mode-specific NCE source-color contracts from the installed ISCS interfaces."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .schema import Request

Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Positive = Annotated[float, Field(strict=True, gt=0, allow_inf_nan=False)]


class Sampling(Request):
    SpectrumCount: Annotated[int, Field(strict=True, ge=1)] | None = None
    WavelengthFrom: Positive | None = None
    WavelengthTo: Positive | None = None

    @model_validator(mode='after')
    def ordered(self):
        if self.WavelengthFrom is not None and self.WavelengthTo is not None:
            if self.WavelengthFrom >= self.WavelengthTo:
                raise ValueError('WavelengthFrom必须小于WavelengthTo。')
        return self


class Tristimulus(Sampling):
    X: Finite | None = None
    Y: Finite | None = None
    Z: Finite | None = None


class Chromaticity(Sampling):
    cx: Finite | None = None
    cy: Finite | None = None


class RGB(Sampling):
    R: Finite | None = None
    G: Finite | None = None
    B: Finite | None = None


class Temperature(Sampling):
    TemperatureK: Positive | None = None


class CIE1976Settings(Sampling):
    u: Finite | None = None
    v: Finite | None = None


class FileSettings(Request):
    SpectrumFile: Annotated[str, Field(strict=True, min_length=1)] | None = None


class SystemWavelengths(Request):
    mode: Literal['SystemWavelengths']
    settings: Request = Field(default_factory=Request)


class CIE1931Tristimulus(Request):
    mode: Literal['CIE1931Tristimulus']
    settings: Tristimulus = Field(default_factory=Tristimulus)


class CIE1931Chromaticity(Request):
    mode: Literal['CIE1931Chromaticity']
    settings: Chromaticity = Field(default_factory=Chromaticity)


class CIE1931RGB(Request):
    mode: Literal['CIE1931RGB']
    settings: RGB = Field(default_factory=RGB)


class UniformPowerSpectrum(Request):
    mode: Literal['UniformPowerSpectrum']
    settings: Sampling = Field(default_factory=Sampling)


class D65White(Request):
    mode: Literal['D65White']
    settings: Sampling = Field(default_factory=Sampling)


class ColorTemperature(Request):
    mode: Literal['ColorTemperature']
    settings: Temperature = Field(default_factory=Temperature)


class BlackBodySpectrum(Request):
    mode: Literal['BlackBodySpectrum']
    settings: Temperature = Field(default_factory=Temperature)


class SpectrumFile(Request):
    mode: Literal['SpectrumFile']
    settings: FileSettings = Field(default_factory=FileSettings)


class CIE1976(Request):
    mode: Literal['CIE1976']
    settings: CIE1976Settings = Field(default_factory=CIE1976Settings)


SourceSpectrum = Annotated[
    SystemWavelengths | CIE1931Tristimulus | CIE1931Chromaticity | CIE1931RGB |
    UniformPowerSpectrum | D65White | ColorTemperature | BlackBodySpectrum |
    SpectrumFile | CIE1976, Field(discriminator='mode')]

MODELS = {model.model_fields['mode'].annotation.__args__[0]: model for model in (
    SystemWavelengths, CIE1931Tristimulus, CIE1931Chromaticity, CIE1931RGB,
    UniformPowerSpectrum, D65White, ColorTemperature, BlackBodySpectrum, SpectrumFile, CIE1976)}


def requested_values(spectrum):
    return spectrum.settings.model_dump(exclude_none=True, exclude_unset=True)


def read_settings(sources):
    """Read only the selected ISCS contract; concrete classes expose alias slots."""
    mode = str(sources.SourceColor)
    model = MODELS.get(mode)
    if model is None:
        from .errors import ZemaxError
        raise ZemaxError('UNSUPPORTED_INTERFACE', '未确认当前光源颜色模式的正式设置。', mode=mode)
    obj = getattr(sources.SourceColorSettings, '_S_' + mode)
    fields = list(model.model_fields['settings'].annotation.model_fields)
    if mode == 'SpectrumFile':
        fields += ['SpectrumCount', 'WavelengthFrom', 'WavelengthTo']
    if mode != 'SystemWavelengths':
        fields.append('Fit')
    settings = {}
    for name in fields:
        try:
            settings[name] = getattr(obj, name)
        except Exception as exc:
            settings.setdefault('unavailable_fields', {})[name] = str(exc)
    return dict(mode=mode, settings=settings)
