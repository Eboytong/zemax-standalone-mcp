# D005 最终交付报告（六项图像/查看器分析）

- 日期：2026-11-08
- 工作单元：D001偏振、透射与光纤耦合（模块 worker）
- 分支：`codex/d001-polarization`，基线 `34e1a18`
- 结论：**离线交付完成，原生验收全部待运行**。六项均不声称完成；无提交、无发布、未改公共台账。
- 配套文件：`pass-d005-plan.md`（计划与输入定义）、`pass-d005-items.json`（逐项记录）、`d005-interface-correction.md`（键归属纠正）、`d005-saved-report-parse.json`（真实文本回放结果）、`native-controls-review-report.md`（N1/N2 探针审查修订）

## 1. 六项与已确认接口

| 条目 | AnalysisIDM | analysis_id | 设置对象 | 已确认结果通道 |
| --- | --- | --- | --- | --- |
| BeamFileViewer | `BeamFileViewer` | 96 | 未发现 IAS_ 设置类 | ZBF 图形，文件在 `<pop>` |
| BitmapFileViewer | `BitmapFileViewer` | 62 | `AS_Default` | 仅图像窗口（0 数据表、无文本导出） |
| GeometricBitmapImageAnalysis | `GeometricBitmapImageAnalysis` | 61 | `IAS_GeometricImageAnalysis`（22 个可读写属性） | RGB 数据表（既有适配器） |
| LightSourceAnalysis | `LightSourceAnalysis` | 63 | `AS_Default` | 该系统仅一条有限共轭提示 |
| ExtendedDiffractionImageAnalysis | `ExtendedDiffractionImageAnalysis` | 65 | `AS_Default` | 1 张数据表 + 文本报告 |
| PartiallyCoherentImageAnalysis | `PartiallyCoherentImageAnalysis` | 64 | `AS_Default` | 1 张数据表 + 文本报告 |

接口证据：`BASE-01/probe/api-interfaces.json`（枚举）、`CV-02/probe442-b005/probe.json` 与 `CV-02/bitmap-viewer-repeat-20261108/probe.json`（设置对象反射）。

## 2. 输入定义（按 2024 R2 手册逐条核对）

- **Light Source**（manual042:35792，p.835–836）：NSC 光源光线文件（DAT 或 SDF/TM25RAY 二进制），几何追迹；DAT 跟随系统波长，SDF/TM25RAY 固定用文件内波长；通量单位 W 或 lm；`Fraction` 选取可复现子集；**仅有限共轭**。
- **Partially Coherent**（35877，p.837–843）：IMA/BIM 输入为相对辐照度、存于 `<images>`；ZBF 子集为相对复振幅、存于 `<pop>`；`Data Type` 决定相干性（不相干/相干/原始、传递函数、部分相干像/PSF/Gamma）；`Gamma` 为复相干度形式、`Alpha` 为其尺度、`Fraction` 为包围能量分数；重采样（Number X/Y、Delta X/Y、Decenter X/Y）与 Oversampling、Zero Padding 分属不同阶段。
- **Extended Diffraction**（36225，p.844–846）：仅接受 IMA/BIM，定义像空间理想像；照明须全相干或全不相干；OTF 可随视场变化（OTF Grid）；`Data Type` 为不相干像/相干像，复数 ZBF 只是可选输出。
- **Geometric Bitmap**（35661，p.832–834）：BMP/JPG/PNG 源图，Filed Y Size 定义视场空间尺寸，`Show Source Bitmap` 不追迹光线。
- **Bitmap File Viewer**（36432，p.849）：BMP/JPG/PNG 原样显示、不做处理，存于 `<images>`。
- **Beam File Viewer**（38246，p.886）：ZBF 存于 `<pop>`，设置为 POP 的子集。

## 3. MODIFYSETTINGS 键归属（已纠正）

手册导出**把键块排在其标题之前**（`DVW_OUTPUTFILE` 行 40 → `Detector Viewer` 行 41 为锚点）。据此：

| 条目 | 前缀 | 键块行 | 标题行 |
| --- | --- | --- | --- |
| Extended Diffraction Image | `EXD_` | 45–48 | 49–50 |
| Partially Coherent Image | `PCI_` | 274–283 | 284–285 |
| Geometric Bitmap Image | `GBM_` | 127–136 | 137–138 |
| Light Source / Bitmap File Viewer / Beam File Viewer | 无 | — | — |

