# Source Spectrum Viewer

Call `run_analysis` with `{"kind":"source_spectrum_viewer"}` in an NSC system. The request has no additional selectors because the installed analysis returns its current native source-spectrum report without a dedicated settings interface.

The result retains the native text artifact and provides paginated `rows` plus a curve in `series`. Each row contains `wavelength_um` and native `relative_weight`; the report also provides input/fitted XYZ, CRI, and CCT. Wavelength is in micrometers. Relative weight is dimensionless and follows the native report's peak-one normalization.

The OpticStudio 24.2.0 Colorimetry two-color mixing sample produced 20 points from 0.44 to 0.64 µm, CRI 70.1766, and CCT 5188 K. See [acceptance evidence](../../../development/evidence/NS-03/source-spectrum-acceptance20261108.md).

Input identity audit (2026-11-08): the report identifies XYZ tristimulus fitting input. It is identical for the two-color sample and a new empty NSC system. Results expose `input_definition` and `source_object_binding`; aggregate-source attribution is unverified. Formal input selection/readback remains pending. Corrupt rows and non-finite metadata now return errors. See `development/evidence/NS-03/source-spectrum-input-identity-20261108.md`.

## NCE source-color contracts

`update_nsc_objects` uses a typed `spectrum.mode/settings` union for all ten native color modes. Each mode accepts its own writable ISCS fields. For example, BlackBodySpectrum accepts TemperatureK plus SpectrumCount/WavelengthFrom/WavelengthTo; CIE1931Tristimulus accepts X/Y/Z and sampling. SpectrumFile accepts only SpectrumFile; its resolved sampling is returned by get_nsc_objects. SystemWavelengths accepts an empty settings object.

Wavelengths use micrometers and temperature uses kelvin. Omitted fields retain native values. Cross-mode aliases, read-only Fit/sampling writes, non-finite numbers and invalid requested wavelength ranges return parameter errors before mutation. Readback contains current-mode fields and Fit; read failures retain the field name and original exception.

Four native controls changed all NCE sources to 3000/6000 K and two XYZ inputs. NCE values and Fit changed; the separate viewer retained the same twenty-point XYZ=[1,1,1] spectrum. Formal viewer input selection remains open. See [controlled evidence](../../../development/evidence/NS-03/source-spectrum-binding-20261109.md) and [requests](../../../examples/requests/nsc-source-spectra.json).
