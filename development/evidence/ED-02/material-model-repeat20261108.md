# MaterialModel Abbe Fit Repeat

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14.

Checks run:

- `.venv\Scripts\python.exe -m pytest tests/unit/test_extended_solves.py -q`: 82 passed.
- `.venv\Scripts\python.exe -m pytest 'tests/native/test_extended_solves_live.py::test_material_solves_numeric_stdio[model]' -q --run-zemax`: failed the existing Abbe numerical gate after 15.42 s.

The controlled sequential interface used an air-to-N-BK7 plane surface and direct rays at six wavelengths, including the standard d/F/C lines and nearby wavelengths. The typed solve requested `IndexNd=1.6`, `AbbeVd=60`, `dPgF=0.001`, with index and dPgF varying. The final native solve was read back and the model round-trip completed before the numerical assertion. Snell-derived Nd met its `1e-6` tolerance; derived Abbe was `59.99988524798844` against 60, failing the retained absolute tolerance `1e-5` plus relative tolerance `1e-7`.

Raw test run: `.local/runs/runs/material_model_numeric048_31fb33c773/` (contains conditions, calls, checks, and close receipt). The test harness shut down the native process and session.

Installed public interface reflection is retained in `development/evidence/ED-02/progress598-formal-fit-audit.json`: `ISolveMaterialModel` exposes Nd/Abbe/dPgF and variation flags, with no coefficient methods; catalog fit coefficient methods target selected catalog materials and expose no temporary `ModelGlass` selector. Completion requires an official temporary-material dispersion definition or supported coefficient read/write contract, followed by prediction and acceptance under the unchanged numerical gate.
