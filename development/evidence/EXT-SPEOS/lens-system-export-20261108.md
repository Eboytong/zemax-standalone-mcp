# Speos LensSystem Export Acceptance

- Environment: OpticStudio 24.2.0 build 240529 PremiumEdition, Python 3.14.
- Plan: verify the typed Cartesian request on the bundled Cooke lens, native setting readback, output, source preservation, and cleanup.
- Ordinary check: `pytest tests/unit/test_speos.py -q` — 29 passed.
- Native check: `pytest tests/native/test_speos_live.py::test_speos_owned_copy_native -m zemax --run-zemax -k cartesian -q -s` — 1 passed in 93.57 s.
- Request: `run_speos_export` with `kind=lens_system`, sensor 10 x 8 mm, configuration 0, Cartesian sampling `S_64x64`, output sampling 11 x 11, and reversal disabled.
- Actual settings: `Configuration=0`, `AssumeRadialSymmetry=false`, `SkipSystemReversal=false`, `SensorWidth=10`, `SensorHeight=8`, `SampleSize=S_64x64`, `XSampling=11`, `YSampling=11`, `FileFormatVersion=3`; all requested values were read back.
- Output: `.local/runs/runs/speos_cartesian_a54755af39/cartesian.OPTDistortion`, 54,523,861 bytes. Native execution state was `succeeded`.
- Source preservation: before/after system settings and surface data matched; source state identity, mode, configuration, lens units, and row count matched.
- Lifecycle: task succeeded; export tool and owned copy reported closed; stdio `disconnect` succeeded.
- Prior evidence covers radial LensSystem export as well as Whitebox export. A runnable Speos receiver was not found in the local v242 installation or uninstall inventory, so importing the output and checking receiver geometry/units remain blocked. Unlock by providing a runnable Speos receiver and importing this output.
- Run record: `.local/runs/runs/speos_cartesian_a54755af39/calls.json` and its task result JSON.
