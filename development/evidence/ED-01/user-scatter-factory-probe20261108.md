# User 散射工厂复测（2026-11-08）

- 条目：`ED-01.Scattering.User`；源码及发行基线 `0.1.61`；OpticStudio `24.2.0 build 240529 PremiumEdition`。
- 本机DLL资源：`ZemaxData\DLL\SurfaceScatter`中存在 `Gaussian_XY.DLL`、`K-correlation.DLL`、`Lambertian.DLL`、`RI_BSDF.DLL`、`TwoGaussian.DLL`。资源文件存在，但不能据此确认原生请求入口采用。
- 原生探针：`.venv\Scripts\python.exe scripts/probes/ED-01/user_scatter_probe.py`。创建独立顺序系统后先成功应用 Lambertian（ScatterFraction=0.1），确认当前散射类型为 Lambertian；随后尝试User接口。
- 工厂调用：`ScatteringData.CreateScatteringTypeSettings(User)` 抛出 `.NET SerializationException`。原始错误指出 `ZemaxUI.Editors.UILDEScatterData` 类型未标记为可序列化；堆栈定位 `IZOSAPI_LDETools.GetParamData(rowIndex, dllName)`→`ZOSAPI_ScatteringTypeSettings.GetParamData()`→`CreateScatteringTypeSettings()`。
- 替代入口探查：活动设置容器的 `_S_User` 为 `None`，因此无法从其读取 `GetAvailableDLLNames()`、参数数量或参数名称；公共 `get_system_resources(scattering_files, User)` 同样触发工厂错误，并返回 `UNSUPPORTED_SETTING`，保留完整 `native_error` 与 `stage=CreateScatteringTypeSettings`。没有取得User参数或应用User设置。
- 普通测试：`.venv\Scripts\python.exe -m pytest tests/unit/test_property_pages_adoption.py -q`，19 passed，覆盖已知异常分类及其他原生异常保留。
- stdio原生回归：`.venv\Scripts\python.exe -m pytest tests/native/test_property_pages_live.py::test_property_pages_stdio -q -s --run-zemax`，1 passed；公开User资源查询的能力错误和会话结束覆盖在该用例中。原生关闭成功。
- 原始证据：`.local/runs/runs/user_scatter_20261108_051001/probe.json`。探针应用在 `finally` 中关闭，`native_closed=true`；没有创建分析任务，模型修订保持为初始化后的1。
- 结论：DLL输入资源已存在；本机正式User设置工厂阻止参数元数据读取和设置，条目保持受阻。
- 解除条件：OpticStudio提供可创建/读取 `ISurfaceScatteringUser` 的正式接口，且 `GetParamData` 不再因 `UILDScatterData` 序列化失败；随后完成DLL列表、参数编号回读、几何追迹、保存重载和资源关闭验收。
