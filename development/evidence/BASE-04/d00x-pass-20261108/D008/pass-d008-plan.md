# D008 计划：SagTable 剩余范围 + 其余六项（96 项走查轮）

- 工作区：`C:\Users\tonge\.codex\worktrees\zemax-p01-hologram\Zemax_MCP`（分支 `codex/d010-hologram-native`）
- 权威计划：主区 `C:/Users/tonge/Desktop/Zemax_MCP/development`；分配依据 `development/tracking/d00x-pass-20261108.json`
- 本 worker 负责的 D008 条目（7 项，`worker_id=zemax-p01-hologram`）：
  `MF-01.SagTable`、`MF-01.TestPlateList`、`CV-01.ISOElementDrawing`、`MF-01.ZemaxElementDrawing`、
  `NS-04.PrescriptionGraphic`、`NS-04.NSCObjectViewer`、`NS-04.PartViewer`
- 不接管：`NS-04.PrescriptionDataSettings`、`NS-04.SurfaceDataSettings`（gradium worker）
- 本轮前置：原生 `application_create` 已三次 180 s 超时（`runtime-recovery-01/02/05`，证据 `development/evidence/BASE-04/runtime-phase-environment-20261108.md`），**本轮跳过原生启动**，不重复排查；本轮只做离线补充、普通测试与证据复算
- 本轮不做 Git 提交、不自行发行；公共台账由协调者更新

---

## 1. SagTable（`MF-01.SagTable`，别名 `MA-01.SagTable`）

### 1.1 当前正式接口

| 项 | 内容 |
| --- | --- |
| MCP 入口 | `run_analysis: sag_table`（`src/zemax_mcp/sag_table.py::run_sag_table`） |
| 请求模型 | `SagTable(Request)`：`surface`(≥1)、`best_fit_sphere ∈ {MinimumVolume, MinimumRMS, MinimumRMSWithOffset}`、`reverse`(仅 MinimumVolume)、`minimum_radius`/`maximum_radius`(0 表示自动)、`samples`(2–10001，默认 51) |
| 正式原生操作数 | `BFSD`（MinimumVolume 八项摘要）、`SSAG`（准则球面，Remove=2，BFS=1/2/3）、`DSAG`（Data9 半径 / Data10 顶点 Z 偏移）、`SSLP`（曲面斜率）、`LDE.GetSag`（矢高） |
| 设置对象 | 专用 SagTable 设置**未采用**：本机该分析仅暴露通用 `AS_Default`/`CFG`，因此全部计算参数以显式操作数实参写入并原样记录于 `actual_settings`/`native_query_arguments` |
| 结果出口 | `summary`（8 项 + 准则曲线附加项）、`rows`（Y/sag/BFS sag/偏离/去除深度/斜率/BFS 斜率/斜率差）、三个 `series`（Sag、Removal|Deviation、Slope）、`sphere_reconstruction`、`native_bfs_fit`、`statistics_sampling`、`slope_query_copy` |
| 单位 | 长度=镜头单位，斜率=无量纲，曲率=1/镜头单位，体积=镜头单位³ |

### 1.2 640/641 已完成范围（**已完成，不得重复计为剩余**）

| 交付 | 证据 | 结果 |
| --- | --- | --- |
| 1001 节点径向加权斜率摘要（非默认准则与反向曲线） | `development/evidence/MF-01/progress641-slope-summary.json`、`ordinary640-slope-summary.xml`、`native641-slope-summary.xml` | 普通 45 项通过；原生 ±1 两例通过（47.142 s / 102.955 s） |
| 摘要字段与采样定义 | 同上 | `maximum_slope_difference`、`rms_slope_difference`、`slope_summary_source`；1000 等长区间/1001 含端点节点；`rms = sqrt(Σ r_i d_i² / Σ r_i)` |
| 12 项摘要数值比较 | `progress641-slope-summary.json.comparisons` | 最大绝对误差 **1.6653345369377348e-15**，门槛 `1e-6 + 1e-5×参考` |
| 统计口径（BFSD 摘要 vs 显式 SSLP 采样） | `progress519-statistics.json`、`native518-statistics.xml` | 已分离标识 `slope_summary_source`，环形区间内边界项保留 |

