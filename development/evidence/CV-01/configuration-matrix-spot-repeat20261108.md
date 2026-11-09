# ConfigurationMatrixSpot Native Repeat

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14, Cooke 40 degree field sample with two configurations.

Checks run:

- `.venv\Scripts\python.exe -m pytest tests/unit/test_configuration_matrix_spot.py -q`: 8 passed.
- `.venv\Scripts\python.exe -m pytest tests/native/test_configuration_matrix_spot_live.py -q --run-zemax`: 1 passed in 16.88 s.

The native test requested both `configuration_matrix_spot` (`color_rays_by=Config`) and `matrix_spot` (`color_rays_by=Waves`). Both native calculations completed with their expected explicit output limitation; task close was confirmed after each. The two-configuration model retained its system settings and surface state, and the session disconnected normally. Raw run: `.local/runs/runs/matrix088_outlets_b0aea1e36e/`; test conditions/output are also captured by `tests/native/test_configuration_matrix_spot_live.py` and `development/evidence/CV-01/probe088.json`.

Completion remains open because the native result outlet returns no usable SpotData/text arrays, and no equivalent complete matrix spot calculation has been established.
