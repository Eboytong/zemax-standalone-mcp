# D003 / D004 支持审计报告（只读）

任务：D003/D004 七项的只读支持审计（Agent 2 / `zemax-p01-material-reports`）
主 owner：`zemax-p01-material-model`（协调者统一索引，本 worker 不申报完成、不改索引）
工作区：`C:\Users\tonge\.codex\worktrees\zemax-p01-material-reports\Zemax_MCP`｜主仓（只读）：`C:\Users\tonge\Desktop\Zemax_MCP`
OpticStudio 24.2.0 build 240529 PremiumEdition｜Python 3.14｜源码基线 0.1.62

**边界**：无新原生；离线审计引用 **2026-11-06/07/08 历史原生结果**（逐条注明来源与日期）；无全量回归（只跑六个定向单元文件）；无源码/台账/`pass_state` 修改；无 Git、无清理。

---

## 1. 七项速览（均 `pending_review`，本轮新增完成 0）

| 条目 | 组 | 类别（判别） | 关键事实 | 完成数 |
| --- | --- | --- | --- | --- |
| ED-02.SolveExtensions018 | D003 | 设置未采用 + 计算通过但门槛未过 | ChipZone→actual=Automatic、MechanicalSD→actual=Fixed（`SOLVE_UPDATE_FAILED`/`PARTIAL_UPDATE`）；MaterialModel Abbe 59.999885…≠60（超 1e-5+1e-7） | 0 |
| NS-01.Conversion | D003 | 原生启动失败 | group 模式 `TASK_START_FAILED`「An unknown error occurred」，`partial_changes_possible=true` | 0 |
| ED-04.RayAimingWizard | D003 | 无可靠终态 | 只读 options/close 可用；历史执行 `TimedOut`、`Close()=false`、需重连 | 0 |
| CV-01.SeidelDiagram | D004 | 计算完成但出口空 | 设置回读有效；文本导出 `EXPORT_FAILED`，无产物 | 0 |
| CV-01.FullFieldSpot | D004 | 计算完成但出口空 | 三次变体均 `RESULT_UNAVAILABLE`（计数全 0、SpotData 空） | 0 |
| CV-01.MatrixSpot | D004 | 计算完成但出口空 | 原生计算有效但 SpotData 空、`GetTextFile=false`→`EXPORT_FAILED` | 0 |
| CV-01.ConfigurationMatrixSpot | D004 | 计算完成但出口空 | 双配置两次计算均完成但出口空；关闭/恢复确认 | 0 |

## 2. 判别纪律：「原生计算通过」≠「仅正确返回错误」

| 类别 | 含义 | 本组条目 |
| --- | --- | --- |
| 计算完成且有数值（对门槛） | 有可对照数值，须与门槛比较 | 无通过者；SolveExtensions018 的 MaterialModel 有数值但**门槛未过** |
| 计算完成但出口为空 | 结果对象有效、无文本/数值载荷（`EXPORT_FAILED`/`RESULT_UNAVAILABLE`） | SeidelDiagram、FullFieldSpot、MatrixSpot、ConfigurationMatrixSpot |
| 原生启动/执行失败 | 无可对照结果（`TASK_START_FAILED`/`TASK_FAILED`） | NS-01.Conversion（group） |
| 设置未采用 | `SOLVE_UPDATE_FAILED`，实际 solve≠请求 | SolveExtensions018（两种 Pickup） |
| 无可靠终态/无法关闭 | 超时未终态、`Close()` 失败 | ED-04.RayAimingWizard（执行路径） |

> 明确：CV 四项的 `EXPORT_FAILED`/`RESULT_UNAVAILABLE` **只说明原生出口为空/不可用**，**不是**「数值比对通过」；SeidelCoefficients 的数值通过属于**另一个分析**，不能替代 Seidel 图。
>
> **错误码不得计为有效结果**：`EXPORT_FAILED`（出口为空）与 `PARTIAL_UPDATE`（批量外层，`completed_surfaces=[]`、`failed_surface=2`，即无任何曲面完成）都**不能**视为有效/完成结果。`PARTIAL_UPDATE` 仅表示「请求已提出、部分曲面被判定失败」，其 `completed_surfaces` 为空即等价于 0 个成功面；`SOLVE_UPDATE_FAILED` 亦为设置未采用。以上一律按未完成计。

## 3. 包级 SolveExtensions 依赖（不因子项部分实现收口）

