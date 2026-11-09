# D007 实施与审计报告：散射模型与杂散光路径（6 项）

- 组：D007；权威清单 `C:/Users/tonge/Desktop/Zemax_MCP/development/tracking/d00x-pass-20261108.json`（`development_group=="D007"`，6 项，未变）
- 本轮：实际审计 + 可执行开发（非仅计划）；原生新启动延后；未改公共台账；未提交 Git
- 复用的正式资料（只读）：`verification/development/BASE-01/probe/api-interfaces.json`（原生反射转储）、`development/ledgers/operations.csv`、`development/evidence/ED-01/`、`development/evidence/NS-02/`、`development/evidence/NS-03/`

## 1. 逐成员审计：谁真正承载散射设置（转储实证）

扫描转储中所有含 `Scatter*` 成员的类型，得出本机实际成员表：

| 宿主 | 成员 | 结论 |
| --- | --- | --- |
| `ISurfaceScatteringNone/Lambertian/Gaussian/ABg/ABgFile/BSDF/User/Catalog` | 类型专属设置对象 | LDE 散射八类齐备 |
| `Lambertian`/`Gaussian`/`BSDF` | `ScatterFraction` | **有**散射比例属性 |
| `ABg`/`ABgFile`/`User`/`ISScatterCatalog` | 无 `ScatterFraction` | **没有**该属性（此前"设置对象拒绝 ScatterFraction"的现象由此得到解释） |
| `ISurfaceScatteringBSDF` | `GetAvailableFileNames()` | BSDF 资源查询 |
| `ISurfaceScatteringUser` | `DLLName`、`NumberOfParameters`、`GetAvailableDLLNames()`、`GetParameterName/Value`、`SetParameterValue` | User 散射资源与参数 |
| `ISurfaceScatteringCatalog` | `Angle`、`SampleSide`、`Sampling`、`GetFile()`、`SetFile(String)`、`GetAvailableFiles()` | IS 目录选择 |
| `ISurfaceApertureFloating` | **0 属性、0 方法** | 本构建中浮动光阑**不是**散射宿主，不能经其设置散射模型或比例 |
| 9 个分析设置（`IAS_Spot`、`IAS_GeometricMtf`、`IAS_GeometricMtfMap`、`IAS_GeometricMtfvsField`、`IAS_GeometricThroughFocusMtf`、`IAS_DiffractionEncircledEnergy`、`IAS_GeometricEncircledEnergy`、`IAS_GeometricImageAnalysis`、`IAS_NSCSingleRayTrace`） | `ScatterRays` / `ScatterNSCRays` | **分析宿主**：仅"是否使用散射光线"开关，不是散射模型定义 |
| `ILDEScatteringData` | `CurrentType`、`CreateScatteringTypeSettings`、`ChangeScatteringTypeSettings` | 写入通道 |

NCE 侧另有 `IOSS_*`/`INCECoatScatter*` 一套，属非序列编辑器，**不在** D007 顺序散射范围，未纳入实现。

以上事实已编码为 `src/zemax_mcp/scatter_capabilities.py`，并由 `tests/unit/test_scatter_capabilities.py::test_type_interface_and_resource_map_match_the_dump` 等 4 个"转储同步测试"强制执行：版本漂移会使测试失败，而不是让适配层静默失真。

## 2. 本轮代码改动

| 文件 | 改动 | 性质 |
| --- | --- | --- |
| `src/zemax_mcp/scatter_capabilities.py`（新） | 反射事实数据表 + `is_placeholder`/`valid_names`/`require_capability`/`require_resource`/`catalog_diagnostics` | 新增 |
| `src/zemax_mcp/scattering_pages.py` | `resource_names` 占位值过滤（全类型）+ 空资源显式 `UNSUPPORTED_SETTING`；`set_scattering` 真实复用 `require_resource`（非目录）与 `catalog_diagnostics`（目录，采用原生精确名） | 修正 |
| `tests/unit/test_scatter_capabilities.py`（新，33 项） | 转储同步、占位值、资源匹配、能力守卫、目录诊断，以及**真实 `resource_names`/`set_scattering` 路径**（写前失败、精确名采用、回读、原始错误保留） | 新增 |
| `tests/support/analysis_scenarios.py` | `prescription_data`/`surface_data` 归入 SPECIALIZED（kind-only 契约） | 修正 |
| `tests/native/test_native_text_reports_live.py`（新） | D008-R1/R2 原生作业（仅准备） | 新增 |

**修正的真实缺陷**：`resource_names` 原先把 `无` 这类占位值当作可用资源返回，使 `INVALID_RESOURCE` 分支永远不触发。现在占位值被单独识别，纯占位枚举直接 `UNSUPPORTED_SETTING` 并带 `placeholder_values`/`native_names`。

### 占位值集合的实证来源（只保留有证据的三类）

`PLACEHOLDERS = {'', '无', 'none'}`，不做推测性扩展：

