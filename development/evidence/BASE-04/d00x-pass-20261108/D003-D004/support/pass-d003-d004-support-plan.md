# D003 / D004 支持审计计划（只读）

任务：复用 Agent 2（`zemax-p01-material-reports`）对 D003/D004 七项的**只读支持审计**，产出逐项事实材料，供主 owner（`zemax-p01-material-model`）与协调者统一索引。
工作区（执行）：`C:\Users\tonge\.codex\worktrees\zemax-p01-material-reports\Zemax_MCP`
主仓（只读源码/证据）：`C:\Users\tonge\Desktop\Zemax_MCP`
OpticStudio：24.2.0 build 240529 PremiumEdition｜Python 3.14｜源码基线 0.1.62

## 0. 边界与约束

- **无新原生**：不创建原生会话；离线审计可引用 2026-11-08 历史原生结果，但必须注明记录日期与来源文件。
- **无全量回归**：只跑下述六个定向单元文件；沿用既有 105 项相关检查结论，不重跑。
- **无源码/台账修改**：不改产品代码、不改 `development/ledgers/*.csv` 与 `d00x-pass-20261108.json` 的 `pass_state`、不改 shared 索引。
- **无 Git、无清理**：不提交、不删除既有文件；保留既有临时目录。
- **属主不变**：主 owner 仍 `zemax-p01-material-model`；本 worker 仅输出审计事实与建议，不申报完成、不代改索引。

## 1. 依据

- 分组定义：`development/tracking/development-groups.json`
  - **D003 顺序建模、拾取与模式转换**：prerequisites「solve 聚合需 D002 的 MaterialModel 完成」；completion「联动值、代表性光线、配置和 solve 保存重载对应；失败保留原始错误与恢复入口，所有任务有终态及关闭回执」。
  - **D004 像质、光斑与屈光力分布**：prerequisites「现有标准光斑、近轴量、Seidel 系数与 FFT/复瞳参考」；completion「返回坐标、单位、有效掩码和原始值；光斑归属与布局对应」。
- 条目与属主：`development/tracking/d00x-pass-20261108.json:130-227`——七项 `worker_id=zemax-p01-material-model`，`support_worker_ids` 含 `zemax-p01-material-reports`，`pass_state=pending_review`，`evidence=[]`（计划内未挂证据，需从 `development/evidence` 取）。
- 原生记录：`development/evidence/{ED-02,NS-01,ED-04,CV-01}/*20261108.md` 与所引 run 目录 / progress json。

## 2. 七项清单（组 / 依赖 / 主仓接口锚点）

| 条目 | 组 | 主仓接口（当前源码） | 依赖 / 备注 |
| --- | --- | --- | --- |
| ED-02.SolveExtensions018 | D003 | 求解请求联合体 `models.py:321-323`（`MaterialModelSolve :289`、`MaterialSubstituteSolve :305`、`MaterialOffsetSolve :299`、`SolveSpec mode=surface_pickup :229`）；原生映射 `modeling.py:14,16-28`（`SOLVES`、`SOLVE_FIELDS`） | **包级依赖** `ED-02.MaterialModel.Material` + 两种 Pickup（`ED-02.SurfacePickup.ChipZone`、`ED-02.SurfacePickup.MechanicalSemiDiameter`，见 groups `depends_on_item_ids`） |
| NS-01.Conversion | D003 | `conversion_models.py:6-22`（`NscConversion`）；`conversion.py:22-71`（`OpenConvertToNSCGroup`，`configure` 回读校验，`collect` 判 `tool.Succeeded`） | 混合组转换 |
| ED-04.RayAimingWizard | D003 | `design_models.py:51-53`（`RayAimingWizard.apply`）；`design_tools.py:47-60`（options/close）、`:90-164`（`GetRecommendedSettings`/`ApplyRecommendedSettings`/回读） | 生命周期/取消/关闭 |
| CV-01.SeidelDiagram | D004 | `analysis_models.py:680-685`；`analyses.py:457-460`（`configure_seidel_diagram`）、`:806` 分派、`:1009-1011` 结果定义；出口=`GetTextFile`（`_collect_general_analysis :840-844`） | 图形/数值出口 |
| CV-01.FullFieldSpot | D004 | `analysis_models.py:598-605`（`FullFieldSpot`）；`spot_topics.py:17-78`（`SpotData` 读取；无行→`RESULT_UNAVAILABLE`） | 全视场光斑 |
| CV-01.MatrixSpot | D004 | `analysis_models.py:584-596`（`ConfigurationMatrixSpot` kind=`matrix_spot`）；`analyses.py:633-639`（`setv` 设置回读） | 矩阵光斑 |
| CV-01.ConfigurationMatrixSpot | D004 | 同上，kind=`configuration_matrix_spot` | 配置矩阵光斑 |

