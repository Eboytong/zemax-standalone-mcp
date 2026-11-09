# D006 光源、光谱、色度与照明 — 逐项短计划

- 日期：2026-11-08
- worker：`zemax-p01-material-reports`（Agent 2，四类材料图表与色散）
- 工作区：`C:\Users\tonge\.codex\worktrees\zemax-p01-material-reports\Zemax_MCP`
- 分支 `codex/d002-material-reports`，基线 `34e1a18494015c2b383ec700b958015020b660fe`，源码 0.1.62
- 权威计划：主区 `development/tracking/d00x-pass-20261108.json`（D006 十项全部指派给本 worker）
- 依赖组定义：`development/tracking/development-groups.json` → D006「光源、光谱、色度与照明」
- 前置：D002 四项材料图表的本轮收口已交回审查（`.local/coordination/final-report.md`、`athermal-reference-plan.md`、`native-jobs.json`）

## 0. 本轮边界（不改动项）

1. 不改产品代码：本轮是计划与证据索引，代码改动留待协调者批准后的实施轮。
2. 不改公共台账：`development/ledgers/analyses.csv`、`operations.csv` 保持现状（D006 十项为 2 `implemented` + 8 `blocked`），由协调者更新。
3. 不改 `d00x-pass-20261108.json` 的 `pass_state`。
4. 不启动原生：本轮无任何 ZOS-API 调用，全部检查为离线复算。
5. 不提交 Git、不发行。

## 1. 正式接口盘点（实际读源码得出）

| 项目 | 产品类型请求 | 正式设置 | 正式结果出口 | 台账状态 |
| --- | --- | --- | --- | --- |
| NS-03.SourceSpectrumViewer | **有** `source_spectrum_viewer` | 仅 `AS_Default`（`IsValid`/`IsActiveWindow`） | 原生文本报告（`GetTextFile`），解析器已实现 | `implemented` |
| NS-03.DirectivityPlot | **有** `directivity_plot` | 仅 `AS_Default` | 原生文本报告，解析器已实现 | `implemented` |
| NS-03.FluxvsWavelength | 无 | 仅 `AS_Default` | 空（文本仅 2 字节 BOM） | `blocked` |
| CV-01.SourceColorChart1931 | 无 | 仅 `AS_Default` | 无（零集合、`GetTextFile=false`） | `blocked` |
| CV-01.SourceColorChart1976 | 无 | 仅 `AS_Default` | 无（同上） | `blocked` |
| NS-03.SourcePolarViewer | 无 | 仅 `AS_Default` | 19×19 网格，标签全 `None`，`GetTextFile=false` | `blocked` |
| NS-03.SourceIlluminationMap | 无 | 仅 `AS_Default` | 空（零集合，`GetTextFile=false`） | `blocked` |
| NS-03.PhotoluminscenceViewer | 无 | 仅 `AS_Default` | 原生报「无效数据/设置」，零集合 | `blocked` |
| NS-03.RadiantSourceModelViewerSettings | 无 | 仅 `AS_Default` | 原生报需旗舰版，零集合 | `blocked` |
| NS-03.RoadwayLighting | 无 | 仅 `AS_Default`（无可写/可回读专题设置） | 文本报告有指标，但输入非道路模型 | `blocked` |

判定依据：

- 十项中只有两项进入产品分派表 `src/zemax_mcp/analyses.py:8` 的 `ANALYSES`（映射见 `:22`：`"source_spectrum_viewer":"SourceSpectrumViewer"`、`"directivity_plot":"DirectivityPlot"`），并在 `src/zemax_mcp/analyses.py:859-870` 接了解析器。
- 类型化请求只有两个：`src/zemax_mcp/analysis_models.py:672`（`SourceSpectrumViewer`）、`:675`（`DirectivityPlot`）。
- 解析器：`src/zemax_mcp/basic_analyses.py:125`（`parse_source_spectrum`）、`:166`（`parse_directivity_plot`）。
- 其余八项在 `ANALYSES` 中无对应 kind，产品**无法发起**，只是历史上用通用分析对象探过的原生主题。
- 需区分的同名物：`src/zemax_mcp/wizards.py:8` 的 `roadway='NSCRoadwayLightingWizard'` 是**评价函数向导**，与 NS-03.RoadwayLighting **分析**不是同一功能；`src/zemax_mcp/nsc_models.py:36` 的 `PhotoluminescenceModel` 是**物体模型**枚举，不是荧光查看器分析。

## 2. 复用材料清单（全部为只读输入）

