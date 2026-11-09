# DIA_fill LDE discovery

- Item: `ED-02.DIA_fill.LDEDiscovery`; source declaration: LDE solve discovery and usable cell/settings path.
- Environment: source 0.1.61, OpticStudio 24.2.0 build 240529, Premium Edition, Sequential mode, configuration 1, Millimeters.
- Input: a new default sequential system; no user model or external resource.
- Command: `.venv\Scripts\python.exe scripts/probes/ED-02/lde_fill_solve_probe.py`.
- Native result: `SolveType.DIA_fill` exists with value 33. Reflected `ZOSAPI.Editors.ISolveData` exposes no `_S_DIA_fill` property or `ISolveDIA_fill` type. On the Standard surface, Radius, Thickness, Material, SemiDiameter, Conic, TCE, MechanicalSemiDiameter and ChipZone report `IsSolveTypeSupported(DIA_fill) == false`; `GetAvailableSolveTypes()` omits DIA_fill. `SemiDiameterCell.CreateSolveType(DIA_fill)` returns null.
- Scope evidence: the existing all-surface scan covers 81 surface types and found no active basic cell exposing a DIA_fill solve; see `development/evidence/ED-02/probe/probe.json` and `docs/topics/modeling/solve-extensions.md`.
- Execution/readback: no setting was applied because there is no formal settings object or supported cell. No model change occurred.
- Checks: `tests/unit/test_extended_solves.py` passed, 82 tests. The probe disconnected successfully and recorded `native_closed: true`; the MCP backend reported no running tasks.
- Conclusion: blocked by absent formal settings and cell support in the installed API. Reopen when a supported OpticStudio API exposes a DIA_fill settings interface and at least one eligible LDE cell, or a documented supported placement is identified.
- Next action: continue with the next unblocked entry in `development/remaining-ranked.md`.
