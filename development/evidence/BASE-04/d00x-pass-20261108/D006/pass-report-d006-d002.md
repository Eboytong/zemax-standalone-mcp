# D006 + D002 交付总报告与路径清单（供统一更新台账）

任务：D006 十项短计划与离线结果 → 收紧三处结论 + 补 D002 四项索引
Agent 2（四类材料图表与色散）｜`zemax-p01-material-reports`｜分支 `codex/d002-material-reports`
工作区 `C:\Users\tonge\.codex\worktrees\zemax-p01-material-reports\Zemax_MCP`｜基线 `34e1a18494015c2b383ec700b958015020b660fe`｜源码 0.1.62｜OpticStudio 24.2.0 build 240529 PremiumEdition｜Python 3.14

本轮边界：**未启动原生、未改产品代码、未改公共台账（`development/ledgers/*.csv`）、未改 `d00x-pass` 的 `pass_state`、未提交 Git**。仅修订协调文档、离线脚本与索引，并实际复跑离线检查与单元测试。

---

## 1. 本轮三处结论收紧（按审查意见）

| # | 位置 | 收紧前（过强） | 收紧后（实际可证） |
| --- | --- | --- | --- |
| 1 | `NS-03.SourcePolarViewer` | 矩阵与 `sample.ies` 亮度表「逐格完全相等」，据此暗指「输出=未归一化 IES 表」；`Dy=360/19` 与 20° 不符→暗示 y 轴映射错误 | 只在**本样例（旋转对称输入）**下逐格相等；因 19 个水平切片全同，**不能**证明任意 IES 原始表的发布方式或单位/归一化契约。`Dy=360/19` 与源节点 20° **不同**这一点**仅记录为事实**（可能是原生像素范围/中心约定），**不判为原生映射错误** |
| 2 | `NS-03.SourceIlluminationMap` | 确认 4×`SourceEllipse`+`DetectorColor` 且出口空→据此「排除输入错误」 | 只证明**被检查模型的对象条件**与其出口为空；缺专题输入选择合同时，**不能**据此排除所有输入条件错误 |
| 3 | `CV-01.SourceColorChart1931/1976` | 替代基准（有出处 CIE 轨迹数据）被表述为可补的推进路径 | 替代 CIE 参考**仍需**官方基准**与**原生图形对应证据；本轮**维持原声明**，不以额外独立绘图关闭该项 |

所有实测数值一律保留，未改动任何数字。

---

## 2. D006 十项（2 `implemented` + 8 `blocked`，台账不动）

| 项目 | 产品 kind | 台账 | 本轮判定 |
| --- | --- | --- | --- |
| NS-03.SourceSpectrumViewer | `source_spectrum_viewer` | implemented | 可实现子项=默认 XYZ 拟合报告解析与数值复核（已实现）；可变输入选择缺 |
| NS-03.DirectivityPlot | `directivity_plot` | implemented | 可实现子项=默认报告 + 独立 IES 参考（已复核）；文件/扫描角选择缺 |
| NS-03.FluxvsWavelength | 无 | blocked | 出口为空（报告行 0，仅 BOM） |
| NS-03.SourcePolarViewer | 无 | blocked | 有矩阵，无轴/单位/标签合同；逐格相等仅本样例成立 |
| NS-03.SourceIlluminationMap | 无 | blocked | 仅证明被检查模型对象条件 + 空出口 |
| NS-03.PhotoluminscenceViewer | 无 | blocked | 原生以「输入无效」拒收 |
| NS-03.RadiantSourceModelViewerSettings | 无 | blocked | 许可（旗舰版）+ 匹配源模型缺失 |
| NS-03.RoadwayLighting | 无 | blocked | 无设置接口、无道路模型；静默默认路规待裁定 |
| CV-01.SourceColorChart1931 | 无 | blocked | 无图像/数值出口；替代需官方基准+原生对应 |
| CV-01.SourceColorChart1976 | 无 | blocked | 同上 |

