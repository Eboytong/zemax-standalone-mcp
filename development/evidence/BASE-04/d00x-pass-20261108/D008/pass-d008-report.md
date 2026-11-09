# D008 七项报告（96 项走查轮 · 第 10 回合）

- 工作区：`C:\Users\tonge\.codex\worktrees\zemax-p01-hologram\Zemax_MCP`；权威计划：主区 `development`（`tracking/d00x-pass-20261108.json`）
- 本 worker 负责 D008 的 7 项（`worker_id=zemax-p01-hologram`）：
  `MF-01.SagTable`、`MF-01.TestPlateList`、`CV-01.ISOElementDrawing`、`MF-01.ZemaxElementDrawing`、
  `NS-04.PrescriptionGraphic`、`NS-04.NSCObjectViewer`、`NS-04.PartViewer`
- 不接管：`NS-04.PrescriptionDataSettings`、`NS-04.SurfaceDataSettings`（gradium worker）
- **原生启动**：`application_create` 已三次 180 s 超时（`runtime-recovery-01/02/05`，`development/evidence/BASE-04/runtime-phase-environment-20261108.md`），本回合跳过原生启动；下文"历史原生"指既有存档运行，"本轮离线"指本回合脚本复算/提取，二者分开记录。
- 本回合未执行任何原生运行；未修改产品代码或公共台账；无 Git 提交。
- 完成条件的**声明范围保持不变**：SagTable 的 reverse 制造摘要、面型适用性、TestPlate 目录选择等，**不以 scoped-out 或缩小范围的方式关闭**。功能完成由协调者裁定，本报告只给分项成果与证据。
- **结论限定**：第 3–7 项（图纸/查看器）的结论均限定为**本机已扫描的公开接口与样本**，不代表相关接口永久不存在；保留未来正式结果出口后重评的条件。

离线脚本与输出（均可复算）：
- `.local/coordination/pass_d008_offline.py` → `.local/coordination/pass-d008-offline-checks.json`
- `.local/coordination/pass_d008_native_evidence.py` → `.local/coordination/pass-d008-native-evidence.json`

---

## 1. `MF-01.SagTable`（别名 `MA-01.SagTable`）

### 1.1 正式接口
- MCP 入口 `run_analysis: sag_table`；请求模型 `src/zemax_mcp/sag_table.py::SagTable`（`surface`、`best_fit_sphere∈{MinimumVolume,MinimumRMS,MinimumRMSWithOffset}`、`reverse` 仅 MinimumVolume、`minimum_radius`/`maximum_radius`、`samples 2–10001`）。
- 正式原生操作数：`BFSD`（八项摘要）、`SSAG`（准则球面）、`DSAG`（Data9 半径 / Data10 顶点 Z 偏移）、`SSLP`（斜率）、`LDE.GetSag`。
- 专用 SagTable 设置对象**未采用**；本机该分析仅暴露通用 `AS_Default`/`CFG`，故计算参数以显式操作数实参写入并原样记录。

### 1.2 已完成范围（640/641，不计为剩余）
| 项 | 证据 | 结果 |
| --- | --- | --- |
| 1001 节点径向加权斜率摘要 | `development/evidence/MF-01/progress641-slope-summary.json`、`ordinary640-slope-summary.xml`、`native641-slope-summary.xml` | 普通 45 通过 / 原生 ±1 两例通过（47.142 s / 102.955 s） |
| 摘要字段与采样 | 同上 | `maximum_slope_difference`、`rms_slope_difference`、`slope_summary_source`；1000 等长区间/1001 含端点节点；`rms=sqrt(Σr·d²/Σr)` |

### 1.3 本轮离线实际检查（O3/O4）
- **O3 640/641 摘要复算**（脚本重算 `progress641-slope-summary.json` 的 12 项）：最大绝对误差 **1.6653345369377348e-15**；12/12 通过 `1e-6 + 1e-5×参考`；与存档判定、存档误差值完全一致。
- **O4 622 偏移/半径复算**（`progress622-dsag-fit.json`）：正负号相反成对行 4；幅值最大差 **2.1348433464811814e-11 mm**；半径最大误差 **5.378943512823753e-09 mm**（门槛 5e-6）。→ 同面型内"符号相反、幅值相等"自洽。
- 普通测试：`pytest tests/unit/test_sag_table.py tests/unit/test_sag_fit.py -q`（含于 71 passed）。