## 3. 逐项审计目标（每项固定字段）

对七项分别提取并写入 items/report：
1. **正式接口**：typed request 类与字段、分派点、原生 tool/settings 类型。
2. **实际输入**：本次历史记录所用的受控模型/样例与请求参数（有则列出）。
3. **设置采用**：请求值 → 原生回读值 / `SETTING_REJECTED` / `SOLVE_UPDATE_FAILED` 等。
4. **结果计数**：`NumberOfDataSeries/Grids/ScatterPoints/RayData/Messages` 或 `SpotData` 非空性、文本导出真假。
5. **原始错误**：`EXPORT_FAILED` / `RESULT_UNAVAILABLE` / `TASK_START_FAILED` / `TASK_FAILED` / `SOLVE_UPDATE_FAILED` + message。
6. **关闭与恢复**：`close_attempted/closed/error`、`requires_reconnect`、检查点恢复/系统状态不变性。

## 4. 关键判定原则（防止混同与夸大）

- **「原生计算通过」≠「仅正确返回错误」**：逐项标注类别——
  - 计算完成且有数值结果（可对门槛）；计算完成但出口为空（`EXPORT_FAILED`/`RESULT_UNAVAILABLE`）；原生启动/执行失败（`TASK_START_FAILED`/超时未终态）；设置未采用（`SOLVE_UPDATE_FAILED`/实际 solve 不符）。
- **包级 SolveExtensions 不因子项部分实现收口**：`ED-02.SolveExtensions018` 只有在 MaterialModel + 两种 Pickup 全部满足后才可整体收口；任一子项（Abbe 数值门槛、ChipZone/MechanicalSemiDiameter 采用）未过即保持未收口。
- **零结果分析的等价追迹替代**：若提出以光线追迹等价替代（FullFieldSpot / MatrixSpot / ConfigurationMatrixSpot / SeidelDiagram），必须**同时保留参考点、坐标系与分面（facet）声明**；若无**可验证的官方定义**，记录**具体阻塞**，不得以近似图替代验收。

## 5. 定向测试与 XML

运行（本工作区，普通单元，无 `--run-zemax`）：
`tests/unit/test_extended_solves.py`、`test_conversion.py`、`test_design_tools.py`、`test_seidel_diagram.py`、`test_full_field_spot.py`、`test_configuration_matrix_spot.py`
→ 保存 JUnit XML：`.local/coordination/pass-d003-d004-pytest.xml`；逐文件计数写入报告。

## 6. 交付物

| 文件 | 内容 |
| --- | --- |
| `.local/coordination/pass-d003-d004-support-plan.md` | 本计划 |
| `.local/coordination/pass-d003-d004-items.json` | 七项机器可读审计条目（固定字段 + 类别标注 + 阻塞/解除条件） |
| `.local/coordination/pass-d003-d004-report.md` | 支持审计报告（逐项事实、判别、风险、待协调者事项） |
| `.local/coordination/pass-d003-d004-pytest.xml` | 六个定向文件的 JUnit 结果 |
