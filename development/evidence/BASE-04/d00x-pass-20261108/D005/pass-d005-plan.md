# D005 短计划（修订版：先纠正输入定义，再补离线可执行件）

- 权威计划：主区 `development/tracking/d00x-pass-20261108.json`（D005 六项，worker `zemax-p01-polarization`）
- 本轮约束：**不创建 OpticStudio 应用**；只用已保存的正式 XML/手册、已有探查与真实文本确认正式接口
- 修订原因：上一版把 LightSource/ExtendedDiffraction/PartiallyCoherent 的输入与相干条件写错（见 §1），本版以手册原文与真实报告纠正
- 交付：本文件 + 六项可执行解析/契约/控制探针 + 普通检查 + `pass-d005-items.json`（本轮末更新）

## 1. 输入定义纠正（手册原文为准）

### 1.1 LightSourceAnalysis（手册 p.835–836，`EXT-EXPORT/manual042.txt:35792`）
- **不是**“系统源光线文件经顺序系统成像”的泛称，而是：以 **NSC Source File 的 ray list 作为光源**，在顺序系统中做纯几何光线追迹成像。
- **文件身份**：`DAT` / `SDF` / `TM25RAY` 源文件（**仅支持二进制 ray 文件**）。DAT 与 SDF/TM25RAY 的波长语义不同：
  - DAT：可用系统单个波长（单色），也可用系统已定义波长与权重；
  - SDF/TM25RAY：**始终用文件内波长**，忽略系统波长设置。
- **波长采用**：由上述规则决定，不是新选波长。
- **像素与通量**：X/Y Pixels 与 X/Y Pixel Size 决定探测器；Units 选 Watts（辐射）或 Lumens（光度，且此时 Show As 才支持 True Color）；`Fraction` 只追迹文件中该比例的射线（随机但可复现）；`Use Polarization` 时因源文件不含偏振数据而**随机赋偏振**。
- **几何假设**：所选视场点为文件所有光线的原点，源坐标系 +Z 与物面 +Z 平行；Rotation 绕该原点逆时针旋转；需配合 Apply Fixed Apertures 否则会越过顺序孔径。
- **适用范围（真实文本证据）**：`probe442-b005/LightSourceAnalysis.txt` 仅一行 `仅有限共轭系统可以使用该功能.` → **仅有限共轭系统可用**，无限共轭时光线文件无法按此方式成像。
- **输出**：可选写出 BMP/JPG/PNG 到 `<images>`；`Output` 只允许文件名、无路径。

### 1.2 ExtendedDiffractionImageAnalysis（手册 p.844–846，`manual042.txt:36225`）
- 输入是**扩展源图像 IMA/BIM**（非 ZBF），描述**像空间**理想像（与 Geometric Image 的 field 空间定义相反）。
- 与 Partially Coherent 的差别：**OTF 可随视场变化**；**照明必须是完全相干或完全非相干**（不支持部分相干）。
- Data Type 只有 **incoherent image / coherent image** 两种；不存在“只有复 PSF”的说法——复振幅只是可选 `Output File`（ZBF）的副产物。
- 关键设置：File Size、Oversampling、Display Size、OTF Sampling、**OTF Grid**（OTF 随视场变化的采样）、Resolution、Use Delta Functions、Consider Distortion、Use Relative Illumination（按相对照度对 OTF 加权）。
- 真实报告头（`probe442-b005/ExtendedDiffractionImageAnalysis.txt`）：波长/位置、`光源 : 0.0500 毫米 宽, 7 乘 7 像素`、`显示: 0.1000 毫米 宽, 256 乘 256 像素`、`包含像差`，随后 256×256 强度网格。