即：**斜率摘要（640/641）已完成**，本轮不再作为剩余项。

### 1.3 剩余范围（本轮计划对象）

**(A) 制造偏移基准与符号**

- 现状：`BFSD` 的 `summary.vertex_offset`（MinimumVolume）与 `DSAG` Data10 的原始 `vertex_z_offset` 是**两个出口**；正负 EvenAspheric 上原始值 −0.0002083725005 / +0.0002083725027 mm，与独立球面加法偏移 +0.0002083725218 mm **符号相反**；ZernikeFringeSag 加 ±0.003 mm piston 的对照显示原始值还包含局部顶点基准（`progress622-dsag-fit.json`）
- 缺口：两者之间的基准/符号换算无正式合同；`MinimumRMSWithOffset` 与反向 MinimumVolume 的物理偏移仍为 `null`
- 已有可离线复算材料：`progress622-dsag-fit.json` 的 `comparisons`（含 `native_offset`、`independent_additive_sphere_offset`、`radius_error`、`opposite_sign_offset_error`）与 `retained_text_comparison`

**(B) 面型拟合适用性**

- 现状：同形无 piston 时 ZernikeFringeSag 带偏移半径 39.8400013026 mm 与 EvenAspheric 39.8400396827 mm 相差 **3.8380e-5 mm**，超 5e-6 门槛
- 缺口：哪些面型（Standard/EvenAspheric/ZernikeFringeSag/Composite/Biconic 旋转对称）的 BFSD/DSAG 拟合与独立参考一致，尚未形成适用性表
- 已有材料：`progress622-dsag-fit.json`、`progress558-applicability.json`、`native553-applicability.xml`

**(C) 反向制造摘要**

- 现状：`reverse=true`（BFS3）只给曲线，`summary.vertex_offset`/`rows.removal_depth` 为 `null`、`manufacturing_state=unavailable`；DSAG 手册列 0–2，生产未发 BFS3 查询（仅 615 诊断）
- 缺口：反向是否应有制造摘要、以何基准给出，无正式依据
- 已有材料：`progress582-criterion-curves.json`、`native615` 诊断

### 1.4 可区分假设（互斥、可离线区分）

| 编号 | 假设 | 离线可区分性 |
| --- | --- | --- |
| H1 | `DSAG` Data10 与 `summary.vertex_offset` 差一个**基准常数**（局部顶点 vs 拟合球顶点） | 用 622 中 piston=0 与 piston=±.003 三组原始值做差分，常数项应稳定 |
| H2 | 二者符号相反是**方向约定**差异（+z 空气→玻璃 vs 去除方向） | 正负 EvenAspheric 上 `sign(native) = -sign(independent)` 且幅值一致（误差 2.1348e-11 mm） |
| H3 | 半径差异源自**面型参数化**而非拟合实现 | 等矢高的 Zernike 与 EvenAspheric 得到不同 BFSD 半径（3.8380e-5 mm），而同一面型自洽 |
| H4 | 反向无摘要是**原生适用条件**（BFS3 仅曲线） | 582 反向结果字段与 615 DSAG BFS3 直接诊断一致为曲线/无量纲值，无摘要项 |

### 1.5 最小控制实验（原生，本轮暂缓）

1. 单面 EvenAspheric（semi 5 mm，z=±.0126 r²）+ piston {0, ±0.003 mm}：一次任务内读 BFSD 八项 + DSAG Data9/10 + SSAG 四点 → 直接区分 H1/H2
2. 正负 EvenAspheric 成对：确认符号关系与幅值一致（复用 622 结构）
3. ZernikeFringeSag 与 EvenAspheric **等矢高**：比较 BFSD 半径与独立拟合 → 区分 H3
4. reverse 曲线 + DSAG BFS3 直接查询：比较可用字段 → 区分 H4

