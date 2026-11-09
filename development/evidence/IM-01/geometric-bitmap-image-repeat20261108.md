# Geometric Bitmap Image repeat, 2026-11-08

- Item: `IM-01.GeometricBitmapImageAnalysis`; scope: native settings/file selection and result output on the installed runtime.
- Source: current worktree; Python 3.14 virtual environment; OpticStudio 24.2.0 build 240529, PremiumEdition; Cooke 40 degree field sample.
- Request: `run_analysis` with `kind=geometric_bitmap_image`, 10k rays, 33 pixels, 10 lens-unit image size, using the controlled `point.IMA`, `bars.IMA`, and `edge.IMA` inputs.
- Native outcome: all three requests return `UNSUPPORTED_INTERFACE`. Runtime settings type is `ZemaxUI.ZOSAPI.Analysis.AS_Default`; `GetFileNames` is absent. The response reports `partial_changes_possible=false`. No analysis result is created, so no bitmap/grid/text output is available for these requests.
- Lifecycle: for all three attempts, the MCP session wrote a successful shutdown checkpoint and the native application close returned `closed=true`; stdio client exited after the expected request rejection.
- Commands: `.venv\\Scripts\\python.exe -m pytest tests/native/test_imaging_live.py -q -k geometric_bitmap --run-zemax` (1 expected-interface test passed; 3 result-matrix cases confirmed unsupported); `.venv\\Scripts\\python.exe -m pytest tests/unit/test_imaging.py -q`.
- Test correction: imaging fixtures are stored at `tests/resources/imaging023`; the native test referenced `tests/native/resources`. The path now resolves from the `tests` directory. GBM was removed from the success-only resource/result matrix because the separate runtime-interface test asserts its supported behavior.
- Conclusion: the request model and adapter are present, while the installed native interface does not expose formal GBM input selection. The feature remains blocked pending a runtime with the dedicated settings interface or a documented formal selection/output route that can be verified against an independent image reference.
- Completion count: 0.
