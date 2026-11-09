# DuplicateSag LDE discovery

- Item: `ED-02.DuplicateSag.LDEDiscovery`; declared scope: determine whether the native solve can be placed on an LDE cell and identify a supported settings/execution path.
- Environment: source 0.1.61, OpticStudio 24.2.0 build 240529, Premium Edition, Sequential mode, configuration 1, Millimeters.
- Input: new default sequential system; no external resources.
- Command: `.venv\Scripts\python.exe scripts/probes/ED-02/lde_fill_solve_probe.py`.
- Native API: `SolveType.DuplicateSag` is enum value 34. `ISolveData` exposes `_S_DuplicateSag` as `ZOSAPI.Editors.ISolveDuplicateSag`; the interface has a `Surface` property. This establishes a settings interface exists.
- Cell discovery: the current native check found `IsSolveTypeSupported(DuplicateSag) == false` on all eight Standard basic cells (Radius, Thickness, Material, SemiDiameter, Conic, TCE, MechanicalSemiDiameter and ChipZone). `SemiDiameterCell.CreateSolveType(DuplicateSag)` returns null. The existing scan across 81 surface types found no active basic or parameter cell listing DuplicateSag; see `development/evidence/ED-02/all-types/probe.json`.
- Execution/readback: no solve was applied because no eligible cell was identified. Model revision remained at the new-system baseline; no model mutation occurred.
- Checks: `tests/unit/test_extended_solves.py` passed, 82 tests. Native disconnect succeeded and `native_closed: true`.
- Conclusion: blocked at cell placement. Reopen when an eligible LDE cell is exposed for DuplicateSag or a documented supported independent entry point and sample are available.
- Next action: perform the InvertSag cell discovery.
