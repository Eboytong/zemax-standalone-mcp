# Fiber Coupling Native and POP Cross-Checks

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14.

## Native topic probe

The Cooke 40 degree field sequential sample was opened as a working copy and `FiberCouplingSettings` executed. The valid native text report identified 0.550000 µm, angular field coordinates `(0,0)`, position units mm, angle units degrees, ignored source fiber, receiver NA X/Y `0.1`, zero receiver position/decenter/tilt, system efficiency `1.000000`, receiver efficiency `0.148061`, and total coupling efficiency `0.148061` (`-8.2956 dB`). The default settings object exposed only validity/activity; the report did not provide a formal writable selector contract. Analysis close and MCP disconnect succeeded.

Raw evidence: `.local/evidence/development/NS-03/fiber-coupling-viewer-20261108/summary.json`; text report: `photoluminescence.txt` beside it.

## POP receiver overlap reference

Command: `.venv\Scripts\python.exe -m pytest tests/native/test_pupil_coupling_live.py::test_tilted_gaussian_coupling_native -q --run-zemax` passed 1 test in 82.46 seconds. The controlled Gaussian overlap scenarios varied beam/receiver waist, X/Y tilt, grid sampling (`S_256x256`, `S_512x512`) and window width (2, 4 mm). The test read back receiver tilt, sampling, polarization, fiber position, and beam/fiber parameters. Receiver efficiency matched the independent scalar overlap formula within absolute tolerance `5e-4`; total coupling equaled system efficiency times receiver efficiency; X/Y tilt sign symmetry and separable two-axis behavior passed. The harness closed native resources and the session.

This verifies the existing POP receiver-coupling workflow. Completion of the dedicated `FiberCouplingSettings` analysis still requires a formal selector and full setting/result contract so typed input can be tied to the native output.