每个实验均复用现有 `test_sag_criteria_live.py` 的任务结构，单会话完成、任务关闭、断连。

### 1.6 沿用容差（不得放宽）

| 用途 | 容差 |
| --- | --- |
| rows（sag/斜率/去除深度） | `1e-8 + 1e-6×参考值` |
| 统计（最大/RMS 斜率差、RMS 去除深度、体积） | `1e-6 + 1e-5×参考值`；体积另加绝对 `1e-5` |
| 半径一致性（SSAG 四点重建 vs DSAG） | 绝对 `5e-6` 镜头单位 |
| 正负偏移对照 | `1e-8 mm + 1e-6×相对` |

### 1.7 实施文件归属

| 文件 | 角色 |
| --- | --- |
| `src/zemax_mcp/sag_table.py` | 主实现（摘要/曲线/斜率摘要/适用性字段） |
| `src/zemax_mcp/sag_fit.py` | 球面重建与残差判定 |
| `src/zemax_mcp/analysis_models.py`、`analyses.py` | 仅当新增请求字段或分派时改动（最小共享补丁） |
| `tests/unit/test_sag_table.py`、`tests/unit/test_sag_fit.py` | 普通测试 |
| `tests/native/test_sag_criteria_live.py`、`test_sag_table_statistics_live.py`、`test_sag_table_applicability_live.py`、`test_sag_table_live.py`、`test_sag_table_units_configuration_live.py` | 原生测试 |

### 1.8 普通/原生作业

- 普通（本轮可执行）：`pytest tests/unit/test_sag_table.py tests/unit/test_sag_fit.py -q`（历史 38 + 7 项）
- 原生（本轮跳过）：`pytest tests/native/test_sag_criteria_live.py --run-zemax -q`（±2 例）、`test_sag_table_statistics_live.py`、`test_sag_table_applicability_live.py`

### 1.9 保存/恢复/关闭

保存重载后曲面与 solve、系统、MFE/MCE、配置保持；任务 `close_attempted=true`；取消保留已完成行与已完成采样；孔径存在时自有斜率副本在成功/失败/取消均关闭，关闭失败置 `requires_reconnect` 并保留原始错误。

### 1.10 完成门槛

1. 制造偏移：给出正式输入选择与采用回读，或给出经审查的**等价验收**（含基准与符号的显式合同）；
2. 面型适用性：对声明面型集合给出独立参考一致的适用性表与反例；
3. 反向摘要：给出正式摘要或明确标注"原生仅曲线"并附适用条件证据；
4. 三项均需普通+原生证据、保存重载与关闭回执。

---

## 2. `MF-01.TestPlateList`（样板目录）

| 项 | 内容 |
| --- | --- |
| 正式成员 | **已存在** typed 请求 `test_plate_list`：`src/zemax_mcp/test_plates.py`（`TestPlateList`：`catalog_file`、`method ∈ {auto, native, file}`）、`analysis_models.py`、`analyses.py`、`backend.py`、`modeling.py`、`models.py` |
| 已有输出 | 活动目录身份 + 目录行（`plate_id`、`radius_mm`、`diameter_mm`、`concave`/`convex`、`availability_code`、`source_line`）；`auto` 下请求目录不符时按文档化 TPD 回退，`native` 强制时返回 `SETTING_NOT_SUPPORTED` |
| 已有证据 | `development/evidence/MF-01/test-plate-list-acceptance20261108.md`（普通 26 通过、原生 2 通过 30.17 s）、`progress435-plates.json`、`native435-plates-final.xml`、`native429/430/431/433` |
| 已有数值 | 原生行与独立 TPD 解析逐行对照（原生尺寸四位小数），容差 `0.0000500001 mm`；含分页、目录身份、回退、强制拒绝、资源缺失/损坏、取消、任务复用、保存重载、系统保持 |
| 剩余缺口 | 原生 `AS_Default` 无目录选择器；**切换目录**的正式采用回读缺失 |
| 可离线补充（本轮） | 用已保存 `plates429_native_f9120956a3` 的原生行与 `parse_tpd` 独立解析逐行复算，重算最大绝对差与容差判定 |
| 完成条件 | 取得正式目录选择与采用回读，或经审查接受"活动目录 + 显式 TPD 文件"为声明范围 |

