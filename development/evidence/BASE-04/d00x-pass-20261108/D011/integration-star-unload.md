# 集成报告：D011 STAR Unload 小补丁

- 来源工作区：`C:/Users/tonge/.codex/worktrees/zemax-p01-material-model/Zemax_MCP`（分支 `codex/d002-material-model`，基线 `34e1a18`）
- 集成方式：`git diff 34e1a18` 生成最小补丁 `git apply`（5 文件）+ 复制示例 JSON；按任务裁剪新注释/文档中的哈希表述，只述字段功能
- 保留主仓其他 hunk（`tests/support/material_reference.py` 主区已有、未重复集成）
- 未执行原生；未全量；未提交 Git；未改发行；未清理临时目录

## 1. 实际合入文件（主仓）

| 文件路径 | 变更 | 说明 |
| --- | --- | --- |
| `src/zemax_mcp/star_models.py` | +7/−1 | `StarUnload(kind∈{unload_deformation,unload_temperature,unload_direct_index}, surface:PositiveIndex)`；`StarOperation` 联合加入 `StarUnload` |
| `src/zemax_mcp/star.py` | +62 | `_run_star_unload`（检查点/取消/恢复/best-effort detail）；`run_star_operation` 分派 `unload_*` |
| `src/zemax_mcp/backend.py` | +1/−1 | capabilities `operations` 加 `'unload'`（工具数仍 101） |
| `docs/topics/extensions/star.md` | +10 | “## 卸载”小节（已去哈希表述） |
| `examples/requests/star-unload.json` | 新增 74 B | `{"request":{"kind":"unload_deformation","surface":1}}` |
| `tests/unit/test_star.py` | +110 | 21 个卸载用例（成功/未导入/未清除/取消/原生失败/参数合同/空数据 Fits 不可用） |

裁剪：`star.py` 删除“source identity / no content-hash check”注释块，保留 `# Detailed STAR read is best-effort; unavailability is recorded, not fatal.`；`star.md` 删除 `，不做内容/哈希校验`。

## 2. 主仓真实通过数（权威）

- `pytest tests/unit/test_star.py tests/unit/test_star_controls.py tests/unit/test_star_materials.py` → **83 passed**
  - `test_star.py` **47**（26 既有 + 21 卸载）+ `test_star_controls.py` **25** + `test_star_materials.py` **11** = **83**（即 83 = 47 star + 其余 controls/materials）
- `pytest tests/unit/test_model_adaptation.py` → **16 passed**（含 `len(implemented_tools)==101`）。此项**另计 16，不累计、不重叠**（与上组无交集）。
- XML（已复制入 durable）：`review-d011-star-unload.xml`（83 tests / 0 fail）、`review-d011-schema.xml`（16 tests / 0 fail）。

> 计数口径修正：源 worker 审计文档内历史 `80/25/28` 早早数字**非最新**；durable 副本统一校正为 **83 / 47 / 21**。

## 3. 三个 Unload 条目状态

- 主仓**已实现**（`StarUnload` 联合 + `_run_star_unload`，离线测试全绿），**待原生验收**。
- **实际台账状态保持 `blocked` 不变**（未改台账/批次/tracking）；`verified` 未置真。
- dn/dT：**只要求有限性**（允许零/负值），不添加 `value>0` 正性门（此为正确行为，历史“缺正性门”判断已撤销）。

## 4. Durable 副本

目录：`development/evidence/BASE-04/d00x-pass-20261108/D011/`
- `pass-d011-plan.md`、`pass-d011-report.md`、`pass-d011-items.json`（16 项；3 个 Unload 项描述为“主仓已实现待原生”，台账 `blocked` 不变）
- `d011-unload-patch.md`（清理版实现记录）
- `integration-star-unload.md`（本报告）
- `review-d011-star-unload.xml`（83 tests）、`review-d011-schema.xml`（16 tests）

## 5. 剩余 native 条件

- 三 Unload 项仍 `blocked`：需 `IsSTARModuleEnabled=True` + 独立拥有的 FEA 副本，原生验证导入标志转 false、源保留、恢复、关闭；16 项本轮均不 close。
- 未合入仍在审查的 gradium STAR 分析/散射补丁（等批准）。
