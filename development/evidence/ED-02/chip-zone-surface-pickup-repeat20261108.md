# ChipZone SurfacePickup 复测（2026-11-08）

- 条目：`ED-02.SurfacePickup.ChipZone`；源码及发行基线 `0.1.61`；OpticStudio `24.2.0 build 240529 PremiumEdition`。
- 普通测试：`.venv\Scripts\python.exe -m pytest tests/unit/test_modeling.py tests/unit/test_extended_solves.py -q`，124 passed。
- 原生试验：`.venv\Scripts\python.exe -m pytest tests/native/test_extended_solves_live.py::test_chip_zone_surface_pickup_rejection_and_checkpoint_restore -q -s --run-zemax`，1 passed。真实 stdio 中用自建顺序模型将源面ChipZone设为0.5、目标面设为0.2，均先回读为固定值，再提交目标面拾取源面、scale=1、offset=0、`replace_solves=true`。
- 原生结果：单元格支持列表包含`SurfacePickup`；`SetSolveData`返回Success但最终`cell.Solve=Automatic`。适配器返回`SOLVE_UPDATE_FAILED`，包括`requested=SurfacePickup`、`actual=Automatic`、`cell=chip_zone`；批量更新返回`PARTIAL_UPDATE`，`failed_surface=2`、`completed_surfaces=[]`、修订号6，并包含目标面状态及检查点。
- 恢复：检查点文件存在；重新打开后源面0.5及目标面0.2的ChipZone值和solve模式与请求前快照相同。
- 生命周期：会话断开后close receipt记录`native.closed=true`；没有原生任务创建，测试客户端正常结束。
- 结果目录：`.local/runs/runs/chip_zone_pickup_refusal_cdca2ea390`；`calls.json`保存请求、原始错误、失败面状态、检查点恢复和回读；`state/close_receipt.json`保存关闭状态。
- 结论：公开请求模型、原生支持枚举与失败诊断已确认；本机原生设置未采用SurfacePickup，无法完成成功路径及保存重载验收，条目保持受阻。
- 解除条件：原生设置接口实际将ChipZone solve采用并回读为SurfacePickup；随后验证来源面、比例/偏移、数值联动、保存重载及关闭。
