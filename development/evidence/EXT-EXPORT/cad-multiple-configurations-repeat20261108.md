# CAD 多配置分层复测（2026-11-08）

- 条目：`EXT-EXPORT.CadMultipleConfigurations`；源码及发行基线 `0.1.61`；OpticStudio `24.2.0 build 240529 PremiumEdition`。
- 范围：双配置顺序模型上的 `current`、`single`、`all_by_layer`、`all_at_once`、`all_by_file` 导出，并复测 IGES 分层模式。
- 输入：测试自建两面 N-BK7 平面圆柱，半径 2 mm，配置 1/2 厚度分别为 2/4 mm；配置 1、2 的组合厚度分别为 4、6 mm。配置模型保存并重新打开后开始基线采集。
- 命令：`.venv\Scripts\python.exe -m pytest tests/native/test_cad_multiple_live.py::test_native_cad_multiple_configurations -q --run-zemax -rxX`。
- 结果：五种 STEP 配置模式任务均成功，文件体积独立解析。当前配置体积为 `π·4·4`，单配置2为 `π·4·4`，AllByLayer/AllAtOnce为 `π·4·6`，AllByFile分别按配置厚度验证；检查容差 `1e-5 mm³ + 1e-6×参考值`。AllByFile 返回两个配置文件。五个任务均 `close_attempted=true` 且无 cleanup warnings。
- 设置及模型保持：每项任务回读配置模式；每项调用后比较配置表、曲面及系统设置，测试断言均通过。
- 分层结果：IGES `all_by_layer` 文件解析得到实际层 `{65535}`，预期 `{10,11}`；`all_at_once` 得到 `{65535}`，预期 `{10}`。两个任务输出文件均可读，偏差与 2026-11-07 的实体层诊断一致。
- 运行目录：`.local/runs/runs/cad169_multiple_9f7b30fe62`；原始层解析为 `all_by_layer-layers.json`、`all_at_once-layers.json`，请求/任务记录在 `calls.json`、`exports.json`；native close receipt 为 `state/close_receipt.json`，`closed=true`。
- 会话：测试完成后没有遗留 pytest、Python 或 OpticStudio 进程；close receipt 记录原生关闭成功。stdio 测试客户端正常结束。
- 结论：多配置几何导出及任务/模型生命周期通过；IGES 的配置层赋值仍未由导出文件采用，本条保持受阻待定。
- 解除条件：取得能输出请求层号的正式导出路径或确认上游修复，再复核两个 IGES 模式的层分配。