依据：`ANALYSES`（`src/zemax_mcp/analyses.py:8`）仅登记 `source_spectrum_viewer`/`directivity_plot`（`:22`）；类型化请求 `src/zemax_mcp/analysis_models.py:672`、`:675`；解析 `src/zemax_mcp/basic_analyses.py:125`、`:166`；分派 `src/zemax_mcp/analyses.py:859-870`。区分：`src/zemax_mcp/wizards.py:8` 的 `NSCRoadwayLightingWizard` 是评价函数向导，非本分析。

## 3. D002 四项（最新发现逐项索引）

| 项目 | 最新发现 | `analyses.csv` / `operations.csv` | 建议 |
| --- | --- | --- | --- |
| MA-01.GlassMap | **346/346** 大小写归一匹配（目录 365 条 `NM`）；7 项仅拼写差异 | implemented / blocked | 保持；xfail 待改归一比较后解除 |
| MA-01.AthermalGlassMap | **温度 359/364**（≤5e-9，最大 4.9452123175592664e-9）+ **五项资源缺口**（F2HTi 占位 + P-SK57Q1/REALVIEW_2.0/LF5G15/SF66 空 `TD`）；色差 363 行差 0.0；温变扫描无原生证据、产品无环境温度设置口 | implemented / blocked | 保持 implemented，不申报完成 |
| MA-01.DispersionDiagram | 折射率参考 **4.966168343223387e-08 < 5.1e-8**（101 点，0.4–0.8 µm） | implemented / blocked | 保持 |
| MA-01.DispersionvsWavelength | 中心差分 **99 点最大 3.4899999992843433e-05 < 5e-5**；**解析导数 4 点超限**（0.408/0.416/0.432/0.488 µm，最大 5.9190213202997555e-08 > 5.1e-8，保留为诊断） | implemented / blocked | 保持 |

四项共同缺口：**正式专题选择仍缺**——均以 `AS_Default` 运行，只回读 `IsValid`/`IsActiveWindow`；唯一正式选择是系统级 `update_system_settings(material_catalogs=[...])`。`operations.csv` 四项 `blocked` 与 `analyses.csv` 的 `implemented` 不一致，**留待协调者裁定**，本 worker 不统一。

---

## 4. 路径清单（全部为本轮实际产出或复用）

### 4.1 本轮新建 / 修订（工作区 `.local/coordination/`）

| 文件 | 用途 |
| --- | --- |
| `pass-d006-plan.md` | D006 十项逐项短计划（已按审查收紧 §3/§4.4-4.7/§5/§7/§8） |
| `pass-d006-items.json` | D006 十项机器可读索引（含 `scope_revisions`，数值未改） |
| `d006-offline.py` | D006 离线复算脚本（无 ZOS-API；极坐标检查更名 `source_polar_sample_correspondence`，结论限域） |
| `d006-offline.out.json` | 上述 9 项检查结果（`failed_checks=[]`） |
| `pass-d002-reports-items.json` | **新建**：D002 四项逐项索引（含数值、容差、缺口、诊断、正式选择缺口） |
| `pass-report-d006-d002.md` | **本总报告 + 路径清单** |

### 4.2 D002 既有证据（本轮复用，未改动）

| 文件 | 用途 |
| --- | --- |
| `final-report.md` | D002 最终报告（公式、359/364、缺口、风险） |
| `athermal-reference-plan.md` | 无热参考与温度语义计划 |
| `athermal-reference.py` / `athermal-reference.out.json` | 无热离线参考与比较输出 |
| `athermal-gaps.json` | 六项缺口原目录行/原生行 |
| `offline-check.py` / `offline-check.out.json` | GlassMap 346/346 与色散 101/99 点离线检查 |
| `native-jobs.json` | 原生作业单（6 条，`executed_this_round=false`） |
| `implementation-report.md`、`plan.md` | D002 实施与计划存档 |

### 4.3 测试工件（工作区，未提交）

| 文件 | 用途 |
| --- | --- |
| `tests/support/athermal_reference.py` | 无热/色散纯函数参考（`ValueError` 统一校验） |
| `tests/unit/test_athermal_reference.py` | 40 项参考检查 |
| `tests/support/material_catalog_reference.py` | 目录大小写归一参考 |
| `tests/unit/test_material_reports_reference.py` | 四项报告参考检查（含 `LF5HTi` 归一） |

### 4.4 主项目证据（只读，未改）