`ED-02.SolveExtensions018` 是**包级聚合条目**，`development-groups.json` 的 `depends_on_item_ids` 为：
`ED-02.MaterialModel.Material` + `ED-02.SurfacePickup.ChipZone` + `ED-02.SurfacePickup.MechanicalSemiDiameter`。
三个依赖均未满足（MaterialModel Abbe 门槛未过；两种 Pickup 均未被原生采用），因此**整体不可收口**；MaterialSubstitute/MaterialOffset 与 PickupChiefRay 虽在请求联合体与原生映射中存在（`models.py:299-323`、`modeling.py:14-28`），也不能以「部分类型可映射」视为完成。

## 4. 逐项事实

### 4.1 ED-02.SolveExtensions018（D003）
- **接口**：`SurfaceSolve` 联合体（`models.py:321-323`）：`MaterialModelSolve(:289-296 index_nd/abbe_vd/dpgf/vary_index/vary_abbe/vary_dpgf)`、`MaterialSubstituteSolve(:305-307 catalog)`、`MaterialOffsetSolve(:299-303 nd_offset/vd_offset)`、`SolveSpec mode=surface_pickup(:229-255 source_surface/scale/offset/source_column)`；原生映射 `modeling.py:14,16-28`。反射：`progress598-formal-fit-audit.json`——`ISolveMaterialModel` 暴露 Nd/Abbe/dPgF 与 variation 标志，**无系数方法**；目录拟合方法针对所选目录材料、**无临时 ModelGlass 选择器**。
- **实际输入**：air→N-BK7 平面、六个波长（含 d/F/C）直射光；`IndexNd=1.6, AbbeVd=60, dPgF=0.001`（index/dPgF 变化）。ChipZone 源 0.5/目标 0.2；MechanicalSD 源 5.5/目标 5.2；均 `scale=1, offset=0, replace_solves=true`。
- **设置采用**：ChipZone `SetSolveData`=Success 但 `cell.Solve=Automatic`（请求 SurfacePickup）→ `SOLVE_UPDATE_FAILED`；MechanicalSD 实际 `Fixed` → `SOLVE_UPDATE_FAILED`；批量外层均 `PARTIAL_UPDATE`（`failed_surface=2`、`completed_surfaces=[]`、修订号 6）。
- **结果计数**：MaterialModel 有数值——Snell 导出 Nd 达 1e-6；**导出 Abbe = 59.99988524798844** 对 60，未过保留门槛（1e-5 绝对 + 1e-7 相对）。Pickup 无联动值（未采用）。
- **原始错误**：`SOLVE_UPDATE_FAILED`（ChipZone actual=Automatic；MechanicalSD actual=Fixed）。
- **关闭/恢复**：检查点存在；重开恢复源/目标值与 solve 模式；`native.closed=true`。
- **阻塞**：本机构建不采用两种 SurfacePickup；且缺官方临时材料色散/系数契约以过 Abbe 门槛。
- **解除**：原生回读两种 cell 实际=SurfacePickup 且数值联动、保存重载通过；并取得官方临时材料色散定义或系数读写契约，按原门槛预测验收。
- **证据（日期）**：`ED-02/material-model-repeat20261108.md`、`chip-zone-surface-pickup-repeat20261108.md`、`mechanical-semi-diameter-pickup-repeat20261108.md`（2026-11-08）；`progress598-formal-fit-audit.json`。

### 4.2 NS-01.Conversion（D003）
- **接口**：`NscConversion`（`conversion_models.py:6-22`，含 `mode=group|pure` 等）；`conversion.py:34-71` 经 `OpenConvertToNSCGroup`，`configure` 回读校验、`collect` 判 `tool.Succeeded`。
- **实际输入**：air 2 mm / N-BK7 平板 2 mm / air 2 mm；group，曲面 1–4，`ConvertStopToNSCAperture=false`、`ConvertToGlobalCoordinates=true`、`CreateSourcesAndDetectors=false`、`IgnoreErrors=false`。
- **设置采用**：原生任务回读 `IsValid=true, Succeeded=false, CanCancel=false`。
- **结果计数**：group 模式无可用结果。
- **原始错误**：`TASK_START_FAILED`「An unknown error occurred」，`partial_changes_possible=true`，任务 `failed`。
- **关闭/恢复**：`close_attempted=true, requires_reconnect=false`；检查点恢复曲面与顺序光线到基线；**失败后 187 项检查 0 失败**；检查点重追任务成功；close receipt `attempted/closed=true,error=null`，无残留进程。
- **类别**：原生启动失败（非数值不符）。**单独**：纯转换参考仍为更早的受控 **379 项全过、最大光线误差 `2.815423927327032e-08`**（`NS-01/progress282.json`，纯路径，非混合组）。
- **阻塞/解除**：本构建无可靠 group 转换路径；待可靠路径或修正构建后重跑光学等价、设置/持久化与清理。

