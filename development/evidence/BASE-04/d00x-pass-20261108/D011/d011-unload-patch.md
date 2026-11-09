# D011 Unload 实现记录（已集成入主区，待原生验收）

状态：**已实现并集成入主区**（来源 workspace `codex/d002-material-model`，基线 `34e1a18`）。未提交 Git；原生验收仍延后。

## 已改动文件

1. `src/zemax_mcp/star_models.py`
   - 新增 typed 请求：
     ```python
     class StarUnload(Request):
         kind: Literal['unload_deformation', 'unload_temperature', 'unload_direct_index']
         surface: PositiveIndex
     ```
   - `StarOperation` 联合加入 `StarUnload`（`StarImport | StarFit | StarUnload | StarRigidBody | ...`）。
   - 共享入口 `run_star_operation(request: StarOperation)` 与 `backend.py` 的 `COMMAND_MODELS` 按联合/`RunStar` 自动接纳，无需改 server 签名。
2. `src/zemax_mcp/star.py`
   - 新增 `_run_star_unload(self, q, data_kind)`：`_mutate` 检查点 → 记录前状态 → `FEAData.UnloadData()` → `yield` 取消边界 → 记录后状态并核对导入标志清除 → 尽力而为 `get_star_data` → 失败/取消 `_restore_model`，恢复失败 `STAR_RESTORE_FAILED` 并保留原始/恢复错误。
   - `run_star_operation` 在算出 `data_kind` 后：`if q.kind.startswith('unload_'): return self._run_star_unload(q, data_kind)`。
   - 导入标志成员来自 `BRANCHES[data_kind][1]`（`AreDeformationsImported`/`AreTemperaturesImported`/`IsDirectIndexImported`），未虚构 `_are*` 字段。
3. `src/zemax_mcp/backend.py`
   - capabilities `operations=['import','fit','unload',*sorted(CONTROL_KINDS)]`（最小共享入口补丁；`implemented_tools` 仍 101）。
4. `docs/topics/extensions/star.md` — 新增“## 卸载”小节。
5. `examples/requests/star-unload.json` — 示例请求。
6. `tests/unit/test_star.py` — 新增卸载测试（3 类型 × 成功/未导入/未清除/取消/原生失败 + 参数合同 + 空数据 Fits 不可用），全部通过。

## 行为约定

- 前读：`imported`、`total=NumberOfDataPoints`、`filename=Filename`。
- 未导入 → `MISSING_FEA_DATA`（预检，不修改模型）。
- 调用 `data.UnloadData()` 后若 `imported` 仍为真 → `SETTING_REJECTED`，触发恢复。
- 记录 `payload.before`、`payload.after` 与 `payload.source_file`（`path`/`exists_before`/`exists_after`/`no_source_delete_performed=true`）；源为导入暂存副本，卸载不删磁盘文件。
- 成功判据 = `read_state` 回读导入标志清除；详细 `get_star_data` 为尽力而为（成功 `detail`，不可用 `detail_unavailable`），空数据下 Fits/坐标/热控读取失败**不会**把成功卸载误报失败。
- 取消在卸载调用后边界生效；失败/取消恢复基线；恢复失败 `STAR_RESTORE_FAILED` + `requires_reconnect`。

## 验证（实测，权威）

- `tests/unit/test_star.py`：**47 passed**（26 既有 + 21 卸载）。
- 全 STAR 单测 `test_star.py + test_star_controls.py + test_star_materials.py` → **83 passed**（47 + 25 + 11），XML `review-d011-star-unload.xml`。
- typed schema 受影响范围：`tests/unit/test_model_adaptation.py` → **16 passed**（含 `implemented_tools==101` 断言），XML `review-d011-schema.xml`。

## 待完成（外部）

- 原生解除：`IsSTARModuleEnabled=True` + 独立拥有的 FEA 副本，验证导入标志转 false、源保留、恢复、关闭；三类型各自数值/生命周期验收。条目仍 `blocked`。