## 3. `CV-01.ISOElementDrawing`

| 项 | 内容 |
| --- | --- |
| 正式成员 | **未在源码中找到** typed 请求（`src/` 无 `ISOElementDrawing`/`iso_element` 成员）；仅原生枚举 `ISOElementDrawing` 存在 |
| 已有证据 | `development/evidence/CV-01/iso-element-drawing-probe20261108.md`、`CV-01/runtime071/settings.json` |
| 已有结果 | Cooke 顺序样本：工厂返回有效 `AS_Default`，仅 `IsValid`/`IsActiveWindow`；执行后 series/grids/RGB/scatter 全 0，`GetTextFile=false`，结果类型无图像/文件导出成员；表面快照前后一致、任务关闭、断连通过 |
| 可离线补充 | 复核静态反射中该分析暴露的设置/结果成员清单（只读），确认"无选择合同"的表述范围 |
| 外部阻塞 | 正式绘图结果/图像出口缺失 |
| 解除条件 | 安装的公开 API 或官方集成暴露可用的绘图结果/图像出口，且具备输入→图纸身份选择合同 |

## 4. `MF-01.ZemaxElementDrawing`

| 项 | 内容 |
| --- | --- |
| 正式成员 | **未在源码中找到** typed 请求；`analyses.csv` 记 `No typed request was found in the current run_analysis union` |
| 已有证据 | `development/evidence/MF-01/zemax-element-drawing-probe20261108.md`、`MF-01/runtime078/settings.json`、`probe427-viewers/probe.json` |
| 已有结果 | 有效 `AS_Default` 但 `IsActiveWindow=false`；八类结果计数全 0、文本导出 false；设置与结果接口均无 drawing/image/vector 出口；关闭与断连通过 |
| 可离线补充 | 同上：静态成员清单复核 |
| 外部阻塞 | 正式图纸数据/图像/矢量出口缺失 |
| 解除条件 | 取得正式图纸结果出口与几何身份合同（输入→图纸对应可核） |

## 5. `NS-04.PrescriptionGraphic`

| 项 | 内容 |
| --- | --- |
| 正式成员 | **未在源码中找到** typed 请求 |
| 已有证据 | `development/evidence/NS-04/prescription-graphic-repeat20261108.md`（原始：`.local/evidence/development/NS-03/prescription-graphic-sequential-20261108/summary.json`、`...-nsc-20261108/summary.json`） |
| 已有结果 | 顺序 Cooke：`AS_Default`/`AR_Default` 有效但结构化计数全 0、文本导出 false；纯 NSC 色度样本：`New_Analysis_SettingsFirst` 返回 `null`，无分析对象；两模式关闭/断连通过 |
| 可离线补充 | 复核顺序模式 settings/result 成员（只读） |
| 外部阻塞 | 顺序图形出口缺失；纯 NSC 工厂不可用 |
| 解除条件 | 正式顺序图形导出路径；若 NSC 属声明范围，需受支持工厂 |

## 6. `NS-04.NSCObjectViewer`

| 项 | 内容 |
| --- | --- |
| 正式成员 | **未在源码中找到** typed 请求 |
| 已有证据 | `development/evidence/NS-04/nsc-object-viewer-repeat20261108.md`、`NS-04/runtime066/settings.json`、`runtime068-sequential/summary.json`、`outlets068/summary.json` |
| 已有结果 | 两色样例：Viewer 设置有效且活动、结果 `AR_Default` 有效，但 series/grids/RGB/scatter 全 0、文本导出 false；同工作副本 `get_nsc_objects` 返回 8 个对象及属性（可用的替代数据入口） |
| 可离线补充 | 复核 `get_nsc_objects` 输出与 Viewer 结果的字段差异（只读证据） |
| 外部阻塞 | Viewer 无对象选择/回读与图形结果出口 |
| 解除条件 | 正式对象选择与采用回读 + 可用图形结果出口 |

