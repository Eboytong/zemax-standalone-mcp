# MarginPercent LDE discovery

- Item: `ED-02.MarginPercent.LDEDiscovery`; declared scope: determine whether a formal settings object and eligible LDE cell exist.
- Environment: source 0.1.61, OpticStudio 24.2.0 build 240529, Premium Edition, Sequential mode, configuration 1, Millimeters.
- Input: new default sequential system; no external resources.
- Command: `.venv\Scripts\python.exe scripts/probes/ED-02/lde_fill_solve_probe.py`.
- Native result: `SolveType.MarginPercent` is enum value 31. Reflected `ZOSAPI.Editors.ISolveData` has no `_S_MarginPercent` property or corresponding solve settings interface. Radius, Thickness, Material, SemiDiameter, Conic, TCE, MechanicalSemiDiameter and ChipZone on a Standard surface all report unsupported; `SemiDiameterCell.CreateSolveType(MarginPercent)` returns null.
- Scope evidence: the existing scan across 81 surface types found no active basic or parameter cell listing MarginPercent; see `development/evidence/ED-02/all-types/probe.json`.
- Execution/readback: no setting was applied and the model remained unchanged.
- Checks: `tests/unit/test_extended_solves.py` passed, 82 tests. Native disconnect succeeded and `native_closed: true`.
- Conclusion: blocked by absent formal settings and cell support in the installed API. Reopen when a supported settings interface and eligible LDE cell are exposed.
- Next action: inspect the independent MCE file interface.
