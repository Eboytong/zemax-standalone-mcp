# 机械半口径 SurfacePickup 复测（2026-11-08）

- 条目：`ED-02.SurfacePickup.MechanicalSemiDiameter`；源码及发行基线 `0.1.61`；OpticStudio `24.2.0 build 240529 PremiumEdition`。
- 普通测试：`.venv\Scripts\python.exe -m pytest tests/unit/test_modeling.py tests/unit/test_extended_solves.py -q`，124 passed。
- 原生试验：`.venv\Scripts\python.exe -m pytest tests/native/test_extended_solves_live.py::test_mechanical_semi_diameter_surface_pickup_rejection_and_checkpoint_restore -q -s --run-zemax`，1 passed。自建顺序系统源面/目标面机械半口径分别设为5.5/5.2，再请求目标面从源面SurfacePickup、scale=1、offset=0、`replace_solves=true`。
- 原生结果：请求单元格支持列表包含SurfacePickup；设置后原生实际模式为`Fixed`，MCP返回`SOLVE_UPDATE_FAILED`（requested=SurfacePickup, actual=Fixed, cell=mechanical_semi_diameter），批量外层返回`PARTIAL_UPDATE`，failed_surface=2、completed_surfaces=[]，修订号6，并包含失败面状态与检查点。
- 恢复：检查点存在；重开后源面和目标面机械半口径数值及solve模式与失败前快照一致。
- 生命周期：stdio测试结束后close receipt记录`native.closed=true`；无原生任务创建，测试客户端正常结束。
- 结果目录：`.local/runs/runs/mechanical_semi_diameter_pickup_refusal_c461b3eaf9`；请求、原始响应、失败面与检查点恢复记录在`calls.json`，关闭记录在`state/close_receipt.json`。
- 结论：本机原生接口没有采用机械半口径SurfacePickup，成功设置与保存重载路径未通过；条目保持受阻。
- 解除条件：原生设置后实际solve回读为SurfacePickup；再检查源面、比例/偏移参数、动态数值联动和保存重载。