| 值 | 来源 |
| --- | --- |
| `''`（空串） | 选择器无条目时的空返回（`bsdf-resource-selector-probe20261108.md` 观测到空/占位返回） |
| `无` | `development/evidence/ED-01/bsdf-resource-selector-probe20261108.md` 明确观测到的字面值 |
| `none` | 适配层对 .NET `null` 调用 `str(None)` 的结果（`is_placeholder` 用 `casefold` 匹配，覆盖 `None`） |

`n/a`、`na`、`null`、`-` **无原生或正式文档依据**，已从集合移除并显式测试为"非占位"（`test_real_names_are_not_placeholders`），以免把可能合法的 ABg/目录名误拒。

### 能力表的实际消费者（不是仅供镜像转储）

`scatter_capabilities` 仅被以下真实路径导入，无纯镜像死函数：

- `src/zemax_mcp/scattering_pages.py::resource_names`：`is_placeholder`/`valid_names`（占位过滤）。
- `src/zemax_mcp/scattering_pages.py::set_scattering`：`require_capability`（类型与 `ScatterFraction` 前置）、`require_resource`（ABg/ABgFile/BSDF/User 资源校验并返回原生精确名）、`catalog_diagnostics`（目录命中与精确名）。
- `tests/unit/test_scatter_capabilities.py`：4 个转储同步测试 + 真实路径测试。

即 `require_resource` 与 `catalog_diagnostics` 都已在 `set_scattering` 真实调用；目录匹配成功时 `vals['file_name']` 被替换为 `diagnostics['matched_name']`，`SetFile` 用的是原生精确大小写，避免 `GetFile()` 回读因大小写不一致而冲突（`test_set_scattering_catalog_uses_the_exact_native_name`）。

## 3. 逐项状态

### ED-01.Scattering.BSDF — blocked（资源）
- 接口：`ISurfaceScatteringBSDF.FileName` + `GetAvailableFileNames()`。
- 已有证据：`development/evidence/ED-01/bsdf-resource-selector-probe20261108.md`（枚举只返回 `无`；写入 `BrownVinyl.bsdf` 后 `FileName` 仍为占位值）。
- 本轮完成：占位值检测 + `.bsdf`/`.abgf` 判别 + 三态错误分层，均有测试。
- 剩余：本机仍需真实 BSDF 资源。解除条件：`GetAvailableFileNames` 返回真实名且回读一致 → 追迹 + 保存/重载。

### ED-01.Scattering.ISScatterCatalog — blocked（资源）
- 接口：`GetAvailableFiles()`/`GetFile()`/`SetFile()`，已由适配层写入并回读比对。
- 本轮完成：占位值过滤 + `catalog_diagnostics`（是否命中、后缀是否 `.isx`、可用清单），**不**新增硬规则以免臆造格式约束。
- 剩余：无 ISX 数据文件与目录条目。解除条件：安装受控 ISX 后验证选择/参数/追迹/重载。

### NS-03.ScatterFunctionViewer — blocked（正式接口）
- 接口：分析枚举存在；设置对象仅 `IAS_` 基类（`IsValid`/`IsActiveWindow`/`Parent`），无曲线/网格/图像出口。
- 本轮完成：把"哪些类型有 `ScatterFraction`"变成可断言事实，排除"以为能通过该分析设置比例"的误判。
- 剩余：无正式结果出口。解除条件：出现曲线/网格/图像出口。

### NS-03.ScatterPolarPlotSettings — blocked（结果含义未确认）
- 已有实证：ABg 与 Lambertian 对照均返回 **181×90 网格**（常数 1/π），轴与值标签为 None，`GetTextFile=false`。
- 事实修正：该分析**不在** `ScatterRays` 宿主表中（转储无该属性），这只说明**不能走散射开关路径**解释该网格，**不足以**推断"结果出口缺失"——网格本身已经返回。
- 当前准确表述：已返回 181×90 网格，但**角度（θ/φ 映射）、单位与"常数值"的模型归属均未确认**；现有证据无法区分"真实但未标注的极坐标网格"与"占位常数网格"。
- 解除条件：出现正式角度/单位映射，且结果随模型（如散射类型或参数）变化。

### NS-02.PathAnalysis — implemented（部分）
- 接口/入口：`kind='path_analysis'` → `AnalysisIDM.PathAnalysis`，结果 `PathAnalysisData`。
- 已有：普通测试通过；原生阈值 1 未复现（分类行全被筛除、`GetPathUncategorized` 称无未分类；独立 ZRD 入口 0.8–0.99 W）。
- 本轮：未改实现（无新证据改变判定），保留为已实现但原生验收待解除。
- 剩余：官方剔除功率出口或供应方分类定义。