| 材料 | 路径 | 用途 |
| --- | --- | --- |
| 光谱原生报告 | 主区 `…/.local/evidence/development/NS-03/source-spectrum-20261108/spectrum.txt` | 20 点光谱、XYZ、CRI、CCT 的离线复算 |
| 方向性原生报告 | `…/NS-03/directivity-20261108/directivity.txt` | 37 点角度曲线、峰值 18 cd、通量 112.81 lm |
| IES 源文件 | `C:/Users/tonge/Documents/Zemax/Objects/Sources/IESNA/sample.ies` | 独立角度/光强/通量参考（LM-63-1995） |
| 通量随波长出口 | `…/NS-03/flux-wavelength-20261108/{flux.txt,summary.json}` | 证明出口可达但内容为空 |
| 极坐标矩阵 | `…/NS-03/source-polar-20261108/summary.json` | 19×19 网格值、`Dx/Dy`、标签 |
| 照明图的源条件 | `…/NS-03/source-illumination-twocolor-20261108/summary.json` | 4×`SourceEllipse` + `DetectorColor` 的对象条件 |
| 两份道路报告 | `…/NS-03/roadway-lighting-20261108/`、`…/roadway-lighting-repeat-20261108/` | 同默认路规、不同模型下的指标差异 |

## 3. 离线复算（本轮实际执行）

脚本：`.local/coordination/d006-offline.py`（纯离线，无 ZOS-API，只读上述材料）
输出：`.local/coordination/d006-offline.out.json`
命令：`C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe -B .local/coordination/d006-offline.py`
结果：**9 项检查全部通过，`failed_checks=[]`**。

| 检查 | 结果 |
| --- | --- |
| `directivity_angles` | 37 点、单扫描角 0°；对 IES 表的归一化参考最大差 **4.44444444444025e-05** ≤ 5.1e-05；峰值 18 cd |
| `directivity_flux` | 梯形积分 **112.81009451201489 lm** 对原生 112.81，差 **9.45e-05** ≤ 5e-3 |
| `source_spectrum` | 20 行、0.44–0.64 µm、峰值权重 1、输入/拟合 XYZ 均 `[1,1,1]`、CRI 70.1766、CCT 5188 K |
| `flux_outlet` | 报告行数 **0**、导出正文字符 0（原文件仅 BOM）、`text_export=true`、结果集合计数全 0 |
| `source_polar_grid` | 19×19、`dx=10.0`、`dy=18.94736842105263`、最小值 0、三个标签均 `None` |
| `source_polar_sample_correspondence` | 在**本样例（旋转对称输入）**下矩阵与 `sample.ies` 亮度表逐格相等（18…0）；x 步长 10° 与该文件垂直角一致；`dy=360/19` 与该文件 20° 节点步长**不同**（仅记录事实） |
| `illumination_condition` | 被检查模型含 4×`SourceEllipse` + 1×`DetectorColor`，其结果集合为空（仅限该模型对象条件） |
| `roadway_reports` | 两次同默认路规（CIE 140-2000）；模型分别为 `Two color mixing gives white` 与 `Fluorescent scattering in a bulk medium`；`Lavg` 由 1.74981e-06 变 0、`SR` 由 3.47391 变 0 |
| `product_interface` | `ANALYSES` 中存在 2 项、缺 8 项 |

配套普通回归（实际执行）：
`…/python.exe -B -m pytest tests/unit/test_yni_contributions.py tests/unit/test_wizards.py tests/unit/test_basic_analyses.py tests/unit/test_contracts.py -q -p no:cacheprovider` → **105 passed in 0.66s**。

## 4. 十项逐项处置

### 4.1 NS-03.SourceSpectrumViewer（`implemented`）

- 正式接口：`kind="source_spectrum_viewer"`；设置仅 `AS_Default`；出口为原生文本报告。
- 已有输入/结果：两色混合 NSC 样例、配置 1；20 点 0.44–0.64 µm、峰值权重 1、XYZ 输入=拟合=`[1,1,1]`、CRI 70.1766、CCT 5188 K；空 NSC 系统得到**完全相同**的报告，故「聚合源光谱」归属已撤回（`input_definition=native XYZ tristimulus fitting input`，`source_object_binding=not exposed by installed analysis settings`）。
- 可离线补齐：已在 `d006-offline.py` 复用原生报告完成行数/端点/峰值/XYZ/CRI/CCT 复算。可选加深：用 CIE 1931 2° 色匹配函数从 20 点权重独立算 XYZ→xy→CCT 与 Ra，与原生数值互校（需带出处的 CMF 表；CCT 需说明算法，原生 5188 K 未公布实现，故只能作量级自检）。
- 外部阻塞：安装接口未暴露按光源/输入模式的正式选择器，无法验证「可变输入」下的光谱与色度参考。
- 解除条件：取得正式输入模式/XYZ/文件选择及采用回读；再对受控可变输入建立光谱与色度参考。
- 本轮动作：**保持 `implemented`，不新增完成数**。

