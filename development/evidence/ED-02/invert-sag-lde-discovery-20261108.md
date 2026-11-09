# InvertSag LDE discovery

- Item: `ED-02.InvertSag.LDEDiscovery`; declared scope: determine whether the native solve can be placed on an LDE cell and identify a supported settings/execution path.
- Environment: source 0.1.61, OpticStudio 24.2.0 build 240529, Premium Edition, Sequential mode, configuration 1, Millimeters.
- Input: new default sequential system; no external resources.
- Command: `.venv\Scripts\python.exe scripts/probes/ED-02/lde_fill_solve_probe.py`.
- Native API: `SolveType.InvertSag` is enum value 35. `ISolveData` exposes `_S_InvertSag` as `ZOSAPI.Editors.ISolveInvertSag`; the interface has a `Surface` property.
- Cell discovery: the current native check found `IsSolveTypeSupported(InvertSag) == false` on all eight Standard basic cells (Radius, Thickness, Material, SemiDiameter, Conic, TCE, MechanicalSemiDiameter and ChipZone). `SemiDiameterCell.CreateSolveType(InvertSag)` returns null. The existing scan across 81 surface types found no active basic or parameter cell listing InvertSag; see `development/evidence/ED-02/all-types/probe.json`.
- Execution/readback: no solve was applied because no eligible cell was identified. Model revision remained at the new-system baseline; no model mutation occurred.
- Checks: `tests/unit/test_extended_solves.py` passed, 82 tests. Native disconnect succeeded and `native_closed: true`.
- Conclusion: blocked at cell placement. Reopen when an eligible LDE cell is exposed for InvertSag or a documented supported independent entry point and sample are available.
- Next action: continue with the next unblocked entry in `development/remaining-ranked.md`.