### 1.4 剩余缺口（保持原声明范围，未关闭）
1. **制造偏移基准/符号**：`BFSD summary.vertex_offset` 与 `DSAG Data10` 原始值之间**无正式换算合同**；ZernikeFringeSag 加 piston 显示原始值含局部顶点基准。H1/H2（基准常数 + 方向约定）与存档数据自洽，但换算合同尚未由原生出口给出。
2. **面型拟合适用性**：ZernikeFringeSag 与 EvenAspheric 等形半径差 **3.8380e-5 mm** > 5e-6；缺适用性表。H3 待 §1.5 控制实验确认。
3. **反向制造摘要**：`reverse=true`（BFS3）仅给曲线，`vertex_offset`/`removal_depth` 为 null、`manufacturing_state=unavailable`；DSAG 手册列 BFS 0–2，生产未发 BFS3。H4 待确认。
- **解除条件**：①正式输入选择+采用回读，或经审查的等价验收（显式基准与符号合同）；②对声明面型集合给独立参考一致的适用性表与反例；③反向摘要正式出口，或"原生仅曲线"的适用条件证据。

---

## 2. `MF-01.TestPlateList`

- **正式成员**：typed 请求 `test_plate_list` 已存在（`src/zemax_mcp/test_plates.py::TestPlateList`；`catalog_file`、`method∈{auto,native,file}`；分派见 `analysis_models.py`/`analyses.py`/`backend.py`/`modeling.py`/`models.py`）。
- **本轮离线实际检查（O2）**：用 `parse_tpd` 独立解析已安装 `Applied.tpd`，与存档原生行 `plates429_native_f9120956a3/native-result.json` 逐行对照：
  - 解析 899 行 / 原生 899 行；半径最大差 **0.0 mm**，直径最大差 **0.0 mm**；超容差（0.0000500001 mm）**0** 行；`plate_id`/`availability_code` 不一致 **0**。→ **通过**（严于 5e-5 容差）。
- **历史原生**：`test-plate-list-acceptance20261108.md`（普通 26、原生 2 通过 30.17 s）；`native435-plates-final.xml`。
- **剩余缺口（未关闭）**：**在本机已扫描的 `AS_Default` 设置接口中未见目录选择器**，切换目录的正式采用回读尚缺；当前只是"活动目录 + 显式 TPD 文件"可用（保留未来正式目录接口后重评）。解除条件：正式目录选择与采用回读，或经审查接受该声明范围（不缩小范围）。

---

## 3. `CV-01.ISOElementDrawing`（图纸）

- **正式成员**：**本机工作区源码检索**中未找到 `ISOElementDrawing`/`iso_element` 的 typed 请求；仅原生枚举存在（不排除未来接口）。
- **本轮离线实际检查**（`pass-d008-native-evidence.json`，来自 `CV-01/runtime071/settings.json` + `iso-element-drawing-20261108/summary.json`）：
  - 设置类型 `ZemaxUI.ZOSAPI.Analysis.AS_Default`；静态公开属性仅 `Analysis/TheDataID/IsValid/IsActiveWindow/Parent`（25 个方法，`cfg_export` 返回 True）；动态 `settings_members` 31。
  - 结果类型 `AR_Default`（`result_members` 76）；各集合计数 `NumberOfMessages/DataSeries/DataGrids/DataGridsRgb/DataScatterPoints/DataScatterPointsRgb` **全 0**；`text_export=false`。
  - 在**本机已扫描的 76 个结果成员**中按 image/bitmap/save/export 等关键字扫描，**未见图像/矢量出口成员**。
  - 模型输入 `Cooke 40 degree field.zos`；`model_unchanged=true`；`close=true`；`disconnect.ok=true`。
