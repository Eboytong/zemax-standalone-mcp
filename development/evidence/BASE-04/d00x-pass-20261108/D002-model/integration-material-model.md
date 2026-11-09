# MaterialModel 参考交付：集成记录（已应用）

状态：**已应用并保持合入**。按批准范围只合入三项；未审批的两个 Power 探针**未合入**。
主区其他未提交变更保持原样，索引未动，未提交。

进度编号按 **D00x**。

## 1. 来源

`C:\Users\tonge\.codex\worktrees\zemax-p01-material-model\Zemax_MCP`（分支 `codex/d002-material-model`）。
协调者在来源树普通测试 **97 项通过**。

## 2. 合入前同符号核对

| 检查 | 结果 |
| --- | --- |
| 主区 `tests/support/material_reference.py` vs 基线 `34e1a18` | **无差异** → 无他人未提交修改，补丁可干净应用 |
| `tests/unit/test_material_model_reference.py` 是否已存在 | 否 → 无归属冲突 |
| `scripts/probes/D002-MODEL_GLASS/model_glass_control018.py` 是否已存在 | 否 → 无归属冲突 |

## 3. 已合入的三项

| # | 路径 | 类型 | 规模 |
| --- | --- | --- | --- |
| 1 | `tests/support/material_reference.py` | 修改 | **+49 / −11**（2 个 hunk） |
| 2 | `tests/unit/test_material_model_reference.py` | 新增 | 4621 B / **12 个用例** |
| 3 | `scripts/probes/D002-MODEL_GLASS/model_glass_control018.py` | 新增 | 13001 B |

### 采用的 hunks（`tests/support/material_reference.py`）

| hunk | 位置 | 功能 |
| --- | --- | --- |
| 1 | `@@ -1,6 +1,11 @@` | 新增 `PHYSICAL_LINES`（0.5875618 / 0.4861327 / 0.6562725，手册 pp.1347-1348）与 `CLASSIC_LINES`（0.5876 / 0.4861 / 0.6563，既有 model-solve 检查实际使用值） |
| 2 | `@@ -14,19 +19,52 @@` | 抽出 `line_positions`、`abbe_from_wavelengths`、`snell_rays`、`snell_request`、`snell_indices_from_rows`；`snell_indices` 改为调用这些 helper |

**语义保持不变**：`snell_indices` 仍是同一请求体（`input_mode='Direct'`、surface 0→1、两组入射角 × 各波长）、
同一断言（`error_code==0`、`vignette_code==0`、行数 `2*count`）、同一容差（`atol=rtol=1e-10`）、
同一检查标签 `Snell independent angle <波长>`。变化是把内联逻辑变成可离线单测的具名函数，并显式区分
"手册物理谱线"与"既有检查用的四位小数谱线"两套约定。

## 4. 未合入（明确排除）

- `scripts/probes/CV-02/power_asymmetric_aperture018.py`
- `scripts/probes/CV-02/power_radius_sweep018.py`

二者**未审批**，主区 `scripts/probes/CV-02/` 仍不存在。

## 5. 实际测试结果

**与协调者 97 项一致的对应范围**（主区实跑）：

```
pytest tests/unit -k "material or glass" -q -p no:cacheprovider
→ 97 passed, 2523 deselected in 2.73s
```

XML：`.local/evidence/development/BASE-04/parallel-01/review-material-model-integration.xml`

**97 项范围的确定方式**（实测收集数，非估计）：

| 范围 | 收集数 |
| --- | --- |
| `tests/unit` 全量 | 2620 |
| `-k material` | 83 |
| `-k glass` | 18 |
| **`-k "material or glass"`** | **97** ← 与协调者结论一致 |
| `-k solve` | 95 |

即"材料 + 玻璃"两类共 97 项，与来源工作区所跑的 97 项同一集合。

**直接消费该 helper 的两个文件**（先跑的窄范围）：

```
pytest tests/unit/test_materials.py tests/unit/test_material_model_reference.py -q
→ 52 passed in 0.44s
```

（`test_materials.py` 40 + `test_material_model_reference.py` 12 = 52。）

未跑全量；未跑原生；未提交。

## 6. 复核

- `git diff 34e1a18 --stat -- tests/support/material_reference.py` = **49 insertions(+), 11 deletions(-)**
- 两份新文件已合入主区
- `tests/support/material_reference.py` 行尾：CRLF=78、裸 LF=0、无 BOM
- `git diff --cached --stat` 为空（索引未动）

## 7. 风险

- `material_reference.py` 是**共享测试辅助**：`tests/native/test_extended_solves_live.py` 与
  `tests/native/test_material_offset_reference_live.py` 也导入它（`abbe`、`model_indices`、`sellmeier1`、`snell_indices`）。
  本次只做了普通单测验证，**原生侧导入未被验证**（原生队列暂停）。
- 新增 `CLASSIC_LINES` 与 `PHYSICAL_LINES` 两套约定并存；若后续把既有检查迁到物理谱线，
  `test_extended_solves` 等原生检查的期望值会整体变化，需同步而非局部改。
- `model_glass_control018.py` 是探针脚本，不在测试收集范围，未被执行。