## 7. `NS-04.PartViewer`

| 项 | 内容 |
| --- | --- |
| 正式成员 | **未在源码中找到** typed 请求 |
| 已有证据 | `development/evidence/NS-04/part-viewer-repeat20261108.md`、`NS-04/runtime066/settings.json`、`runtime068-sequential/summary.json` |
| 已有结果 | 色度样本无部件几何；Boolean Example 4 Lens Mount（RectangularVolume×1、CylinderVolume×3、BooleanNative、NullObject）：`AS_Default`/`AR_Default` 有效且活动但结构化计数全 0、文本导出 false，结果未标识或分组部件；关闭/断连通过 |
| 可离线补充 | 复核部件几何清单与结果字段（只读证据） |
| 外部阻塞 | 无部件选择/回读合同与可用结果出口 |
| 解除条件 | 部件选择/回读合同 + 可用部件数据或图像/矢量出口 |

---

## 8. 本轮离线执行清单（不启动原生）

| 编号 | 内容 | 状态 |
| --- | --- | --- |
| O1 | `pytest tests/unit/test_sag_table.py tests/unit/test_test_plates.py -q` | 待执行 |
| O2 | 样板目录：独立 `parse_tpd` vs 已保存原生行逐行复算（`plates429_native_f9120956a3`） | 待执行 |
| O3 | SagTable：重算 641 摘要 12 项误差与容差判定（`progress641-slope-summary.json`） | 待执行 |
| O4 | SagTable：重算 622 偏移符号/半径差与 piston 基准差（`progress622-dsag-fit.json`） | 待执行 |

结果与实测数值将在执行后补入本文件第 9 节。

---

## 9. 离线执行结果（本轮实测）

脚本：`.local/coordination/pass_d008_offline.py`；结果：`.local/coordination/pass-d008-offline-checks.json`

### 9.1 普通测试

```
pytest tests/unit/test_sag_table.py tests/unit/test_sag_fit.py tests/unit/test_test_plates.py -q
71 passed in 0.56s
```

### 9.2 O2 样板目录独立复算（Applied.tpd）

| 项 | 值 |
| --- | --- |
| TPD 路径 | `C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio\ZemaxData\Testplate\Applied.tpd` |
| 独立解析行数 / 原生行数 | 899 / 899 |
| 半径最大差 | **0.0 mm** |
| 直径最大差 | **0.0 mm** |
| 超容差行数（容差 0.0000500001 mm） | 0 |
| plate_id / availability_code 不一致 | 0 |
| 判定 | **通过** |

原生目录行与独立 TPD 解析在本目录上逐行完全一致（严于 5e-5 容差），活动目录身份 `Applied.tpd` 同时得到佐证。

### 9.3 O3 640/641 斜率摘要复算

| 项 | 值 |
| --- | --- |
| 比较项数 | 12 |
| 最大绝对误差 | **1.6653345369377348e-15** |
| 全部通过（1e-6 + 1e-5×参考） | 是 |
| 与存档判定一致 | 是 |
| 与存档误差值一致（≤1e-18） | 是 |

### 9.4 O4 622 制造偏移/半径复算

| 项 | 值 |
| --- | --- |
| 正负号相反的成对行 | 4 |
| 幅值最大差 | **2.1348433464811814e-11 mm** |
| 半径最大误差 | **5.378943512823753e-09 mm**（门槛 5e-6） |
| 判定 | 符号关系与幅值一致；半径通过 |

结论：**H1/H2 的"基准常数 + 方向约定"假设与已存数据自洽**（同面型内符号相反、幅值相等），但两者之间的**换算合同**仍未由原生出口给出；H3（面型参数化导致 3.8380e-5 mm 半径差）与 H4（反向无摘要）仍需 §1.5 的原生控制实验确认。