### 4.3 ED-04.RayAimingWizard（D003）
- **接口**：`RayAimingWizard(apply=False)`（`design_models.py:51-53`）；options 路由 `design_tools.py:47-60`（`OpenRayAimingWizard` + `read_settings` + close）；执行路由 `design_tools.py:90-164`（`GetRecommendedSettings`→`ApplyRecommendedSettings`→回读）。反射：`FIELDS['ray_aiming_wizard']=()`，安装向导无可读选项字段，`settings={}`。
- **实际输入/设置**：只读 options 查询；before/after `SystemData.RayAiming` 相等（只读不变更）。
- **结果计数**：无计算输出（生命周期/选项）。
- **原始错误（历史执行，`ray-aiming276/probe.json`）**：`RunAndWaitWithTimeout(10)`→`TimedOut`（15.061 s），`IsRunning=true`；`Cancel()=true`；`WaitWithTimeout(10)`→`TimedOut`；`IsRunning` 仍 true；`Close()=false`；因句柄未闭需重连。
- **关闭/恢复**：只读 options/close 正常（`attempted/closed=true,error=null`，stdio 正常）；执行路径句柄未闭→重连。
- **类别**：无可靠终态。**阻塞/解除**：需原生任务到终态且 `Close()` 成功；随后对比 preview/Apply、存/读 Ray Aiming 全字段、确认模型状态。

### 4.4 CV-01.SeidelDiagram（D004）
- **接口**：`SeidelDiagram(ignore_chromatic/ignore_distortion/suppress_frame/plot_scale)`（`analysis_models.py:680-685`）；`configure_seidel_diagram`（`analyses.py:457-460`，分派 `:806`）；结果定义 `:1009-1011`；出口 `GetTextFile`（`:840-844`）。
- **设置采用**：回读 `IgnoreChromatic=false, IgnoreDistortion=false, SuppressFrame=false, PlotScale=0`，有效激活。
- **结果计数/错误**：文本导出失败 `EXPORT_FAILED`，无产物（结果对象有效但出口无载荷）。
- **关闭**：`close_attempted=true`。
- **等价追迹**：需要逐面 Seidel 系数 + 原生绘图比例/边框 + 分面/标注定义；**无可验证定义**（SeidelCoefficients 只给系数，不定义图面布局）→ 记录为具体阻塞。
- **阻塞/解除**：无可用图形/数值 SeidelDiagram 出口；待该出口（或文档化分面/比例契约）后比对数值。

### 4.5 CV-01.FullFieldSpot（D004）
- **接口**：`FullFieldSpot`（`analysis_models.py:598-605`）；`spot_topics.py:17-78` 读取原生 `SpotData`，无行且 SpotData 空→`RESULT_UNAVAILABLE`（`:65-68`）。
- **实际输入**：Cooke40；三种变体 `(f1,wl1,Centroid,exag1)`、`(f0,wl0,Centroid,exag1)`、`(f1,wl1,ChiefRay,exag3)`；可用性探针另 3 请求。
- **设置采用**：`IsValid=true, IsActiveWindow=true`；Field/Wavelength/Surface 选择与 PlotScale/Exaggerate/DeltaFocus 均按请求回读。
- **结果计数**：`NumberOfDataGrids/Series/ScatterPoints(+Rgb)/RayData/Messages` **全 0**；`SpotData=null`；`native_text_exported=false`。
- **错误**：`RESULT_UNAVAILABLE`（含 native_result_counts）。
- **关闭/恢复**：三次均关闭；surfaces/settings/merit 保持；disconnect ok。
- **等价追迹**：需「有载图形/专属结果出口」**或**「完整 shared-reference/exaggeration 契约」，并声明参考点（Centroid/ChiefRay）、表面局部截点坐标、逐视场分面布局与放大系数；`progress591` 明确记为 next_action，**当前无可验证定义**→具体阻塞。
- **阻塞/解除**：无可用原生出口且无 shared-reference/exaggeration 契约；待有效出口或经验证的等价参考/尺度/布局映射。`numerical_acceptance=false`。

