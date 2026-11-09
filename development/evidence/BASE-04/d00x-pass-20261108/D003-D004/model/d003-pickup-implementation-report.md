# D003 实现报告：ChipZone / 机械半口径 SurfacePickup

条目：`ED-02.SurfacePickup.ChipZone`、`ED-02.SurfacePickup.MechanicalSemiDiameter`，**均保持 `blocked`**。
工作区 `C:\Users\tonge\.codex\worktrees\zemax-p01-material-model\Zemax_MCP`，分支 `codex/d002-material-model` 不变。
**本轮未运行原生、未改 backend 产品逻辑、未改公共契约/schema/台账/批次、未提交。** MaterialModel 与 Power Maps 全部交付原样保留。

## 1. 审查意见与落实

| # | 审查意见 | 落实 |
| --- | --- | --- |
| 1 | 列枚举合法只排除"枚举名称无效"，不能排除绑定/活动条件 | 计划 §3 增加"关于枚举合法性的限定"段，§2 结论收窄为"列名本身不是失败原因" |
| 2 | `GetSolveData().Type` 等成员要逐项核反射清单 | 新增 `.local/coordination/d003-interface-check.py`，5 个接口、逐成员核对，全部命中（§2） |
| 3 | 可准备有界 C2/C3 控制探针与必要普通测试 | `scripts/probes/ED-02/pickup_solve_adoption018.py` + `tests/unit/test_pickup_probe_contracts.py`（5 项） |
| 4 | 提交前不改 backend 产品逻辑 | 未改 `src/`；探针只读调用现有 API |
| 5 | 无证据时保持 blocked | 两条目状态未变，无完成计数 |

## 2. 逐项接口核对结果（离线，`d003-interface-check.py`）

| 接口 | 结果 |
| --- | --- |
| `ZOSAPI.Editors.IEditorCell` | OK：`IsActive`、`IsReadOnly`、`Solve`、`Value`、`DoubleValue`；`GetSolveData`、`IsSolveTypeSupported`、`GetAvailableSolveTypes`、`CreateSolveType`、`SetSolveData`、`MakeSolveFixed`、`MakeSolveVariable` |
| `ZOSAPI.Editors.ISolveData` | OK：`IsValid`、`Type`、`_S_SurfacePickup`、`_S_Automatic`、`_S_Fixed` |
| `ZOSAPI.Editors.ISolveSurfacePickup` | OK：`Surface`、`ScaleFactor`、`SupportsScale`、`Offset`、`SupportsOffset`、`Column`；`IsPickupFromCurrentColumn`、`MakePickupFromCurrentColumn` |
| `ZOSAPI.Editors.LDE.ILDERow` | OK：`ChipZone`、`ChipZoneCell`、`MechanicalSemiDiameter`、`MechanicalSemiDiameterCell` |
| `ZOSAPI.IOpticalSystem` | OK：`UpdateStatus`、`UpdateFileLists`、`Save`、`LoadFile` |

补充事实：

- `ChipZoneCell` 与 `MechanicalSemiDiameterCell` 的反射类型都是 `ZOSAPI.Editors.IEditorCell`（通用单元格），无专用接口。
- `SurfaceColumn.ChipZone=7`、`SurfaceColumn.MechanicalSemiDiameter=8`——**仅证明枚举名有效**。
- 全库唯一的 `DoManualUpdate()` 属于 `ISTARSubsystem`，与 LDE 求解无关；因此仍无整系统重算入口，"Update 后恢复"只能靠 `UpdateStatus()`、追迹、保存重载间接探测。

## 3. C2/C3 控制探针（`pickup_solve_adoption018.py`）

- **C2（单变量 = 回读时机）**：同一请求，依次在 `immediate` / `after_update_status` / `after_ray_trace` / `after_save_reload` 四个时刻做**三路回读**：
  `str(cell.Solve)`、`str(GetSolveData().Type)`、`_S_SurfacePickup{Surface,Column,ScaleFactor,Offset,IsPickupFromCurrentColumn}`。
  任一路不一致即视为未采用，`adopted_at` 记录首次采用时刻。
- **C3（单变量 = 绑定方式）**：仅当 C2 全程未采用时执行，分支 `make_pickup_from_current_column`、`make_solve_fixed_first`。
- 两个单元格各跑一遍；每例先记录 `supported`、`is_solve_type_supported`、`is_active`、`is_read_only`、`solve_valid`、`supports_scale/offset`、`set_status`。
- 有界：任务轮询 180 s；`TaskFailure` 保留原始 task/result；`finally` 关闭；`error` 与 `cleanup_error` 分开；回执全文入库。

## 4. 普通测试（`tests/unit/test_pickup_probe_contracts.py`，5 项）

用 FakeBackend 跑**真实探针**，两个"世界"分别验证可区分性：

| 测试 | 断言 |
| --- | --- |
| `test_probe_reports_never_adopted` | `set_status=='Success'` 但四个时刻 `adopted=False`；`first_adoption_step=None`；C3 两个变体都执行且未采用 |
| `test_probe_distinguishes_adoption_after_update` | `immediate=False`、`after_update_status=True`、`first_adoption_step=='after_update_status'`；C3 被跳过 |
| `test_probe_records_three_way_readback_and_activity` | `cell_solve`/`solve_data_type`/`is_active`/`is_read_only`/`value`/`supported`/`solve_valid` 均被记录 |
| `test_probe_covers_both_cells` | 两单元格都跑；机械半口径失败前为 `Fixed` |
| `test_probe_keeps_cleanup_and_error_separate` | shutdown 抛错时 `cleanup_error` 记录、`closed` 仍 true、`error` 不出现 |

这两项"never / after update"测试正是审查要求的**可区分性**证明：同一个探针在两种原生行为下给出不同且正确的记录。

## 5. 实际执行的检查与结果

| 检查 | 命令 | 结果 |
| --- | --- | --- |
| 接口逐项核对 | `python -B .local/coordination/d003-interface-check.py` | 5/5 接口 OK，`missing=[]`，exit 0 |
| 拾取探针普通测试 | `python -B -m pytest tests/unit/test_pickup_probe_contracts.py -q -p no:cacheprovider` | **5 passed** |
| 探针编译 | `python -B -m py_compile scripts/probes/ED-02/pickup_solve_adoption018.py` | ok |
| 原始 stdio 复算 | `d003-calls-index.py`、`d003-calls-detail.py` | 两份日志各 11 条调用，字段级核对一致 |
| `git status` | — | 无 `src/` 改动 |

首次运行 5 项全失败，原因是 FakeCell 缺少 `Solve` 属性（探针读 `cell.Solve` 是正确行为），补 `Solve` 属性后 5/5 通过；探针本身未改。

## 6. 状态与剩余风险

- 两条目仍 `blocked`；`docs/topics/modeling/solve-extensions.md:76-79` 的限制表未改。
- 探针**未执行**：`application_create` 180 s 超时未解除。
- 枚举合法性只排除"名称写错"；绑定是否被接受、`IsActive` 是否为前提、`MakePickupFromCurrentColumn` 是否更正式，均仍属未核。
- 机械半口径失败写入导致值 5.2→5.0 的成因仍未解释；探针会记录 `before`/各时刻 `value`，但不推断机制。
- FakeBackend 只验证探针逻辑，不证明原生行为。

## 7. 工作区遗留物（已知，不清理）

- 工作区根目录存在 `pytest-of-tonge/`（pytest 临时目录，由本轮普通测试产生）。
- 依本轮指示**保留**、**跳过清理**，不重试先前被拒绝的删除命令；该目录未纳入 Git，只含测试临时文件，不含源码或产品资产。
