# BSDF 资源选择器探查（2026-11-08）

- 条目：`ED-01.Scattering.BSDF`；源码及发行基线 `0.1.61`；OpticStudio `24.2.0 build 240529 PremiumEdition`。
- 本机资源：安装目录和用户 `Documents\Zemax\ScatterData` 中均有 `.bsdf` 文件，包括 `BrownVinyl.bsdf`。探针将此文件复制到自建项目的 `ScatterData` 子目录，未修改安装资源或用户原文件。
- 正式接口：反射类型为 `ZOSAPI.Editors.LDE.ISurfaceScatteringBSDF`；公开 `FileName`、`ScatterFraction`、`Angle`、`SampleSide`、`Sampling` 属性，其中 `FileName` 可写。项目内含 `BrownVinyl.bsdf` 时，原生 `GetAvailableFileNames()` 仍仅返回占位项 `无`（U+65E0）。
- 设置尝试：直接把 `BrownVinyl.bsdf` 文件名及项目内绝对路径写入 `FileName`，每次写前 getter 返回占位项；`ChangeScatteringTypeSettings()` 返回 true，但设置对象和活动设置的 `FileName` 仍为占位项，文件没有被采用。未把该结果用于追迹或保存重载，因为资源身份未确认。
- 原生探针：`.venv\Scripts\python.exe scripts/probes/ED-01/bsdf_selector_probe.py`；结果 `.local/runs/runs/bsdf_selector_20261108_050418/probe.json`；原生应用关闭成功。
- 普通检查：`.venv\Scripts\python.exe -m pytest tests/unit/test_property_pages_adoption.py -q`，19 passed。覆盖空/占位/ABGF错配被拒绝，以及明确 `.bsdf` 名称的过滤。
- MCP 检查：`.venv\Scripts\python.exe -m pytest tests/native/test_property_pages_live.py::test_property_pages_stdio -q -s --run-zemax`，1 passed。`get_system_resources(scattering_files, BSDF)` 返回 `UNSUPPORTED_SETTING`，`native_filenames=["无"]`、`valid_bsdf_names=[]`；stdio 断开和原生关闭通过。原始调用和关闭回执在 `.local/runs/runs/property_pages_e0195d2100`。
- 实现调整：BSDF 资源发现现在仅返回明确 `.bsdf` 项；原生列表无 `.bsdf`、含 ABGF 错配或空/占位时返回带原始文件列表的 `UNSUPPORTED_SETTING`，防止占位字符串成为可选资源。
- 结论：请求模型与不可用状态诊断完成；本机正式设置对象未能采用可用 BSDF 文件，几何追迹及保存重载无法验收，条目保持受阻。
- 解除条件：官方选择器对实际 `.bsdf` 文件返回可验证名称，并且 `FileName` 实际回读为所选资源；随后完成受控光线追迹、保存重载和资源关闭。
