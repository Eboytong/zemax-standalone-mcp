# Diffraction Efficiency 2D repeat, 2026-11-08

- Item: `CO-01.DiffEfficiency2D`; OpticStudio 24.2.0 build 240529 PremiumEdition; supplied sequential `Transmission hologram.zos` sample, native Hologram1 surface.
- Ordinary checks: `.venv\\Scripts\\python.exe -m pytest tests/unit/test_diff_efficiency.py -q` passed 24 tests.
- Native check: `.venv\\Scripts\\python.exe -m pytest tests/native/test_diff_efficiency_live.py -q --run-zemax` passed 1 serial scenario in 18.39 s. It ran 2D, angular and chromatic native analyses after applying the documented emulsion enable/order, checked settings readback, 64×64 2D dimensions and units (degrees × micrometers), curve units and pagination, exported images, compared central wavelength/angle slices, and verified source surfaces/system settings remained unchanged. Each task reported close attempted; stdio disconnected normally.
- 2D reference: central angular row agrees with the angular analysis; central wavelength column agrees with the chromatic analysis. The Hologram1 S/P numerical reference and off-axis/cancellation evidence remain in `development/evidence/CO-01/acceptance059.json` and existing CO-01 records.
- Scope boundary: the installed user DLL's P result has a separately measured extra external ray-direction projection factor and fails its independent physical reference in 192 comparisons (maximum error 0.4438234531919145). The current rerun covers the native Hologram1 path and does not clear the DLL P projection blocker.
- Completion count: 0; retain `implemented` pending the CO-01 Kogelnik DLL P projection definition.