- **剩余缺口（未关闭）**：**在本机已扫描的接口/样本范围内**未见正式绘图结果/图像出口；保留未来正式结果出口后重评的条件。解除条件：公开 API 暴露可用的绘图结果/图像出口且有输入→图纸身份选择合同。

## 4. `MF-01.ZemaxElementDrawing`（图纸）

- **正式成员**：**本机工作区源码检索**中未找到 typed 请求（`analyses.csv` 记 run_analysis union 无该项）。
- **本轮离线实际检查**（`MF-01/runtime078/settings.json` + `zemax-element-drawing-repeat-20261108/probe.json`）：
  - 设置类型 `AS_Default`；静态属性同上 5 项（25 方法）；探针设置属性 `Analysis/TheDataID/IsValid/IsActiveWindow/Parent`，`cfg_saved=true`。
  - 结果各集合计数（含 **`NumberOfRayData`**）共 8 类 **全 0**；`text_exported=false`。
  - **本机已扫描**结果方法 21、结果属性 27，未见图像/矢量出口。
  - `IsActiveWindow=false`（存档记录）；`closed=true`；`disconnect.ok=true`。
- **剩余缺口（未关闭）**：**在本机已扫描的接口/样本范围内**未见正式图纸数据/图像/矢量出口；保留未来正式结果出口后重评的条件。解除条件：正式图纸结果出口 + 输入→图纸几何身份合同。

## 5. `NS-04.PrescriptionGraphic`（图形）

- **正式成员**：**本机工作区源码检索**中未找到 typed 请求。
- **本轮离线实际检查**（`NS-04/runtime066/settings.json`（静态）+ 顺序/纯 NSC 两份 summary）：
  - 静态 `runtime_settings_type=AS_Default`，5 属性（25 方法，`cfg_export` True，`closed=true`）。
  - **顺序 Cooke**：`AR_Default` 结果，6 类计数**全 0**，`text_export=false`；`close=true`、`disconnect.ok=true`；`get_nsc_objects` 因混合模式需显式 `nsc_surface` 返回 `UNSUPPORTED_MODE`（0 行）。
  - **纯 NSC 色度样本**：`New_Analysis_SettingsFirst(PrescriptionGraphic)` 返回 null，随后 `GetSettings` 抛 `AttributeError: 'NoneType' object has no attribute 'GetSettings'`；无分析对象；`disconnect.ok=true`；该样本对象列表本身可读（5 个：4×SourceEllipse + DetectorColor）。
  - **本机已扫描**结果成员中未见图像/矢量出口。
- **剩余缺口（未关闭）**：**在本机已扫描的接口/样本范围内**，顺序无可用图形/文本出口、纯 NSC 工厂返回 null；保留未来正式出口后重评的条件。解除条件：正式顺序图形导出路径；若 NSC 属声明范围需受支持工厂。

## 6. `NS-04.NSCObjectViewer`（对象查看器）

- **正式成员**：**本机工作区源码检索**中未找到 typed 请求；替代数据入口 `get_nsc_objects` 可用。
- **本轮离线实际检查**（`NS-04/runtime066/settings.json` + `nsc-object-viewer-repeat-20261108/summary.json`）：
  - 静态 `AS_Default`，5 属性（25 方法）。
  - 结果 `AR_Default`，6 类计数**全 0**，`text_export=false`；**本机已扫描**结果成员中未见图像/矢量出口；`close=true`、`disconnect.ok=true`。
  - 同工作副本 `get_nsc_objects`：`ok=true`，`total=5`、`next_start=null`（完整），对象类型 `['SourceEllipse'×4, 'DetectorColor']`。
  - **复核发现（与旧叙述不一致，如实记录）**：`nsc-object-viewer-repeat20261108.md` 叙述"8 个对象"，但存档 summary 实测 `total=5`；本报告以存档实测为准并标记该差异供审查。
- **剩余缺口（未关闭）**：**在本机已扫描的接口/样本范围内**，Viewer 无对象选择/回读与图形结果出口；保留未来正式出口后重评的条件。**分项成果**：`get_nsc_objects` 可完整读取当前对象数据（5 个，含属性/面/体积等），可作对象数据替代入口记录。解除条件：正式对象选择+采用回读 + 图形结果出口。

