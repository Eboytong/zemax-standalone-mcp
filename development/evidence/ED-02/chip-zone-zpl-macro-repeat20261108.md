# ChipZone ZPLMacro 复测（2026-11-08）

- 条目：`ED-02.ZPLMacro.ChipZone`；源码及发行基线 `0.1.61`；OpticStudio `24.2.0 build 240529 PremiumEdition`。
- 普通测试：`.venv\Scripts\python.exe -m pytest tests/unit/test_modeling.py tests/unit/test_extended_solves.py -q`，124 passed。
- 原生stdio测试：`.venv\Scripts\python.exe -m pytest tests/native/test_extended_solves_live.py::test_chip_zone_zpl_macro_name_adoption -q -s --run-zemax`，1 passed。自有临时宏 `MCP92_930420182f.ZPL` 内容为 `SOLVERETURN .375`，位于`application.ZPLDir`；`get_system_resources(solve_macros, surface=1, cell=chip_zone)`返回含该宏的29项列表。
- 设置尝试：提交 `mode=zpl_macro, macro=MCP92_930420182f`、`replace_solves=true`。原生类型可切为ZPLMacro，但实际宏名回读为空；适配器返回`SETTING_REJECTED`（requested为临时宏名、actual为空），外层`PARTIAL_UPDATE`。失败面状态显示solve类型ZPLMacro、macro为空；宏未执行，未产生可验证的0.375结果。
- 恢复与生命周期：错误附带检查点；测试重开检查点并比较原ChipZone值/solve模式，断言通过。临时宏由测试finally删除；stdio断开和原生关闭成功。
- 结果目录：`.local/runs/runs/chip_zone_zpl_macro_probe_86e90a6fde`；原生请求、资源列表、失败面状态及关闭回执分别在`calls.json`、`state/close_receipt.json`。
- 结论：宏目录发现可用，ChipZone ZPLMacro类型本身可设置，但正式接口没有采用宏名，条目保持受阻。
- 解除条件：原生实际回读请求宏名，并在保存重载后仍保持同一名称；随后确认宏返回值及资源关闭。
