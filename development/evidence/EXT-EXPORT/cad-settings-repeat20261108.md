# CAD 格式与版本复测（2026-11-08）

- 条目：`EXT-EXPORT.CadSettings`；源码及发行基线 `0.1.61`；OpticStudio `24.2.0 build 240529 PremiumEdition`。
- 普通测试：`.venv\Scripts\python.exe -m pytest tests/unit/test_cad_adoption.py -q`，63 passed。
- 格式矩阵：`.venv\Scripts\python.exe -m pytest tests/native/test_cad_formats_live.py::test_installed_cad_format_availability -q -s --run-zemax`，1 passed。Cooke 40 degree field 样例上依次尝试 `CAD_EXTENSIONS` 中的21种格式；15种输出成功：STEP、IGES、SAT、STL、SAB、OBJ、VRML、VisualizationJSON、ZMO、XT、XB、PRC、JT、N3MF、U3D；6种被拒绝：ASAT、ASAB、MODEL、CATPART、CATPRODUCT、XCGM。成功任务检查输出文件及适用的格式、Tolerance、配置和面范围回读；普通CAD任务检查关闭且无清理警告。拒绝项保留原生错误 `Unsupported export format`。测试完成后 stdio 正常断开、原生 owner 关闭。
- ACIS 版本：`.venv\Scripts\python.exe -m pytest tests/native/test_cad_acis_live.py::test_native_acis_version_refusal_and_reuse -q -s --run-zemax`，1 passed。SAT/SAB 的 V30 设置均被 getter 接受，但实际输出头 `version_code=500`（major 5）；适配器以 `SETTING_REJECTED` 返回请求和实际头信息，失败任务已关闭。SAT/SAB 的 Current 请求随后成功，文件头实际值为500。Cooke 曲面和系统设置保持。
- ASAT/ASAB 对照：沿用 2026-11-07 `native521-advanced-acis.xml` 与 `progress521-advanced-acis.json`：正式属性 getter 接受 `Current`，Run 均返回 `Unsupported export format`，无输出头可供版本判定；任务关闭和模型保持通过。
- 运行目录：格式矩阵 `.local/runs/runs/cad_formats_d8ff4e038a`；版本复用 `.local/runs/runs/cad185_acis_readback_684c427a31`。结果、请求、实际设置、原生错误和 close receipt 均保存在目录中。
- 结论：可用格式的当前设置回读、输出和资源关闭通过；SAT/SAB 的实际版本核验能阻止静默采用错误版本。CAD 格式/版本声明范围按本机能力矩阵保持实现待验收状态，ASAT/ASAB 及其他不支持格式不标记为可用。
- 解除条件：ASAT/ASAB 需本机正式导出器实际支持后才能验版本；SAT/SAB 显式版本需原生输出头采用请求版本或上游提供正式版本设置路径。其他格式以 `get_capabilities` 本机能力表为准。