### 4.2 NS-03.FluxvsWavelength（`blocked`）

- 正式接口：产品无 kind；原生 `AS_Default` 创建成功。
- 已有输入/结果：两色 NSC 样例（系统波长 0.46/0.57 µm）；结果对象 `AR_Default` 有效但消息/序列/网格/RGB 网格/散点全为 0；`GetTextFile=true` 而文件仅 2 字节 BOM。
- 可离线补齐：已用 `flux_outlet` 固化「出口可达但为空」这一事实（行数 0、正文字符 0）。可静态算出该两波长系统应恰好有 2 个波长分箱，但源的光谱功率未公开，**无法**给出期望通量值。
- 外部阻塞：专题正式设置/输入选择缺失，且无非空结果出口。
- 解除条件：官方公布本专题的适用输入合同并给出非空结果出口（曲线/网格/文本任一），再建参考。
- 本轮动作：**保持 `blocked`**。

### 4.3 NS-03.DirectivityPlot（`implemented`）

- 正式接口：`kind="directivity_plot"`；设置仅 `AS_Default`；出口为原生文本报告。
- 已有输入/结果：报告含 IES 身份 `sample.ies`、峰值 18 cd、总光通量 112.81 lm、单条 37 点曲线（−180…+180，步长 10°），归一化到峰值 1。
- 可离线补齐：本轮已离线复现原生审计——从 `sample.ies`（19 垂直角 0–180、19 个相同水平切片、18→0 cd）重建归一化参考，37 点最大差 4.444e-05 < 5.1e-05；并复算梯形通量 112.81009451201489 lm 对 112.81。
- 外部阻塞：`AS_Default` 未暴露正式 IES 文件选择与扫描角选择，也没有采用回读；现有输入是旋转对称光强（所有水平切片相同），无法区分「按角度正确读取」与「按垂直角一维近似」。
- 解除条件：取得正式 IES 文件/扫描角选择器及采用回读；再用**非旋转对称**、多扫描角资源验收选择与归一化。
- 本轮动作：**保持 `implemented`**；离线复算作为参考证据补强，不计新增完成数。

### 4.4 / 4.5 CV-01.SourceColorChart1931、CV-01.SourceColorChart1976（`blocked`）

- 正式接口：产品无 kind；原生仅在 `AS_Default` 下创建并执行。
- 已有输入/结果：顺序（Cooke）与 NSC（两色）两种模式下均为 `AR_Default`、有效、零消息/零序列/零网格/零 RGB 网格/零散点，`GetTextFile=false`；无图像、无数值。2024 R2 帮助把两者定义为**固定 CIE 参考图**，其定义不依赖光学系统或源图像，故「源图选择器」这一条件已撤销。
- 可离线补齐：说明性算术只——给定报告中的输入 XYZ=`[1,1,1]`，1931 坐标为 (1/3, 1/3)、1976 为 u'=4/19≈0.21053、v'=9/19≈0.47368。这只是坐标变换恒等式，**不构成验收**，也不能替代原生图。台账允许的替代路径（「有出处与精度的 CIE 轨迹数据」）**仍需**官方基准与原生图形对应证据；本轮不以额外独立绘图关闭该项。
- 外部阻塞：`AR_Default` 不暴露图形像素或坐标，且文本导出关闭。
- 解除条件：可用的官方图像/数据出口；若走替代路径，还须同时给出官方基准与原生图形的对应证据（台账已列此路径，但未因替代而免除对应要求）。
- 本轮动作：**保持 `blocked`**，维持原声明；不引入外部色度数据，不自行绘图替代。

### 4.6 NS-03.SourcePolarViewer（`blocked`）