## 7. `NS-04.PartViewer`（零件查看器）

- **正式成员**：**本机工作区源码检索**中未找到 typed 请求。
- **本轮离线实际检查**（`NS-04/runtime066/settings.json` + 两份 summary）：
  - 静态 `AS_Default`，5 属性（25 方法）。
  - 色度样本：`AR_Default`，6 类计数全 0，`text_export=false`，`close=true`、`disconnect.ok=true`；对象 5 个（无部件几何）。
  - **Boolean Lens Mount**（含真实部件）：对象 `ok=true`、`total=6`、`next_start=null`，类型 `['RectangularVolume','CylinderVolume'×3,'BooleanNative','NullObject']`；但 `AR_Default` 6 类计数**全 0**、`text_export=false`、结果未标识或分组部件；`close=true`、`disconnect.ok=true`。
  - 结果成员扫描**无图像/矢量出口**。
- **剩余缺口（未关闭）**：**在本机已扫描的接口/样本范围内**，无部件选择/回读合同与可用结果出口（已排除"首个样本无部件几何"为唯一原因）；保留未来正式出口后重评的条件。解除条件：部件选择/回读合同 + 可用部件数据或图像/矢量出口。

---

## 8. 七项汇总

| 项 | 正式成员 | 本轮实际检查 | 结果 | 剩余缺口（保持原范围） |
| --- | --- | --- | --- | --- |
| MF-01.SagTable | `sag_table` 入口 + BFSD/SSAG/DSAG/SSLP/GetSag | O3 摘要 12 项、O4 偏移/半径复算 | 摘要全通过；偏移符号自洽 | 偏移基准合同 / 面型适用性 / 反向摘要 |
| MF-01.TestPlateList | `test_plate_list` typed 请求 | O2 Applied.tpd 899 行独立解析对照 | 0 差、0 超容差 | 目录选择器与采用回读 |
| CV-01.ISOElementDrawing | 本机源码未见（仅原生枚举） | 静态反射+原始结果提取 | AS_Default；计数全 0；本机未见图像出口；关闭/断连通过 | 正式绘图结果/图像出口 |
| MF-01.ZemaxElementDrawing | 本机源码未见 typed 请求 | 同上 | AS_Default；8 类计数全 0；本机未见出口；关闭通过 | 正式图纸数据/矢量出口 |
| NS-04.PrescriptionGraphic | 本机源码未见 typed 请求 | 顺序+纯 NSC 两模式提取 | 顺序全 0；NSC 工厂 null；关闭通过 | 顺序图形出口 / NSC 工厂 |
| NS-04.NSCObjectViewer | 本机源码未见 typed 请求；`get_nsc_objects` 可用 | Viewer 提取 + 对象清单 | Viewer 全 0；对象完整 5 个（旧述 8 不一致，协调者更正） | 对象选择/回读 + 图形出口 |
| NS-04.PartViewer | 本机源码未见 typed 请求 | 色度+Lens Mount 两样本提取 | 全 0；部件对象 6 个可读；关闭通过 | 部件选择/回读 + 结果出口 |

**分项成果记录**：TestPlateList 的显式 TPD 文件解析与活动目录身份（O2 899 行零差）、SagTable 的 640/641 斜率摘要（O3 复算通过）、NSCObjectViewer 的 `get_nsc_objects` 对象数据读取，均作为分项成果记录；**完整功能完成由协调者裁定**。

**外部阻塞与解除条件**：以上五项图纸/查看器均因公开 API 未暴露正式结果/图像/矢量出口或选择合同而阻塞，解除条件已逐项列明；原生启动三次 180 s 超时为本轮统一前置阻塞（`BASE-04/runtime-phase-environment-20261108.md`）。

> 说明：以上结论仅针对**本机已扫描的公开接口与样本**；若后续正式接口暴露绘图/查看器结果出口，应据此重新评估。`NSCObjectViewer` 存档证据为 **5 个对象**，旧文档所述 8 个为错误，由协调者更正。
