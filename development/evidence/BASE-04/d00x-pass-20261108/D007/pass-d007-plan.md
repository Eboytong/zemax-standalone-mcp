# D007 逐项计划：散射模型与杂散光路径（6 项）

- 开发组：**D007**（`development/current.md` D007 段；`development/tracking/d00x-pass-20261108.json` 中 `development_group=="D007"` 共 6 项）
- 权威来源：主项目 `C:/Users/tonge/Desktop/Zemax_MCP/development/`（本冻结工作区无 `tracking/d00x-pass-20261108.json`）
- 本 worker 负责顺序（按 pass 文件顺序）：`ED-01.Scattering.BSDF` → `ED-01.Scattering.ISScatterCatalog` → `NS-03.ScatterFunctionViewer` → `NS-03.ScatterPolarPlotSettings` → `NS-02.PathAnalysis` → `ED-01.Scattering`
- 公共台账只读；本轮不启动原生（`application_create` 180 s 超时 ×3 已登记外部阻塞）
- 源码改动仅在本 worker 工作区

## 0. 组内共同点（先说明，避免逐项重复）

- 散射类型/资源选择已有 typed 适配：`src/zemax_mcp/scattering_pages.py`（`NoScatter|Lambertian|Gaussian|ABg|ABgFile|BSDF|User|Catalog`，`RESOURCES` 映射 `GetAvailableABgNames`/`GetAvailableFileNames`/`GetAvailableDLLNames`/`GetAvailableFiles`），写入统一走 `ChangeScatteringTypeSettings` + 回读。
- 路径分析已有 typed 入口：`src/zemax_mcp/path_analysis.py` + `path_models.py`（`kind='path_analysis'`，`ANALYSES['path_analysis']='PathAnalysis'`）。
- 两个 viewer（`ScatterFunctionViewer`/`ScatterPolarPlotSettings`）**没有** typed 入口，台账为 `blocked`，原因是"静态设置接口缺失、运行时发现待初始化"。
- 已有普通测试：`tests/unit/test_scatter_report.py`(0.8 KB)、`tests/unit/test_path_analysis.py`(9.4 KB)、`tests/unit/test_property_pages_adoption.py`；原生用例：`tests/native/test_finite_scatter_live.py`、`test_multievent_scatter_live.py`、`test_scattering_reference_live.py`、`tests/support/scatter_reference.py`。
- 外部阻塞（组级）：本机 BSDF 资源枚举只返回占位值"无"；无 ISX 目录数据文件；`IsSTARModuleEnabled=false` 与散射无关但与 D012 相关。

## 1. ED-01.Scattering.BSDF（BSDF 文件选择）

- **当前正式接口**：`IAS_SurfaceScattering`/`IAS_Scattering` 分支 `BSDF`，资源枚举 `GetAvailableFileNames()`；写入 `BSDF` 文件名后 `ChangeScatteringTypeSettings` 返回 true。
- **已有输入/结果**：本机枚举仅返回占位值"无"；写入 `BrownVinyl.bsdf` 与绝对路径后 `FileName` 仍为占位值 → 台账 `blocked`，证据 `development/evidence/ED-01/bsdf-resource-selector-probe20261108.md`。
- **可离线补齐**：① 资源名与"占位值"判定（`无`/`None`/空）显式建模为 `RESOURCE_PLACEHOLDER` 而非有效选择；② 选择未采用时给出 `SETTING_REJECTED` 且保留请求与回读对照；③ 单元测试覆盖"枚举为空/占位/真实名"三态与回读不一致。
- **实际检查**：`pytest tests/unit/test_property_pages_adoption.py tests/unit/test_scatter_report.py -q`（现有）。新增：占位值三态 + 未采用拒绝。
- **外部阻塞**：本机无真实 BSDF 资源可供枚举采用（环境/许可资源缺失，非代码）。
- **解除条件**：`GetAvailableFileNames` 返回真实 BSDF 名，且写入后 `FileName` 回读等于请求值；随后做追迹 + 保存/重载。

## 2. ED-01.Scattering.ISScatterCatalog（散射目录有效数据）

