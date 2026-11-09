# D005 接口归属纠正报告（MODIFYSETTINGS 键）

- 日期：2026-11-08
- 触发：审查指出 `image_viewers.MODIFY_SETTINGS` 把 `XSE_*` 错配给 ExtendedDiffractionImageAnalysis、把 `PPM_*` 错配给 PartiallyCoherentImageAnalysis
- 结论：**两组映射确属错误，已删除**；同时发现 `IMA_*` 也不是 Geometric Bitmap Image 的键，一并删除。三组错键的真实归属如下，均以手册与源码引用行为据。
- 影响面：`image_viewers.py` 是新增模块，**未接入任何产品路径**（`analyses.py`/`analysis_models.py`/`backend.py`/`imaging.py`/`models.py`/`server.py` 均不引用），本次纠正不改变任何已发布行为；新增守护测试固定这一点。

## 1. 误配原因

`BASE-01/manual349-modifysettings.txt` 是 Programming Tab 的文本导出。该导出**把每个分析的键块排在它自己的标题之前**，标题在键块之后出现。我上一版按“标题在上、键在下”的常规阅读顺序，把每个键块**后面**的标题当成了归属，于是整体错位一格：

| 键块（行号） | 上一版误判归属 | 真实归属（下一行标题） |
| --- | --- | --- |
| `XSE_*` 51–62 | Extended Diffraction Image | **Extended Source Encircled Energy**（标题 63–64） |
| `PPM_*` 286–295 | Partially Coherent Image | **Polarization Pupil Map**（标题 296） |
| `IMA_*` 139–146 | Geometric Bitmap Image | **Geometric Image Analysis**（标题 147） |

佐证该“键在前、标题在后”规则的三处锚点：

1. `DVW_OUTPUTFILE`（第 40 行）紧接标题 `Detector Viewer`（第 41 行）——DVW 只可能是 Detector Viewer。
2. `LSF_*`（65–73）→ 标题 `FFT Line/Edge Spread`（74）；`PSF_*`（75–82）→ 标题 `FFT PSF`（83）；`TFM_*`（148–157）→ 标题 `FFT Through Focus MTF`（158）；`POP_*`（297–300）→ 标题 `PhysicalOpticsPropagation`（301）。全部按“键在前”才自洽。
3. 源码 `src/zemax_mcp/polarization.py:103` 已用 `PPM_SAMP/PPM_FIELD/PPM_WAVE/PPM_SURFACE/PPM_JX/PPM_JY/PPM_PX/PPM_PY/PPM_ADDCONFIG/PPM_SUBCONFIGS` 驱动**既有 PolarizationPupilMap**（`polarization_pupil_map`），与标题 296 一致；`PPM_JX/JY/PX/PY`（Jones 振幅/相位）也只在偏振瞳图有意义，与“部分相干成像”无关。

## 2. 已移除字段

- 从 `extended_diffraction_image` 移除：`XSE_FIELD, XSE_FIELDSIZE, XSE_WAVE, XSE_KRAYS, XSE_IMANAME, XSE_SURFACE, XSE_MAXRAD, XSE_TYPE, XSE_REF, XSE_POLARIZATION, XSE_REMVIGNET, XSE_MULDIFFLI`
- 从 `partially_coherent_image` 移除：`PPM_SAMP, PPM_FIELD, PPM_WAVE, PPM_SURFACE, PPM_JX, PPM_JY, PPM_PX, PPM_PY, PPM_ADDCONFIG, PPM_SUBCONFIGS`
- 从 `geometric_bitmap_image` 移除：`IMA_FIELD, IMA_IMAGESIZE, IMA_IMANAME, IMA_KRAYS, IMA_NA, IMA_OUTNAME, IMA_SURFACE, IMA_PIXELS`

## 3. 纠正后的实际文档依据

| 条目 | 键前缀 | 键块行号 | 标题行号 | 键 |
| --- | --- | --- | --- | --- |
| ExtendedDiffractionImageAnalysis | `EXD_` | 45–48 | 49–50 | `EXD_DISPLAYSIZE, EXD_FIELD, EXD_FILESIZE, EXD_WAVE` |
| PartiallyCoherentImageAnalysis | `PCI_` | 274–283 | 284–285 | `PCI_FIELD, PCI_FILESIZE, PCI_WAVE, PCI_RESAMPLE, PCI_RSNX, PCI_RSNY, PCI_RSDCX, PCI_RSDCY, PCI_RSDLX, PCI_RSDLY` |
| GeometricBitmapImageAnalysis | `GBM_` | 127–136 | 137–138 | `GBM_FIELDSIZE, GBM_RAYS, GBM_XPIX, GBM_YPIX, GBM_XSIZ, GBM_YSIZ, GBM_INPUT, GBM_OUTPUT, GBM_SURFACE, GBM_ROTATION` |
| LightSourceAnalysis | 无 | — | — | 未找到专题键 → **未确认** |
| BitmapFileViewer | 无 | — | — | 未找到专题键 → 未确认 |
| BeamFileViewer | 无 | — | — | 未找到专题键 → 未确认 |

注意：`EXD_*` 只有 4 个键（显示尺寸/视场/文件尺寸/波长），**没有** OTF Grid、Oversampling、Display Resolution 等对话框项的键，因此这些设置在本轮仍属“无 documented 写入口”，不得臆造键名（`XSE_MULDIFFLI` 属于扩展源包围能量，不能借用）。`PPM_*` 属于既有 `polarization_pupil_map` 专题，D005 不得复用；`IMA_*` 属于既有 Geometric Image Analysis，`GBM_*` 才是 Geometric Bitmap Image。

## 4. 已落实的防护

- `image_viewers.KEY_ATTRIBUTION` 记录每个归属的键块行号与标题行号；`FOREIGN_PREFIXES` 列出 `XSE_/PPM_/IMA_/POP_/TFM_/MTF_/LSF_/PSF_` 及其真实归属，防止再次误用。
- 普通测试：
  - `test_modify_settings_use_only_documented_prefixes`（只允许 EXD_/PCI_/GBM_，并逐键集合断言）
  - `test_foreign_key_prefixes_are_never_claimed_by_our_kinds`（任何外来前缀都不出现在我们的键表）
  - `test_attribution_records_the_manual_lines_that_were_checked`（行号固定为 45–48 / 274–283 / 127–136）
  - `test_metadata_is_not_wired_into_product_modules`（产品模块不得 import `image_viewers`）
- 未确认项保持空表：LightSource / BitmapFileViewer / BeamFileViewer 的 `MODIFY_SETTINGS` 仍为 `{}`，`settings_surface(...).writable` 为假。

## 5. 未改变与仍未验收

- 真实文本解析继续保留，并补充了：实际样本回放（`d005-saved-report-parse.json`）、物理轴与尺寸身份（`pixel_size`、`display_pixel_size`、`size_units`、`axes`）、数据类型身份（`value_semantics=relative_intensity`）、非有限值拒绝（`ANALYSIS_TEXT_NON_FINITE`）、形状/像素数一致性（`ANALYSIS_TEXT_SHAPE_MISMATCH`）。
- 六项仍**全部未验收**：原生设置反射、受控 `ModifySettings` 回读（仅 EXD_/PCI_/GBM_ 三组有 documented 键）、查看器显示通道均未运行；`application_create` 前置未解除。
