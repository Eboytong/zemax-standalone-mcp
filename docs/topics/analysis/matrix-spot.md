# Matrix Spot

`run_analysis` accepts `kind="matrix_spot"` and shares the checked `IAS_Spot` request with `configuration_matrix_spot`. It applies pattern, reference, scale display, ray color source, ray density, direction-cosine, symbol, polarization, scatter, Airy disk, and lateral-color settings, then runs the native MatrixSpot analysis through the standard result and close lifecycle.

```json
{
  "request": {
    "kind": "matrix_spot",
    "pattern": "Hexapolar",
    "reference": "Centroid",
    "show_scale": "ScaleBar",
    "color_rays_by": "Wavelength",
    "ray_density": 6
  }
}
```

The analysis ID and setting interface are confirmed by the installed 2024 R2 API reflection in `.local/evidence/development/BASE-01/probe/api-interfaces.json`. Matrix row/column meaning and native output data remain pending execution against a multi-field, multi-wavelength system.