- **当前正式接口**：分支 `ISScatterCatalog`，`GetAvailableFiles()` + `GetFile()`；`ChangeScatteringTypeSettings` 采用。
- **已有输入/结果**：台账 `blocked`，解除条件写明需"documented ISX data file with matching catalog entry"，证据 `verification/property-pages017-summary.json` 等。
- **可离线补齐**：① `file_name` 与目录条目的匹配校验（大小写、扩展名 `.isx`）在适配层显式化；② 缺文件/目录项不匹配时的错误码与信息（不吞异常）；③ 单元测试覆盖匹配/不匹配/缺文件。
- **实际检查**：新增上述单元测试；`tests/unit/test_property_pages_adoption.py` 回归。
- **外部阻塞**：本机无 ISX 数据文件与其目录条目（资源缺失）。
- **解除条件**：安装受控 ISX 文件 + 目录条目；启动恢复后验证选择、参数、追迹、保存/重载。

## 3. NS-03.ScatterFunctionViewer（散射函数查看器）

- **当前正式接口**：`AnalysisIDM.ScatterFunctionViewer` 存在；运行时设置对象只暴露 `IAS_` 基类（`IsValid`/`IsActiveWindow` 等），**无**正式曲线/网格/图像出口。
- **已有输入/结果**：ABg 样例对象 2/面 0 回读为 ABg 及 `ABG-EXAMPLE`；任务结果仍无数据、文本导出失败；设置对象**拒绝** `ScatterFraction` 属性 → 台账 `blocked`。
- **可离线补齐**：① 只读反射测试：确认该分析设置对象的属性面（防止未来版本新增选择器而漏接）；② 结果为空时的分层（`NO_RESULT_DATA` 而非成功空表）；③ 与 `scattering_pages` 的采用参数一致性校验（请求的 ABg 与回读 ABg 对照）。
- **实际检查**：新增反射/空结果分层单元测试（合成对象）；原生作业见 items JSON。
- **外部阻塞**：无正式曲线/图像出口；`ScatterFraction` 属性被拒（正式接口缺失）。
- **解除条件**：出现正式曲线/网格/图像出口与可写 `ScatterFraction`（或文档化等价键）。

## 4. NS-03.ScatterPolarPlotSettings（散射极坐标图）

- **当前正式接口**：`AnalysisIDM.ScatterPolarPlotSettings` 存在；设置为 `IAS_` 基类，无角度映射/单位属性；`GetTextFile=false`。
- **已有输入/结果**：ABg 与 Lambertian（`ScatterFraction=1`）对照均返回 181×90 常数 1/π；轴与值标签为 None → 台账 `blocked`。
- **可离线补齐**：① "常数网格"检测（全等值）→ 标记 `degenerate_grid` 而非当作有效结果；② 缺轴标签/单位时返回 `INVALID_RESULT_DATA` 并保留原始网格；③ 单元测试覆盖常数网格与正常网格。
- **实际检查**：新增上述单元测试。
- **外部阻塞**：无正式角度映射/单位，结果不随散射模型变化（正式接口缺失）。
- **解除条件**：出现正式角度/单位接口，且结果随散射模型变化可对照。

## 5. NS-02.PathAnalysis（路径分析）

- **当前正式接口**：`kind='path_analysis'` → `AnalysisIDM.PathAnalysis`；结果读 `PathAnalysisData`；分类/未分类行解析已实现。
- **已有输入/结果**：普通 36 项通过；原生阈值 1 实验复现失败：分类行全被筛除，`GetPathUncategorized` 仍称无未分类路径；独立 ZRD 入口功率约 0.8–0.99 W。台账 `implemented`，证据 `development/evidence/NS-02/path-analysis-uncategorized*.md`。
- **可离线补齐**：① 分类行筛选与未分类计数的自洽校验（二者相加应等于总行数，否则 `INVALID_RESULT_DATA`）；② 功率缺失时的显式字段而非 0；③ 单元测试覆盖"全部被筛除"的不自洽场景。
- **实际检查**：`pytest tests/unit/test_path_analysis.py -q`（现有 9.4 KB 用例）+ 新增自洽校验用例。
- **外部阻塞**：无正式"剔除功率"出口；供应方分类定义未知。
- **解除条件**：官方剔除功率出口或供应方分类定义文档化。

