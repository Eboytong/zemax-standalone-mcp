# Polarization Transmission Fan

Call `run_analysis` with `{"kind":"polarization_transmission_fan"}`. The response retains native text and returns paginated pupil rows plus `series` curves grouped by sagittal/tangential fan, field, and wavelength. X is normalized pupil coordinate; Y is dimensionless native normalized intensity. The report identifies the native input polarization, which may be unpolarized.

The OpticStudio 24.2.0 Cooke sample returns 3 fields, 3 wavelengths, and 18 curves from its native report. The installed `AS_Default` interface does not expose topic selectors. `method=native` accepts the default report request; supplying selectors with this method returns `UNSUPPORTED_SETTING`.

For selectable inputs use `method=ray_trace`, or supply a selector with `method=auto`. The adapter uses formal normalized polarized batch ray tracing. `field` and `wavelength` use one-based indices; 0 selects all. `sampling` is an odd pupil-point count from 3 to 1001, default 201. Sagittal scans pupil X and tangential scans pupil Y. System field normalization and vignetting factors are retained.

Omit `polarization` or set it to null for the mean of orthogonal unit X/Y input powers. A Jones input accepts nonnegative `jx`/`jy` amplitudes and `x_phase`/`y_phase` in degrees; amplitudes are normalized to unit incident intensity. Results include actual system selection and formal call arguments, computation source and child task identities. A separate geometric trace identifies clipping; invalid samples remain null with status and `invalid_count`.

```json
{"kind":"polarization_transmission_fan","field":2,"wavelength":2,"sampling":21,"polarization":{"jx":1,"jy":1,"y_phase":90}}
```

The native parser supports a variable wavelength-column count and preserves native invalid-ray markers. See [original evidence](../../../../development/evidence/PO-01/transmission-fan-acceptance20261108.md). Current numerical checks are recorded separately in the development evidence directory.