### 1.3 PartiallyCoherentImageAnalysis（手册 p.837–843，`manual042.txt:35877`）
- 输入按扩展名分流，**不能混为一谈**：
  - `IMA`/`BIM`：描述待成像物体，数值单位为**相对辐照度（intensity）**，必须位于 `<images>`；
  - `ZBF`：仅支持**子集**，数值单位为**相对复振幅（complex amplitude）**，必须位于 `<pop>`；仅当 Data Type 为完全相干或非相干图像时，结果复振幅才可再存为 ZBF（且零填充后总像素须为 2 的幂）。
- **Data Type** 才是相干性开关：incoherent/coherent/raw image、incoherent/coherent transfer function、transform of raw image，以及 **partially coherent image（mostly coherent / mostly incoherent）、partially coherent PSF、gamma**。
- **Gamma / Alpha / Fraction** 的含义：Gamma 是复相干度函数形式；Alpha 是该函数的尺度参数；Fraction 是 PSF/Gamma 中参与计算的**包围能量比例**。三者都**不是**“相干长度/光谱”这类自造字段。
- **重采样**：Resample Image + Number X/Y、Delta X/Y、Decenter X/Y；仅对相干/非相干/raw/部分相干空间域图像可用。另有 Oversampling、Zero Padding（IMA/ZBF 有效，BIM 无效；奇数像素 2n-1、偶数 2n）、OTF Sampling。
- 真实报告头（`probe442-b005/PartiallyCoherentImageAnalysis.txt`）：`0.5500 μm对于0.00 (度)。`、`宽度是 1.8571 毫米, 13 以 13像素.`、`非相干成像`、`包含像差`，随后 13×13 强度网格。

### 1.4 三个查看器/几何位图
- **Geometric Bitmap Image Analysis**（p.832–834）：源为 **BMP/JPG/PNG**（`<images>`），field 空间尺寸由 Field Y Size 定义；输出 RGB 网格；`Show Source Bitmap` 可只画源位图不追迹（校验读取）。
- **Bitmap File Viewer**（p.849）：**仅显示** JPG/BMP/PNG，**无任何处理**，文件须在 `<images>`；真实探查为 `AS_Default`、0 网格、无文本导出 → 结果只在图像窗口。
- **Beam File Viewer**（p.886）：查看/分析 **ZBF**（`<pop>`），设置是 POP 的子集；真实探查无独立设置类。
- **IMA and BIM File Viewer**（p.848，同族但非本六项）仅作对照。

## 2. 已确认的正式接口（离线证据，未创建应用）

| 条目 | AnalysisIDM 枚举值 | 设置类（已有探查） | 结果通道 | 证据 |
| --- | --- | --- | --- | --- |
| LightSourceAnalysis | 63 | `AS_Default` | 1 条 message + 文本；网格 0 | `probe442-b005/probe.json`、`api-interfaces.json` |
| PartiallyCoherentImageAnalysis | 64 | `AS_Default` | 1 个 DataGrid + 文本 | 同上 |
| ExtendedDiffractionImageAnalysis | 65 | `AS_Default` | 1 个 DataGrid + 文本 | 同上 |
| BitmapFileViewer | 62 | `AS_Default` | 0 网格、无文本 | `bitmap-viewer-repeat-20261108/probe.json` |
| BeamFileViewer | 96 | 未见独立设置界面 | 未探查 | `api-interfaces.json`（无对应 IAS_ 类） |
| GeometricBitmapImageAnalysis | 61 | `IAS_GeometricImageAnalysis`（有公开属性） | RGB DataGrid | `analyses.py`/`imaging.py`、`api-interfaces.json` |

关键结论：`api-interfaces.json` 的 77 个 `ZOSAPI.Analysis.Settings.*` 中**没有** LightSource/ExtendedDiffraction/PartiallyCoherent/BitmapViewer/BeamViewer 的设置类，与探查处 `AS_Default` 一致 → 这五项**只能**靠 documented `MODIFYSETTINGS` 键（下表）或默认值，禁止臆造属性名。

## 3. documented MODIFYSETTINGS 键（`BASE-01/manual349-modifysettings.txt`）

