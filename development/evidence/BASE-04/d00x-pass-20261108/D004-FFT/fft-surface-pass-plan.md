# CV-01.FftSurfaceMtf 留存数据独立数值控制实验 — 短计划（第 2 版，按审查收紧）

- 条目：`CV-01.FftSurfaceMtf`（D004 支持；本 worker 仅对**留存数据**做离线数值实验）
- 约束：无新原生、无全量测试、不清理、不 Git、不改产品/公共台账；门槛 **绝对 0.005 保持**
- 定位原则：不因旧 `outputs/...` 路径不存在即判缺失；以实际定位到的文件为准（未做逐字节比对）

## 1. 输入（实际使用的具体路径）

| 材料 | 路径 | 关键内容 |
| --- | --- | --- |
| 605 相干复瞳 | `.local/runs/runs/surface_mtf605_coherent_pupil_7d0d1a6c1d/coherent-pupil.json` | field1/3 的 `MTF_Incoherent`/`Real_Coherent`/`Imaginary_Coherent`（512×512，`values[y][x]`，DC=(255,255)） |
| 610 结论 | `development/evidence/CV-01/progress610-coherent-pupil.json` | field1 max 6.661338147750939e-16；field3 max 4.95019710934963e-03 |
| 509 独立追迹 | `.local/fixtures/surface_mtf509_pupil_3517781fe1/autocorrelation.json` + `field1-rays.json`/`field3-rays.json` | 每场 50613 ray：`hx,hy,px,py`、`position`、`direction`、`opd`、`intensity`、`iy,ix` |

> 605 md 记录的运行目录后缀与本实验实际使用目录不同，本计划以实际定位到的文件为准；未做逐字节比对。

## 2. 基线复现（605，照 test + diffraction_reference 算法）

`pupil=Real+1j·Imag` → `pupil_autocorrelation`（2× 零填充、`/Σ|pupil|²`、`fftshift|·|`）→ 按 DC=(255,255) 裁剪 → 与 `MTF_Incoherent` 比较。预期 field1 6.661338e-16、field3 4.950197e-03。

## 3. 605 单因素对照（网格层，各自只改一项；均标注成立边界）

- **E1 幅度**：E1a 全局标量归一（÷max）——只证明**全局归一不影响**；E1b 分模归一；E1c 相位仅（支持域幅度→1）——若显著变差，说明**原生空间幅度加权起作用**，故不能因 E1a 不变就排除空间幅度。
- **E2 支持域阈值**：在**原生网格**上扫描 t∈{0,1e-10,1e-6,1e-3,1e-2} 置零；只能说明网格层阈值不敏感，**不覆盖投影后支持域差异**。
- **E3 中心/DC**：仅测整数 ±1 像素切片偏移；只能说明整数格点最优，**不排除亚像素/中心因素**。
- **E4 频率节点**：仅比较 `grid.dx` 与 `native_axes.dx` 元数据 → **元数据审计**，不作插值实验。

## 4. 509 实际复算（由 ray 重建 pupil，非读取旧值）

- 用 `iy,ix` 落格、`sqrt(intensity)*exp(2πi·OPD)` 建 256×256 复瞳（intensity 恒 1）；
- `pupil_autocorrelation`；按存留的 **3 种 `frequency_spacing`（paraxial/real/native_cutoff）** 把 10 个频点（原生网格节点）映射到 acf lag 并双线性采样；
- 输出每点 **stored 与 recomputed** 的 reference 与 error，并核对 recomputed 复现 stored；给出各 mode 的 `max_error_stored` 与 `max_error_recomputed`；
- 核验：重建 `pupil_power` 是否等于存档 `pupil_power`（50613）、DC 是否 1。
- 若某参数（如物理频率/参考球/投影常数）未在数据中定义，则列明"正式物理映射/参考球与投影定义未建立"，保留原误差，不虚构。

## 5. 判据与区分

- **诊断**（本实验）：605 网格层四类单因素对残差的影响；509 由 ray 实际重建后 3 种 spacing 的 stored/recomputed 数值。
- **验收（未达成）**：正式物理映射/参考球与投影定义未建立；cross-outlet 0.005 通过不关闭独立参考范围；`completion_count` 保持 0。
- 门槛绝对 0.005 保持。

## 6. 交付
`fft-surface-pass-plan.md`（本文件）、`fft_surface_controls.py`、`fft-surface-controls.json`、`fft-surface-report.md`。