- 正式接口：产品无 kind；原生 `AS_Default`/`AR_Default` 有效。
- 已有输入/结果：单张 19×19 网格，范围 0–18，`Dx=10`、`Dy=18.94736842105263`、`MinX=MinY=0`，三个标签均 `None`，`GetTextFile=false`；2026-11-08 复测一致。
- 可离线补齐（**范围受限的观察**）：在**本样例的旋转对称输入**下，保存的 19×19 矩阵与 `sample.ies` 的亮度表逐格相等（18,17,…,0）。但该文件的 19 个水平切片完全相同，故此结果只支持「**本样例的数值对应**」，**不能**证明原生对任意 IES 原始表的发布方式，也不能确定其单位与归一化契约。
- 已记录但**不作判定**的差异：原生 `Dy=18.94736842105263` 恰等于 360/19，与该文件的 20° 节点步长（0,20,…,360）不同。这可能是原生的像素范围/中心约定所致，本轮**只记录事实**，不判为原生映射错误。
- 外部阻塞：无正式轴/单位/归一化定义，三个标签均为 `None`。
- 解除条件：官方轴语义与单位说明；随后用**非旋转对称**的受控方向性源复核发布方式与单位，并据官方约定解释 `Dy`（像素范围/中心）与 20° 节点步长的关系。
- 本轮动作：**保持 `blocked`**；上述观察作为受限证据登记，不改台账结论，也不申报原生缺陷。

### 4.7 NS-03.SourceIlluminationMap（`blocked`）

- 正式接口：产品无 kind；原生 `AS_Default`/`AR_Default` 有效。
- 已有输入/结果：两色样例确认 4 个 1 W `SourceEllipse`（覆盖波长 1/2）与 1 个 `DetectorColor`；专题返回零消息/零序列/零网格/零 RGB/零散点，`GetTextFile=false`。
- 可离线补齐：已复算并固化**被检查模型的对象条件**（4×SourceEllipse + DetectorColor）与该模型的空结果集合。这只能证明「本模型对象条件成立且出口为空」，**不能**据此排除其它所有输入条件错误——本专题缺少输入选择合同，未检查的条件无法排除。
- 外部阻塞：缺可用的照明网格/图像出口；同时缺专题输入选择合同。
- 解除条件：官方照明网格/图像出口出现**且**取得输入选择合同后，再验坐标、单位与通量（对探测器参考）。
- 本轮动作：**保持 `blocked`**。

### 4.8 NS-03.PhotoluminscenceViewer（`blocked`）

- 正式接口：产品无 kind；原生可创建并执行（Premium 许可允许创建该主题）。
- 已有输入/结果：`Fluorescence Example using Waveshift.zos` 与 `White LED Phosphor.zos` 均返回一条原生消息「输入无效数据/设置」；后者对象 3 上有 `PhotoluminescenceModel` 仍被拒。2026-11-08 重启后复测一致（30 字节文本导出，零结果集合）。
- 可离线补齐：无——样例二进制模型文件无法在不启动原生的前提下解析其输入合同；本轮不臆测。
- 外部阻塞：缺本专题的正式输入/选择合同或有效模型条件。
- 解除条件：取得文档化输入合同（或官方给出的有效模型要求），随后取非空输出并建参考。
- 本轮动作：**保持 `blocked`**。

### 4.9 NS-03.RadiantSourceModelViewerSettings（`blocked`）

- 正式接口：产品无 kind；原生可创建。
- 已有输入/结果：两次探测（两色样例、荧光样例）均返回原生消息「只有 OpticStudio 旗舰版支持所需功能」；无序列/网格/散点/文本。本机许可为 `PremiumEdition`；样例树中未发现专用 Radiant 源模型文件，现有 IES 不能充当其输入合同。
- 可离线补齐：无——许可与资源两项都不在离线可补范围。
- 外部阻塞：**许可**（需旗舰版/企业版）+ **匹配的 Radiant 源模型输入**。
- 解除条件：取得旗舰版许可与匹配资源后，验设置采用与非空结果。
- 本轮动作：**保持 `blocked`**；属环境/许可类阻塞，按本轮策略「保存证据与解除条件后跳过」。

### 4.10 NS-03.RoadwayLighting（`blocked`）

- 正式接口：产品无 kind；原生 `AS_Default` 无可写/可回读专题设置。注意与 `src/zemax_mcp/wizards.py:8` 的 `NSCRoadwayLightingWizard`（评价函数向导）**不是同一功能**。
- 已有输入/结果：两次报告均用默认路规（CIE 140-2000、安装高度 10000、单侧、纵向间隔 30000、3 车道、车道宽 5000、R1、ME1）。第一次（`Two color mixing gives white`）给出 `Lavg=1.74981e-06`、`Uo=0`、`Ul=0`、`TI=0`、`SR=3.47391`；第二次（`Fluorescent scattering in a bulk medium`）全部为 0，照度行为 N/A。
- 可离线补齐：本轮已逐字段比对两份报告，确认「同一默认路规 + 不同系统 → 不同指标」，且 `SR` 目标为 ≥0.5。这证明指标随输入变化、但设置不可采用/回读，故两次数值都不能归属到受控道路输入。
- 外部阻塞：缺道路专用模型/光源，且无正式设置回读接口。
- 解除条件：取得道路专用模型或光源，并取得可回读的正式专题设置；再对 NSC 探测器参考验光度坐标与指标。
- 本轮动作：**保持 `blocked`**。

