# EXT-HPC.Settings Native Check

- Date: 2026-11-08 (Asia/Shanghai)
- Source: current checkout, Python 3.14, OpticStudio 24.2.0 build 240529, PremiumEdition.
- Command: `\.venv\Scripts\python.exe -B -m pytest tests\native\test_hpc_live.py::test_hpc_native_configuration_query --run-zemax -q`
- Result: 1 passed. The test now accepts either a typed settings readback or the explicit native-unavailable response and checks its method attribution.
- Request: `get_hpc_settings({request: {mode: "preferences"}})`.
- Native result: `HPC_SETTINGS_UNAVAILABLE`; `GetHPCSettingsFromPrefs` returned null. Error details included `partial_changes_possible=false`. No configuration flag, node count, instance type, thread count, or shutdown-time values were available.
- Startup context: sequential mode, configuration 1, no source model, PremiumEdition. Startup completed through application creation and primary-system acquisition. The test client exited through stdio teardown after the request; no analysis task or SystemTool was opened by the query.
- Scope: native invocation and unavailable-result handling are verified. Reading adopted preference values and HPC job execution remain unverified on this machine.
- Unlock condition: configure an HPC preference that causes `GetHPCSettingsFromPrefs` to return a non-null `IHPCSettings`; rerun the same test, then run the relevant job test when the license/node service is available.
- Original first-run response: the same call failed its former success-only assertion with `HPC_SETTINGS_UNAVAILABLE`, native method `GetHPCSettingsFromPrefs`; captured at `.local/runs/runs/hpc_settings_a5fe9c5bd1/calls.json`.
