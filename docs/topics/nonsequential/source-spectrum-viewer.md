# Source Spectrum Viewer

Call `run_analysis` with `{"kind":"source_spectrum_viewer"}` in an NSC system. The request has no additional selectors because the installed analysis returns its current native source-spectrum report without a dedicated settings interface.

The result retains the native text artifact and provides paginated `rows` plus a curve in `series`. Each row contains `wavelength_um` and native `relative_weight`; the report also provides input/fitted XYZ, CRI, and CCT. Wavelength is in micrometers. Relative weight is dimensionless and follows the native report's peak-one normalization.



## NCE source-color contracts

`update_nsc_objects` uses a typed `spectrum.mode/settings` union for all ten native color modes. Each mode accepts its own writable ISCS fields. For example, BlackBodySpectrum accepts TemperatureK plus SpectrumCount/WavelengthFrom/WavelengthTo; CIE1931Tristimulus accepts X/Y/Z and sampling. SpectrumFile accepts only SpectrumFile; its resolved sampling is returned by get_nsc_objects. SystemWavelengths accepts an empty settings object.

Wavelengths use micrometers and temperature uses kelvin. Omitted fields retain native values. Cross-mode aliases, read-only Fit/sampling writes, non-finite numbers and invalid requested wavelength ranges return parameter errors before mutation. Readback contains current-mode fields and Fit; read failures retain the field name and original exception.
