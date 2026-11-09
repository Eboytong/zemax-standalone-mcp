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

The installed 2024 R2 API reflection confirms the analysis ID and settings. The native manual defines field rows and wavelength columns; controlled execution still returns no matrix output.