`development/evidence/NS-03/**`（D006）、`development/evidence/CV-01/**`（色度图）、`development/evidence/MA-01/**`（D002）、`.local/evidence/development/{NS-03,CV-01,MA-01}/**`（运行证据）；
权威计划 `development/tracking/d00x-pass-20261108.json`；台账 `development/ledgers/analyses.csv`、`operations.csv`。

---

## 5. 本轮实际执行的检查与结果

| 命令 | 结果 |
| --- | --- |
| `python -B .local/coordination/d006-offline.py` | **9/9 通过**，`failed=[]`；键：`directivity_angles, directivity_flux, source_spectrum, flux_outlet, source_polar_grid, source_polar_sample_correspondence, illumination_condition, roadway_reports, product_interface` |
| `python -B .local/tmp/verify_index.py` | `pass-d002-reports-items.json` 全部数值与 `offline-check.out.json` / `athermal-reference.out.json` **逐项一致**（GlassMap 计数/SHA、色散 101/99 点与 4 个超限波长、无热 359/364/中位数/色差 363、五项缺口名与原生热光值） |
| `python -B -m pytest tests/unit/ -q -p no:cacheprovider` | **2645 passed**（全量单元） |
| `python -B -m pytest tests/unit/test_yni_contributions.py tests/unit/test_wizards.py tests/unit/test_basic_analyses.py tests/unit/test_contracts.py -q -p no:cacheprovider` | **105 passed**（D006 相关普通回归） |

关键保留数值：
- 方向性 37 点最大角差 `4.44444444444025e-05` ≤ 5.1e-5；梯形通量 `112.81009451201489 lm`（原生 112.81，差 `9.45e-05`）
- 光谱 20 行 0.44–0.64 µm、峰值 1、XYZ `[1,1,1]`、CRI `70.1766`、CCT `5188 K`
- 极坐标 19×19、`Dx=10.0`、`Dy=18.94736842105263`、标签 `None`；本样例逐格相等
- 通量随波长：报告行 `0`、导出字符 `0`、`text_export=true`
- 照明：4×`SourceEllipse` + 1×`DetectorColor`，结果计数全 0
- 道路：模型 `Two color mixing gives white` vs `Fluorescent scattering in a bulk medium`；`Lavg` `1.74981e-06`→`0`、`SR` `3.47391`→`0`

---

## 6. 风险与未决

1. `SourcePolarViewer`：逐格相等仅本样例（旋转对称）；不能推断其它源，也不能确定原生发布/单位/归一化契约；`Dy=360/19` vs 20° 只作事实记录。
2. `SourceIlluminationMap`：空结果只覆盖被检查模型；未检查的输入条件无法排除。
3. 色度图替代基准：仍需官方基准 + 原生图形对应证据，本轮未关闭。
4. 无热 5 项数据缺口（空 `TD` / 占位系数）未验收；若要求全覆盖，需先解除官方默认语义。
5. 温变路径无原生证据且产品无环境温度设置口（`SystemPatch` `src/zemax_mcp/models.py:186` 无温度字段；`backend.py:749` 只读；仅 MCE `TEMP` `src/zemax_mcp/universal_configuration.py:17`）；作业 `ma01-athermal-temperature-sweep` 为 `not_executable_this_pass`，**不替代** 359/364。
6. 色散解析导数 4 点超限仅诊断（原生差分步长/算法未定义），不作验收依据。
7. 全部结论仅覆盖 PremiumEdition 24.2.0 build 240529；旗舰版行为未验证。

## 7. 待协调者决定

1. 两项 CIE 色度图：替代路径是否必须先具备「官方基准 + 原生图形对应证据」再启用（本轮按此保持未关闭）。
2. `SourcePolarViewer`：`Dy=360/19` 与 20° 不同，是否登记为「待解释的像素范围/中心约定」观察项（**非缺陷**）。
3. `RoadwayLighting`：无道路输入时静默返回默认路规指标，是否按缺陷登记。
4. D006 是否按「2 `implemented` + 8 `blocked`」结账；D002 四项 `operations.csv` 是否维持 `blocked`（与 `analyses.csv` 的 `implemented` 不一致由协调者裁定）。
