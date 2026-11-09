# 机械半口径 ZPLMacro 复测（2026-11-08）

- 条目：`ED-02.ZPLMacro.MechanicalSemiDiameter`；源码及发行基线 `0.1.61`；OpticStudio `24.2.0 build 240529 PremiumEdition`。
- 普通测试：`.venv\Scripts\python.exe -m pytest tests/unit/test_modeling.py tests/unit/test_extended_solves.py -q`，124 passed。
- 原生stdio测试：`.venv\Scripts\python.exe -m pytest tests/native/test_extended_solves_live.py::test_mechanical_semi_diameter_zpl_macro_name_adoption -q -s --run-zemax`，1 passed。自有临时宏 `MCP93_*.ZPL` 内容为 `SOLVERETURN .625`，位于`application.ZPLDir`；`get_system_resources(solve_macros, surface=1, cell=mechanical_semi_diameter)`包含该宏。
- 设置尝试：对目标面提交`mode=zpl_macro`和临时宏名，`replace_solves=true`。原生实际模式回退为`Fixed`，MCP返回`SOLVE_UPDATE_FAILED`，外层`PARTIAL_UPDATE`；失败面状态显示mechanical_semi_diameter solve=Fixed、macro为空。宏未执行，未取得0.625数值结果。
- 恢复与生命周期：检查点存在且重开后原机械半口径数值/模式恢复；临时宏由测试finally删除，stdio断开和原生关闭成功。
- 结果目录：`.local/runs/runs/mechanical_semi_diameter_zpl_macro_probe_32ec18896a`；请求、错误、失败面状态及恢复调用在`calls.json`；关闭回执在`state/close_receipt.json`。
- 结论：本机宏资源可发现，但机械半口径ZPLMacro模式未被采用，条目保持受阻。
- 解除条件：原生实际采用ZPLMacro并回读指定宏名，保存重载后保持，再验证宏返回值和关闭。
