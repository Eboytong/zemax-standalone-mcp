# CA_fill LDE discovery

- Item: `ED-02.CA_fill.LDEDiscovery`; source declaration: LDE solve discovery and usable cell/settings path.
- Environment: source 0.1.61, OpticStudio 24.2.0 build 240529, Premium Edition, Sequential mode, configuration 1, Millimeters.
- Input: a new default sequential system; no user model or external resource.
- Command: `.venv\Scripts\python.exe scripts/probes/ED-02/lde_fill_solve_probe.py`.
- Native result: `SolveType.CA_fill` exists with value 32. Reflected `ZOSAPI.Editors.ISolveData` exposes no `_S_CA_fill` property or `ISolveCA_fill` type. On the Standard surface, Radius, Thickness, Material, SemiDiameter, Conic, TCE, MechanicalSemiDiameter and ChipZone report `IsSolveTypeSupported(CA_fill) == false`; `GetAvailableSolveTypes()` omits CA_fill. `SemiDiameterCell.CreateSolveType(CA_fill)` returns null.
- Scope evidence: the existing all-surface scan covers 81 surface types and found no active basic cell exposing a CA_fill solve; see `development/evidence/ED-02/probe/probe.json` and the corresponding `docs/topics/modeling/solve-extensions.md` record.
- Execution/readback: no setting was applied because there is no formal settings object or supported cell. No model change occurred.
- Checks: `tests/unit/test_extended_solves.py` passed, 82 tests. The probe disconnected successfully and recorded `native_closed: true`; the MCP backend reported no running tasks.
- Conclusion: blocked by absent formal settings and cell support in the installed API. Reopen when a supported OpticStudio API exposes a CA_fill settings interface and at least one eligible LDE cell, or a documented supported placement is identified.
- Next action: perform the corresponding DIA_fill discovery.
