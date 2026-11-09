# Independent MCE file interface discovery

- Item: `ED-03.MCE.independent_file`; scope: determine whether MCE supports independent file load/save apart from whole-system files.
- Environment: source 0.1.61, OpticStudio 24.2.0 build 240529, Premium Edition, Sequential mode.
- Input: new default sequential system; no external file.
- Command: `.venv\Scripts\python.exe scripts/probes/ED-03/mce_independent_file_probe.py`.
- Interface evidence: installed `ZOSAPI_Interfaces.dll` reflection of `IMultiConfigEditor` and inherited `IEditor` contains no public method with Load, Save or File in its name. Runtime MCE type is `ZemaxUI.ZOSAPI.Editors.ZOSAPI_MCE`; its public methods likewise have no matching file method. Runtime system retains `LoadFile(String, Boolean)` and `SaveAs(String)` for whole-system persistence.
- Existing supported behavior: MCE operations remain available through typed configuration tools; whole-system SaveAs/LoadFile preserves MCE content as exercised by `tests/native/test_configurations_live.py`.
- Checks: `.venv\Scripts\python.exe -m pytest tests/unit/test_universal_configuration.py tests/unit/test_configuration_cell_precision.py -q` passed, 23 tests. Read-only native probe completed, disconnected, and recorded `native_closed: true`.
- Conclusion: blocked for an independent MCE file artifact by missing formal interface. Whole-system persistence remains the supported path.
- Reopen condition: Ansys exposes an independent MCE load/save interface or documents a supported method with verifiable file semantics.
- Next action: inspect the formal standalone macro execution contract.
