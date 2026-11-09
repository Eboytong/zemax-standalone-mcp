# Transmission Fan Adapter Acceptance

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14, Cooke 40 degree field sample. Added `run_analysis` kind `polarization_transmission_fan` with a kind-only typed request. It parses native TransmissionFan text into paginated pupil rows and `series` grouped by fan direction, field and wavelength. The report identifies dimensionless normalized intensity, unpolarized input, and the native wavelengths.

Targeted checks: 9 ordinary parser/request cases and 1 native stdio case passed. The stdio test verified 3 wavelengths, sagittal/tangential curves, field identity, endpoint pupil coordinates, center-field 0.55 µm native value, native text artifact, terminal result and disconnect. Native analysis close succeeded through the task path.

Raw original probe: `.local/evidence/development/NS-03/transmission-fan-20261108/summary.json`; adapter stdio evidence: `.local/runs/runs/polarization_transmission_fan_*/`.

This adapter covers the installed default unpolarized report. The native settings object exposes no selectors; independent transmission reference and selectable polarization/wavelength/field contract remain open.

## Repeat checks, 2026-11-08

Command: `.venv\Scripts\python.exe -m pytest tests/unit/test_yni_contributions.py -q` passed 9 tests. The default native invocation without `--run-zemax` was skipped by the fixture as designed; rerunning with `.venv\Scripts\python.exe -m pytest tests/native/test_transmission_fan_live.py -q --run-zemax` passed 1 test in 14.11 seconds. The test confirmed the native text adapter, three wavelengths, 18 sagittal/tangential field-wavelength series, pupil endpoints, center-field 0.55 µm value, artifact presence, and task/session completion.

The test log is the execution evidence for this repeat. Selector and independent-reference gaps remain unchanged.