### ED-01.Scattering — blocked（组项；范围＝原生内建散射类型与资源查询）
- 范围依据：`development/tracking/scope.json` 将 `ED-01.Scattering.User` 列入 `excluded_item_ids`（理由“自定义代码、宏、宿主或DLL扩展”）；`development/ledgers/operations.csv` 中 `ED-01.Scattering` 的范围为“原生内建散射类型与资源查询”，验收限当前内建散射范围的类型/参数回读、几何追迹和保存重载。
- 本轮完成：内建类型的类型/接口/资源/能力矩阵全部落到可执行断言；`ISScatterCatalog`（内建目录资源查询）与 BSDF/ABg 资源路径均有测试覆盖。
- 聚合项剩余：**仅 BSDF 与 ISX 的原生选择/追迹/重载**（见上两项）。
- **User 归属（不列为完成前置）**：`ED-01.Scattering.User` 已按 `scope.json` 移出计划，故**不**作为本聚合项的前置条件。其既有产品/历史诊断仍如实保留：`ScatteringData.CreateScatteringTypeSettings(User)` 抛 `.NET SerializationException`，根因 `ZemaxUI.Editors.UILDEScatterData` 未标记可序列化，堆栈经 `IZOSAPI_LDETools.GetParamData(rowIndex, dllName)` → `ZOSAPI_ScatteringTypeSettings.GetParamData()` → `CreateScatteringTypeSettings()`；`_S_User` 为 `None`，无法读取 `GetAvailableDLLNames()`/参数；`get_system_resources(scattering_files, User)` 在工厂处失败并返回 `UNSUPPORTED_SETTING`+`stage=CreateScatteringTypeSettings`。
  - 诊断复现证据（既有）：`development/evidence/ED-01/user-scatter-factory-probe20261108.md`；原始运行 `.local/runs/runs/user_scatter_20261108_051001/probe.json`（`finally` 关闭，`native_closed=true`，模型修订保持初始化后的 1）。
  - 该诊断的解除条件（仅作为产品能力记录）：OpticStudio 提供可创建/读取 `ISurfaceScatteringUser` 的正式接口且 `GetParamData` 不再因 `UILDScatterData` 序列化失败。此条件**不影响** D007 聚合项完成判定。

## 4. 实际执行的命令与回执（本轮定向，无全量、无原生）

```
C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe -B -X utf8 -m pytest \
  tests/unit/test_star_analyses.py tests/unit/test_analysis_scenarios.py \
  tests/unit/test_scatter_capabilities.py tests/unit/test_plotting_units.py \
  tests/unit/test_imaging.py tests/unit/test_scatter_report.py \
  tests/unit/test_property_pages_adoption.py -q -p no:cacheprovider
→ 225 passed in 1.91s
```

`tests/unit/test_scatter_capabilities.py` 新增 6 个真实路径用例（`resource_names` 纯占位拒绝、`set_scattering` 纯占位写前失败、未知资源写前失败、BSDF 精确大小写采用、目录精确名采用、未知目录文件拒绝），均断言"写前失败"（`ChangeScatteringTypeSettings` 调用次数为 0）与"原始错误/回读不丢失"。

**发现的真实回归**（历史，已修）：加入 D008 的 kind-only 条目后，`tests/unit/test_analysis_scenarios.py` 对 `surface_data` 失败——`cooke_request` 因 `kind.startswith('surface_')` 注入了 `surface=1`，被 kind-only 模型拒绝。按既有 SPECIALIZED 机制修复（`prescription_data`/`surface_data` 归入专用路由并给出理由）。

## 5. 剩余范围与解除条件汇总

| 项 | 剩余范围 | 类型 | 解除条件 |
| --- | --- | --- | --- |
| BSDF | 真实资源选择、追迹、重载 | 资源 | 枚举返回真实 BSDF 名且回读一致 |
| ISScatterCatalog | ISX 选择、追迹、重载 | 资源 | 受控 ISX 文件与目录条目 |
| ScatterFunctionViewer | 结果出口 | 正式接口 | 曲线/网格/图像出口 |
| ScatterPolarPlotSettings | 已返回 181×90 常数 1/π 网格；缺角度/单位与模型响应参考 | 结果含义 | 正式角度/单位映射且结果随模型变化 |
| PathAnalysis | 剔除功率/分类定义 | 正式接口 | 官方出口或供应方定义 |
| Scattering（组项） | 仅 BSDF 与 ISX 的原生选择/追迹/重载 | 资源 | BSDF 真实名回读一致；受控 ISX 文件与目录条目 |

## 6. 风险

- 转储是 2026-11-06 采集；若版本升级，同步测试会失败（这是设计意图），需重新采集而非放宽断言。
- `ISurfaceApertureFloating` 为空接口可能只是转储不完整；本报告只声明"本构建反射为空"，未推断原生一定不支持。
- `catalog_diagnostics` 只做诊断不做硬规则；目录匹配用 `casefold`，命中时采用原生精确名，未命中只报 `INVALID_RESOURCE` + 可用清单。
- 占位值集合刻意收窄到 `''`/`无`/`none`；`n/a`/`null`/`-` 无依据不纳入，宁可让合法名通过也不误拒。
- 原生未运行，故 BSDF/ISX/两 viewer/PathAnalysis 均无本轮新原生证据；User 序列化异常为既有产品/历史诊断，且 `ED-01.Scattering.User` 已按 `scope.json` 移出计划，不作为本聚合项完成前置。
