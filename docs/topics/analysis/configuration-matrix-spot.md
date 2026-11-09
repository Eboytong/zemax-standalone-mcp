# Configuration Matrix Spot

`run_analysis` accepts `kind="configuration_matrix_spot"`. The typed request exposes the `IAS_Spot` controls confirmed by OpticStudio 2024 R2 reflection: pupil pattern, reference point, displayed scale, ray color source, ray density, direction-cosine output, symbols, polarization, scattering, Airy disk, and lateral-color handling. The adapter writes and reads each value through the checked native setting path. Results use the shared analysis task and native text/data collector.

```json
{
  "request": {
    "kind": "configuration_matrix_spot",
    "pattern": "Hexapolar",
    "reference": "Centroid",
    "show_scale": "ScaleBar",
    "color_rays_by": "Config",
    "ray_density": 6,
    "use_polarization": false
  }
}
```

The controlled live case adds a second configuration. The native manual defines field rows and configuration columns; settings adoption and empty native outlets are recorded by the factory comparison.
