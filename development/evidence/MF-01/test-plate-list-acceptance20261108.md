# TestPlateList Acceptance

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14.

The existing typed `test_plate_list` request supports the active native catalog and explicit TPD file parsing. Native `AS_Default` does not expose catalog selection; the implementation reports the active catalog identity and handles a requested mismatch by documented TPD fallback under `auto`, or returns `SETTING_NOT_SUPPORTED` under forced `native`.

Checks run:

- `.venv\Scripts\python.exe -m pytest tests/unit/test_test_plates.py -q`: 26 passed.
- `.venv\Scripts\python.exe -m pytest tests/native/test_test_plates_live.py -q --run-zemax`: 2 passed in 30.17 s.

The native tests compared every catalog row against the independent TPD parser (native dimensions are rounded to four decimals; tolerance `0.0000500001 mm`), checked paginated rows, active catalog identity, mismatch fallback, forced-native rejection, missing/corrupt resources, cancellation, task reuse, save/reload, system/model preservation and normal close. The second test used an owned TPD resource and removed it in `finally`.

Conclusion: the supported native-active-catalog and explicitly selected TPD workflows are accepted. The missing native selector remains a documented interface limitation; it is surfaced as a specific method behavior rather than silently claiming the requested catalog was applied.

Source evidence: `tests/native/test_test_plates_live.py`, `tests/unit/test_test_plates.py`, `development/evidence/MF-01/progress435-plates.json`, and `development/evidence/MF-01/native435-plates-final.xml`.