该导出中**每个分析的键块排在其标题之前**（锚点：`DVW_OUTPUTFILE` 行 40 后接标题 `Detector Viewer` 行 41；`POP_*` 行 297–300 后接 `PhysicalOpticsPropagation` 行 301）。据此逐条核对归属与行号：

| 条目 | 键前缀 | 键块行号 | 标题行号 |
| --- | --- | --- | --- |
| Extended Diffraction Image Analysis | `EXD_` | 45–48 | 49–50 |
| Partially Coherent Image Analysis | `PCI_` | 274–283 | 284–285 |
| Geometric Bitmap Image Analysis | `GBM_` | 127–136 | 137–138 |
| Light Source / Bitmap File Viewer / Beam File Viewer | 无 | — | — |

- `EXD_DISPLAYSIZE, EXD_FIELD, EXD_FILESIZE, EXD_WAVE`（**没有** OTF Grid / Oversampling / Resolution 的键）
- `PCI_FIELD, PCI_FILESIZE, PCI_WAVE, PCI_RESAMPLE, PCI_RSNX, PCI_RSNY, PCI_RSDCX, PCI_RSDCY, PCI_RSDLX, PCI_RSDLY`
- `GBM_FIELDSIZE, GBM_RAYS, GBM_XPIX, GBM_YPIX, GBM_XSIZ, GBM_YSIZ, GBM_INPUT, GBM_OUTPUT, GBM_SURFACE, GBM_ROTATION`

**不得复用**他人键：`XSE_*` 属 Extended Source Encircled Energy（51–62 / 标题 63–64），`PPM_*` 属 Polarization Pupil Map（286–295 / 标题 296，已被 `polarization.py` 使用），`IMA_*` 属 Geometric Image Analysis（139–146 / 标题 147）。纠正经过与依据见 `d005-interface-correction.md`。

Light Source / Bitmap File Viewer / Beam File Viewer **没有** documented 键 → 保持“无可写选择面、未确认”，不得按名称联想补键。

## 4. 本轮实施内容（离线可执行）

1. `src/zemax_mcp/image_viewers.py`（共享补丁，单独列出，**未接入产品路径**）：
   - `ANALYSIS_IDS`、`settings_surface`（有/无公开属性类）、`MODIFY_SETTINGS`（仅上述已核对归属的键）、`KEY_ATTRIBUTION`/`FOREIGN_PREFIXES`（归属行号与外来前缀防护）
   - `parse_extended_diffraction_text` / `parse_partially_coherent_text` / `parse_light_source_text`：真实样本可回放，并输出物理轴/尺寸（`pixel_size`、`display_pixel_size`、`size_units`、`axes`）、数据类型身份（`value_semantics=relative_intensity`）、非有限值拒绝与形状一致性校验
   - `source_file_identity(name)` / `bitmap_identity(name, data)`：容器（`images`/`pop`）、数值语义（intensity/complex amplitude/ray list）、位图头尺寸与后缀一致性
   - `declared_scope(kind)`：声明范围 + `verified=False`
2. `scripts/probes/D005/parse_saved_reports.py`：对 `probe442-b005` 三份真实报告离线解析并落 JSON（控制探针，不建应用）
3. `tests/unit/test_image_viewers.py`：契约/解析/身份/键表测试 + 真实证据解析测试（文件缺失时 skip）
4. 保留：`geometric_bitmap_image` 既有适配器与测试不动（仅在缺断言时补）；`beam_files`/`ima_viewer` 既有能力不重复造测试。

## 5. 未运行的原生作业与解除条件

- 原生作业：六项的 settings 反射/CFG、真实结果网格抓取、查看器显示通道（BitmapFileViewer 无文本）。
- 解除条件：`application_create` 恢复后，按 `N1` 式反射确认无设置类；对 Extended/PartiallyCoherent 用 documented 键做一次受控 `ModifySettings` + 读回；对查看器抓取窗口图像或确认仅图像通道。
- 本轮不申报任何一项 done；查看器“完整声明范围”保持未验收。
