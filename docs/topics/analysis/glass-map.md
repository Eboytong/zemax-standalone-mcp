# Glass Map

`run_analysis` accepts `{"kind":"glass_map"}` and reads the native Glass Map report for the currently loaded glass catalogs. The request has no catalog or range selectors because the OpticStudio 24.2.0 settings object exposes only `IsValid` and `IsActiveWindow`.

The parser returns a page-able `rows` table with each native glass name, refractive index `Nd`, Abbe number `Vd`, and source line. It also returns `scatter[0]` with Abbe number on X and refractive index on Y, both dimensionless. The native display convention places decreasing Abbe values from left to right; exported scatter images preserve that direction. Full point data remains in the saved result artifact while `get_task_result` pages the material rows.

On OpticStudio 24.2.0 Build 240529 Premium Edition, the current SCHOTT catalog report contained 346 glasses. The `N-BK7` point matched the installed `SCHOTT.AGF` values (`Nd=1.51680`, `Vd=64.17`) within the native report precision. Settings and resource selection limitations, output provenance and lifecycle evidence are tracked as `MA-01.GlassMap`.

Example:

```json
{"kind":"glass_map"}
```