### 4.6 CV-01.MatrixSpot（D004）
- **接口**：`ConfigurationMatrixSpot(kind='matrix_spot', …)`（`analysis_models.py:584-596`）；`analyses.py:633-639` `setv` 设置回读；出口 `GetTextFile`。
- **实际输入**：Cooke40 + 复制配置；请求 `kind=matrix_spot, color_rays_by=Waves`，`DeltaFocus=0` 采用。
- **结果计数/错误**：原生计算有效但 `SpotData=null`、series/grid/scatter 全 0、`GetTextFile=false`→`EXPORT_FAILED`。
- **关闭/恢复**：任务关闭/断开；系统设置与曲面状态不变。
- **等价追迹**：需文档化原生矩阵光斑结果/图形出口，或等价计算声明 pattern/ray_density/reference/color_rays_by 及逐视场/逐配置分面与参考坐标；**无可验证定义**（`probe088`）→具体阻塞。
- **纪律**：`counts_as_completed=false`。

### 4.7 CV-01.ConfigurationMatrixSpot（D004）
- **接口**：`ConfigurationMatrixSpot(kind='configuration_matrix_spot', …)`，同 MatrixSpot 通用路径。
- **实际输入**：Cooke40 + 两配置；请求 `configuration_matrix_spot, color_rays_by=Config`（并以 `matrix_spot, color_rays_by=Waves` 作对照）。
- **结果计数/错误**：两次原生计算均完成但出口空（文本 false、SpotData null、计数 0）→`EXPORT_FAILED`。
- **关闭/恢复**：每次关闭确认；双配置模型保留系统设置与曲面状态；会话正常断开。
- **等价追迹**：需配置→分面映射、参考坐标、光线 pattern 与逐配置布局的可验证声明；**无文档化定义**（`probe088`）→具体阻塞。

## 5. 实际执行的定向检查（无原生；**本轮执行**，与历史原生记录分开）

> 日期/来源分离：本节 169 项为**本会话本轮于 2026-11-08 执行**的普通单元检查（无原生）；第 4 节引用的原生结果均为**历史记录**——`*repeat20261108.md`（先前 pass，2026-11-08 记录）、`progress591`（2026-11-07）、`probe088`（2026-11-06）、`progress282`/`ray-aiming276`（更早受控运行）。两者日期/来源不同，不得互相替代或据历史原生判本轮普通检查通过。

| 文件 | 结果 |
| --- | --- |
| `tests/unit/test_extended_solves.py` | 82 passed |
| `tests/unit/test_conversion.py` | 22 passed |
| `tests/unit/test_design_tools.py` | 39 passed |
| `tests/unit/test_seidel_diagram.py` | 5 passed |
| `tests/unit/test_full_field_spot.py` | 13 passed |
| `tests/unit/test_configuration_matrix_spot.py` | 8 passed |
| **合计** | **169 passed in 0.82 s，0 failed/error** |

命令：`python -B -m pytest <六个文件> -q -p no:cacheprovider --junitxml=.local/coordination/pass-d003-d004-pytest.xml`；逐文件计数与 2026-11-08 记录一致。XML：`.local/coordination/pass-d003-d004-pytest.xml`（36,199 字节，169 testcase，0 failure/error）。

## 6. 风险与未决（交协调者）

1. CV 四项均为「出口空/不可用」，非数值比对；若要关闭需原生补出口或经验证的等价定义（含参考点/坐标/分面）。当前一律记具体阻塞，不以近似图替代验收。
2. SeidelCoefficients 数值通过≠Seidel 图；勿在索引中合并。
3. MaterialModel 有数值但 Abbe 门槛未过（59.999885… vs 60）——若协调者拟放宽门槛须显式裁定；否则按未过处理。
4. NS-01 纯转换 379 项参考为**更早日期**的纯路径证据，非混合组；勿据此判混合组通过。
5. ED-04 执行路径无可靠终态（超时+Close 失败+需重连）；只读 options/close 可用不等于生命周期完成。
6. 全部结论仅覆盖 PremiumEdition 24.2.0 build 240529。
7. 本 worker 为支持角色，未改任一 `pass_state`/台账；统一索引由协调者完成。