## 6. ED-01.Scattering（内建散射类型与资源查询，组项）

- **当前正式接口**：`Scattering` 联合类型 + `RESOURCES` 资源枚举映射；`ChangeScatteringTypeSettings` 采用。
- **已有输入/结果**：台账 `implemented`（"已验内建类型保留"），下一步"补 BSDF 文件实际选择、ISScatterCatalog 匹配 ISX 输入、追迹及重载"。
- **可离线补齐**：① 联合类型全成员的类型/资源矩阵测试（每个类型可构造、资源名映射正确、未知类型拒绝）；② `RESOURCES` 与实际属性名一致的断言。
- **实际检查**：新增矩阵单元测试；`tests/unit/test_scatter_report.py` 回归。
- **外部阻塞**：追迹/重载需真实 BSDF/ISX 资源（同 1、2）。
- **解除条件**：1、2 的资源条件满足后，本项补追迹与重载证据即可收口。

## 7. 汇总：离线 vs 原生

| 项 | 可离线 | 需原生 |
| --- | --- | --- |
| BSDF | 占位值/未采用拒绝、三态测试 | 真实 BSDF 名枚举与采用、追迹、重载 |
| ISScatterCatalog | 匹配校验、缺文件分层 | ISX 文件与目录条目、追迹、重载 |
| ScatterFunctionViewer | 反射面记录、空结果分层、参数一致性 | 正式结果出口（缺失） |
| ScatterPolarPlotSettings | 常数网格检测、缺标签分层 | 角度/单位接口（缺失） |
| PathAnalysis | 分类/未分类自洽校验、功率缺失表达 | 剔除功率出口或供应方定义（缺失） |
| Scattering | 类型/资源矩阵测试 | 依赖 1、2 的资源条件 |

## 8. 完成条件（不降容差）

- 每项：请求可构造、采用值回读一致、失败有分层码且保留原始结果、模型前后一致、任务终态与关闭证据齐全。
- 数值项沿用既有门槛（不新增放宽）：路径分析行数与分类计数必须自洽；散射网格不得以常数占位通过。
- 资源类阻塞：保存具体证据（枚举输出、写入回读对照）与解除条件，不登记为代码缺陷。

## 9. 下一步

1. 本计划与 `pass-d007-items.json` 交审查
2. 审查通过后按 §1→§6 顺序实施离线部分（每项一个短分支提交），原生部分排队
3. 每项完成后回填证据索引，未闭合项保留具体解除条件

## 10. 最终状态（2026-11-08 收尾，离线）

- 实现已落地：`scatter_capabilities.py`（转储事实表 + 占位/能力/资源校验）、`scattering_pages.py`（`resource_names` 占位过滤、`set_scattering` 真实复用 `require_resource`/`catalog_diagnostics` 并采用原生精确名）、`tests/unit/test_scatter_capabilities.py`（33 项，含真实 `resource_names`/`set_scattering` 路径）。
- 占位值收窄为 `{'', '无', 'none'}`（有据），`n/a`/`null`/`-` 不纳入以免误拒合法 ABg 名。
- 聚合项 `ED-01.Scattering` 范围＝原生内建散射类型与资源查询；剩余仅 **BSDF 与 ISX 的原生选择/追迹/重载**。
- `ED-01.Scattering.User` 已按 `development/tracking/scope.json`（`excluded_item_ids`，理由“自定义代码、宏、宿主或DLL扩展”）移出计划；其 `CreateScatteringTypeSettings`/`UILDEScatterData` 序列化异常仅作为既有产品/历史诊断保留，**不作本聚合项完成前置**。
- NS-03.ScatterPolarPlotSettings：历史已返回 181×90 常数 1/π 网格，**缺角度/单位与模型响应参考**，不写“无结果出口”。
- 台账（`development/ledgers/operations.csv`）范围＝“原生内建散射类型与资源查询”，本计划不越界。
