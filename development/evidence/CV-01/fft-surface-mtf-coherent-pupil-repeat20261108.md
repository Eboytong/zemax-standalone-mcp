# FFT Surface MTF coherent-pupil repeat, 2026-11-08

- Item: `CV-01.FftSurfaceMtf`; OpticStudio 24.2.0 build 240529 PremiumEdition; Cooke 40 degree field sample; wavelength 2 (0.55 µm); fields 1 and 3; 256×256 sampling.
- Plan: compare the native noncoherent MTF with the autocorrelation of the native real and imaginary coherent-OTF grids, while preserving the independent phase/coordinate mapping as the unresolved reference.
- Ordinary checks: `.venv\\Scripts\\python.exe -m pytest tests/unit/test_fft_surface_mtf.py tests/unit/test_surface_mtf.py -q` passed 13 tests.
- Native check: `.venv\\Scripts\\python.exe -m pytest tests/native/test_surface_mtf_coherent_pupil_live.py -q --run-zemax` passed 1 scenario in 27.60 s. Each of the six native analyses succeeded and closed without cleanup warnings; source surfaces, system settings and merit function matched baseline, and stdio disconnected normally.
- Results: field 1 coherent support 50,617 points; autocorrelation maximum absolute difference `6.661338147750939e-16`, RMS `5.762582010181931e-17`. Field 3 support 41,361; maximum difference `0.00495019710934963`, RMS `0.000230877724138614`, below the fixed absolute gate `0.005`.
- Conclusion: native coherent OTF to noncoherent MTF consistency remains within tolerance. This cross-outlet check does not resolve the independent physical mapping from traced rays to the off-axis complex pupil; prior controlled mappings remain outside tolerance. Keep `implemented` until that mapping is established.
- Raw run: `.local/runs/runs/surface_mtf605_coherent_pupil_*/coherent-pupil.json`.
- Completion count: 0.