上一版把 `XSE_*`（扩展源包围能量）、`PPM_*`（偏振瞳图，已由 `polarization.py` 使用）、`IMA_*`（Geometric Image Analysis）错配给上述条目，**已全部删除**，详见 `d005-interface-correction.md`。`EXD_` 仅 4 个键，OTF Grid、Oversampling、Display Resolution 等无 documented 写入口，保持"未确认"。

## 4. 已交付的离线产物

- `src/zemax_mcp/image_viewers.py`（共享补丁，**未接入产品路径**，有守护测试）：分析 ID、`settings_surface`、纠正后的 `MODIFY_SETTINGS`、`KEY_ATTRIBUTION`/`FOREIGN_PREFIXES`、`source_file_identity`、`bitmap_identity`/`sniff_bitmap_header`、`declared_scope`（`verified=False`）、三个解析器。
- 解析器能力：真实 UTF-16 报告回放；物理轴与尺寸身份（`pixel_size`、`display_pixel_size`、`size_units`、`axes`）；数据类型身份（`value_semantics=relative_intensity`）；非有限值拒绝 `ANALYSIS_TEXT_NON_FINITE`；形状/像素数一致性 `ANALYSIS_TEXT_SHAPE_MISMATCH`；相干性文字精确行匹配（避免"相干成像"命中"部分相干成像"）。
- `scripts/probes/D005/parse_saved_reports.py`：离线控制探针，解析 probe442 三份真实报告并输出 `d005-saved-report-parse.json`。

## 5. 实际运行过的检查

| 检查 | 结果 |
| --- | --- |
| `tests/unit/test_image_viewers.py` | 53 passed |
| 组合套件（D001 四解析 + native_controls + polarization + transmission_fan + image_viewers） | 220 passed in 1.96s（在探针审查修订前运行；本轮只改探针脚本与探针测试，不触及产品模块） |
| `scripts/probes/D005/parse_saved_reports.py` | 三份报告全部解析成功，`application_created=false` |
| `tests/unit/test_native_controls.py`（审查后定向） | 41 passed |

## 6. 未验证与阻塞

1. **原生执行全部未运行**：`application_create` 三次 180 s 超时（证据 `development/evidence/BASE-04/runtime-phase-environment-20261108.md`）。D5-B1…D5-B6 仍为 `not_run`。
2. 无 documented 键的三项（Light Source、Bitmap File Viewer、Beam File Viewer）只能声明"无可写选择面"，不得按名称联想补键。
3. 六项的 `verified` 均为 `false`；查看器完整声明范围未验收。
4. 未提交 Git、未改公共台账；`pytest-of-tonge/` 残留未清理（按要求留给协调者）。

## 7. 逐项验收门槛（`verified` 置真条件）

单项要把 `verified` 置真，必须**同时**满足下列四类条件，缺一不可；只拿到一条原生回执不足以置真：

1. **输入身份**：该项声明的输入被原生确认为同一身份——容器（`<images>` / `<pop>`）、数值语义（相对辐照度 / 相对复振幅 / 光线表 / RGB）、波长归属（DAT 跟随系统波长，SDF/TM25RAY 用文件内波长）、尺寸与像素标定（宽 ÷ 像素）。
2. **设置实际采用**：受控写入后回读证明设置被采纳——`EXD_*` / `PCI_*` / `GBM_*` 三组 documented 键需 `ModifySettings` 写入且回读一致；`IAS_GeometricImageAnalysis` 走属性写入 + 回读；无 documented 键的三项只能记为"无可写选择面"，不得用默认值冒充已验证设置。
3. **有效结果/参考**：产出与参考可比——数据表维度与统计同离线解析一致，或与独立参考（手册公式、受控样本）在声明容差内一致；文本报告头（波长、视场、宽/像素、相干性文字）与所用设置一致。
4. **分页与生命周期**：`get_task_result` 分页游标严格前进且行数与声明一致；任务终态明确（成功/失败/取消），取消与断开回执字段已确认，无遗留活动原生任务。

任一类缺失时，该项保持 `verified=false`，并在 `pass-d005-items.json` 中记录缺失类别与证据缺口。原生应用可创建后按 D5-B1…D5-B6 逐项执行上述四类检查。