## 5. 有正式设置/结果的可实现子项（本轮判定）

**可实现（有正式结果出口，且本轮已离线复核）**

1. `NS-03.SourceSpectrumViewer` — 默认 XYZ 拟合报告的解析与数值复核。设置侧仍只有 `AS_Default`，所以可实现的仅是「默认报告的解析」，不是「可变输入选择」。
2. `NS-03.DirectivityPlot` — 默认报告（IES 身份、峰值、通量、角度曲线）的解析与独立 IES 参考复核。同样不包含文件/扫描角选择。

**不可实现（缺正式设置或非空结果，本轮不动代码）**

3. `NS-03.FluxvsWavelength`、`NS-03.SourceIlluminationMap` — 出口为空（照明图仅证明**被检查模型**的对象条件，不足以排除所有输入条件错误）。
4. `CV-01.SourceColorChart1931/1976` — 无图像/数值出口；替代基准仍需官方基准与原生图形对应证据，本轮维持原声明。
5. `NS-03.SourcePolarViewer` — 有矩阵但无轴/单位/标签合同；逐格相等只对本样例成立。
6. `NS-03.PhotoluminscenceViewer` — 原生拒收输入。
7. `NS-03.RadiantSourceModelViewerSettings` — 许可限制。
8. `NS-03.RoadwayLighting` — 无设置接口且无道路模型。

即：十项中 **2 项**具备正式结果出口并已获离线复核，**8 项**维持外部阻塞；本轮不产生新增 `done`。

## 6. 建议顺序（交给协调者批准后实施）

1. 两项色度图：等官方图像/数据出口，或「官方基准 + 原生图形对应证据」齐备后再推进；本轮不靠额外独立绘图关闭。
2. `SourcePolarViewer`：等官方轴语义/单位说明。`Dy=360/19` 仅作事实记录，不按缺陷提交；后续用非旋转对称源复核发布方式与单位。
3. `DirectivityPlot` / `SourceSpectrumViewer`：等正式选择器；在此之前不再新增探测轮次（旋转对称输入已到极限）。
4. `FluxvsWavelength`、`SourceIlluminationMap`、`PhotoluminscenceViewer`、`RoadwayLighting`：等官方出口或输入合同。
5. `RadiantSourceModelViewerSettings`：等旗舰版许可，本轮及后续普通轮次跳过。

## 7. 风险与未决

1. 5.1e-5 角度门槛沿用既有原生审计口径；若改用更严格门槛，当前 4.444e-05 的最大差仍有约 13% 余量，需重估。
2. 通量门槛 5e-3 取自报告 4 位小数；原生若改变显示精度需重算。
3. `sample.ies` 是旋转对称样例（19 个水平切片完全相同），因此通量与角度参考都无法验证水平方向选择性——这是 `DirectivityPlot` 的实质限制。
4. `SourcePolarViewer` 的逐格相等仅对**本样例（旋转对称）**成立：既不能推断其它源的行为，也不能据此确定原生的发布方式/单位/归一化契约。
5. `SourceIlluminationMap` 的空结果只覆盖**被检查模型**的对象条件，不能作为「所有输入条件都正确」的证明。
6. 两份道路报告使用了不同系统却均标为默认路规，说明该专题可能在无有效道路输入时静默套用默认值——若成立，属于产品应显式报错的场景，需协调者确认是否列为缺陷。
7. 全部结论仅覆盖 PremiumEdition 24.2.0 build 240529；旗舰版行为未验证。

## 8. 交给协调者的决定点

1. 两项 CIE 色度图：台账允许的「有出处与精度的 CIE 轨迹数据」替代路径，是否要求先取得**官方基准 + 原生图形对应证据**再启用？本轮按此要求保持原声明（未关闭）。
2. `SourcePolarViewer`：`dy=360/19` 与 `sample.ies` 的 20° 节点步长不同，是否登记为「待解释的像素范围/中心约定」观察项（**不是**缺陷）？
3. `RoadwayLighting` 在无道路输入时静默返回默认路规指标，是否按缺陷登记？
4. D006 十项本轮是否按「2 项维持 `implemented` + 8 项 `blocked`」结账，还是需要我继续在离线范围内深挖某一项？
