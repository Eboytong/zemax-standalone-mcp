# 四项原生能力移植探查

日期：2026-11-10。源码版本：1.0.0。工作仓库：`C:/Users/tonge/Desktop/mcp`。

本机原生环境为 OpticStudio 2024 R2，ZOS 版本 `24.2.0`，build `240529`；安装目录为 `C:/Program Files/ANSYS Inc/v242/Zemax OpticStudio`。本次核对外部项目源码、当前产品源码、安装程序集，并通过自有 Standalone 实例执行受控模型。

## 1. 结论

| 功能 | 本机结果 | 当前 MCP 状态 | 接入判断 |
|---|---|---|---|
| Atto System Drawing / Unfold | 正式程序集没有 `New_SystemDrawing`，没有同名分析类型；扫描公开方法也没有 SystemDrawing / Unfold 方法 | 已有原生 Cross Section、3D Viewer 等布局导出 | Atto 所示代码无法在本机直接使用；展开设置和 PNG/PDF/EMF 三种原生结果导出均缺少对应入口 |
| Yonggang Detector Viewer | 原生直接查看、Scale、Smoothing、ShowAs、DataType 设置及网格读取实际执行成功 | 已有当前探测器数据读取和 ZRD Replay；显示选项尚未完整开放 | 可接入，复用分析任务、网格分页及结果文件链路 |
| Joey 曲面镀膜性能直接读取 | `ILDERow.GetCoatingPerformanceData()` 和双向 `GetCoatingPerformance` 实际执行成功 | 已有镀膜随角度/波长扫描及 `reverse_direction`；尚无这一直接查询工具 | 可接入，当前 2024 R2 环境即可运行 |
| OptiVibe Gradient2 / Gradient3 | 现有 MCP 接口已完成面型切换、八参数写入回读、变量设置、保存重载、剖面和真实光线计算 | 通用 `update_surfaces` 已可使用；能力说明中的七面型列表没有完整表达这一范围 | 已具备核心功能，主要补充专用参数说明、能力登记和回归用例 |

本次属于移植探查，产品公开工具、请求模型、wheel 和开发完成计数保持原状态。

## 2. 原始证据及复现

- 探针：[probe.py](../../.local/evidence/feature-portability-20261110/probe.py)。
- 最终接口及执行数据：[result.json](../../.local/evidence/feature-portability-20261110/result.json)。
- 探针调试记录：同目录下 `attempt01.json`、`attempt02.json`、`attempt03.json`。
- 原生 Viewer 报告：同目录下 `detector_1.txt`、`detector_2.txt`、`detector_3.txt`。
- Gradient2 / Gradient3 模型：同目录下 `Gradient2.zos`、`Gradient3.zos`。
- 工作副本、检查点、任务和逐光线结果：同目录下 `runs/`。

复现命令，从项目根目录执行：

```powershell
& .\.venv\Scripts\python.exe -B -X utf8 .\.local\evidence\feature-portability-20261110\probe.py
```

最终运行的 53 次 Backend 调用全部返回成功；三个 Viewer 分析对象逐一关闭，应用正常断开，进程退出码为 0。原生库另输出 `FRU__delta_init(): Attempt to start when running!`，保留在本次终端记录中。

探针通过当前产品的 Backend 执行接口；MCP 服务端的部分参数包装在 Backend 边界需展开。前两份调试记录保留包装处理错误。第三份记录保留 Gradient2 参考公式调整前的数据；最终记录采用官方定义，与原生结果对应。

## 3. System Drawing

Atto 的 `zemax_generate_folded_drawing` 调用 `New_SystemDrawing()`，然后依次尝试 `UnfoldSystem`、`Unfold`、`UseUnfoldedSystem`，导出使用 `ExportAsPNG`、`ExportAsPDF`、`ExportAsEMF`。

本机 `ZOSAPI_Interfaces.dll` 的结果为：

- `I_Analyses` 没有 `New_SystemDrawing`。
- 没有对应的 SystemDrawing 设置接口或 AnalysisIDM 成员。
- 扫描公开方法，没有 SystemDrawing 或 Unfold 成员。
- 通用结果接口 `IAR_` 提供 `GetTextFile` 和数据读取，不提供以上三个 `ExportAs*` 方法。
- `ICrossSectionExport`、`I3DViewerExport` 有光线数量和图片导出接口，未提供展开开关。

当前布局适配见 `src/zemax_mcp/exports.py`；有类型请求见 `src/zemax_mcp/export_models.py::LayoutExport`。这条可用路径继续承担普通原生光路图导出。

恢复 System Drawing 专项开发所需材料：正式版本文档或可运行环境中确实存在的创建、展开及导出接口，附对应程序集和最小原生结果。PDF 图片封装与原生矢量 PDF/EMF 分别登记。

## 4. Detector Viewer

使用 SourceRay 发出一条 1 W 光线，DetectorRectangle 位于 Z=10 mm，尺寸 4×6 mm，网格为 5×3。先用现有 `run_nsc_ray_trace` 追迹，再创建 `New_DetectorViewer()`，明确将 `RayDatabaseFilename` 设为空字符串。

| 情况 | 设置与结果 |
|---|---|
| 当前数据，Linear，Smoothing=0 | 返回 5×3 网格和原生报告；中心像素为 62.5 W/cm² |
| 当前数据，Log_Minus_5，Smoothing=2 | 设置按枚举值采用；返回 5×3 网格，原生文本标记平滑次数为 2 |
| 当前数据，Filter=H99 | 字符串可写入和回读；结果与无 Filter 情况相同 |

查看前后通过现有 `get_detector_data` 读取的总功率均为 1 W。三次分析均正常关闭。

官方说明规定 Filter 仅用于光线数据库。当前探测器模式下应限制非空 Filter，ZRD 模式继续使用现有回放链路。

本机枚举存在别名：`Log_Minus_5` 与 `Normalized` 的值同为 1；`IncoherentIrradiance` 回读名称为 `PositionSpace`，枚举值相同。设置采用应比较枚举值。显示网格在对数和光滑模式下会改变，应附显示设置及数据来源；原始辐射度数据继续由 `get_detector_data` 提供。

建议扩展现有分析入口，提供当前数据/ZRD 来源、Detector、ShowAs、DataType、Scale 和 Smoothing，并覆盖非方形网格、枚举别名、显示变换及关闭。本次执行覆盖 Rectangle + FalseColor；其他探测器/ShowAs 组合按其原生结果类型增加用例。

## 5. 镀膜性能直接读取

本机实际接口为：

```python
data = row.GetCoatingPerformanceData()
data.GetCoatingPerformance(angle_degrees, wavelength_um, direction)
# data.Reflection.S / P
# data.Transmission.S / P
# data.Absorption.S / P
```

`direction` 的原生枚举名为 `inward` / `outward`。官方 2024 R1 接口索引已列出该方法，本机 2024 R2 的调用成功。

使用无膜层 N-BK7 平面界面、0.55 µm 波长、0°/30°入射角，两个传播方向共计算四个条件。S/P 反射率与独立 Fresnel 公式的最大差为 `2.636779683484747e-16`；S/P 的 R+T+A 闭合误差最大为 `4.440892098500626e-16`。

30°时的实际反射率为：

| 传播方向 | Rs | Rp |
|---|---:|---:|
| inward | 0.06095558800299922 | 0.026941676879372014 |
| outward | 0.11418575041922545 | 0.004343669708255311 |

本次参考模型为裸界面。多层膜的直接查询可与既有镀膜扫描及独立薄膜参考复用条件进行对照。

当前 `src/zemax_mcp/coatings.py` 已将扫描请求的 `reverse_direction` 写入原生 `ReverseDirection`。新增价值为指定曲面、角度和波长的直接读取，省去创建扫描分析和提取曲线的步骤。可增加有类型同步查询，返回曲面、膜名、波长、角度、方向及 S/P 的 R/T/A；查询对象归属于曲面，无独立分析窗口需要关闭。

## 6. Gradient2 / Gradient3

当前 `SurfacePatch.surface_type` 接受原生面型名称；Backend 检查 `AvailableSurfaceTypes()` 后执行 `ChangeType`，没有用 `SURFACE_TYPES` 的七个名称限制写入。该七项列表位于能力元数据中。

现有接口实际完成：

- Gradient2 / Gradient3 各自八个参数的写入和读取。
- 将 `parameter_3`（Nr2）设置为 Variable。
- 保存和重新打开模型后，八个参数及 Variable 状态保持。
- `grin_profile` 对每类面型返回 101 点曲线，与独立公式逐点最大差均为 0。
- 每类三条真实光线全部成功到达目标面，错误、截断和缺失数量均为 0。

两种面型的参数表：

| 参数 | Gradient2 | Gradient3 |
|---|---|---|
| 1 | Delta T | Delta T |
| 2 | n0，基础折射率的平方 | n0，基础折射率 |
| 3 | Nr2 | Nr2 |
| 4 | Nr4 | Nr4 |
| 5 | Nr6 | Nr6 |
| 6 | Nr8 | Nz1 |
| 7 | Nr10 | Nz2 |
| 8 | Nr12 | Nz3 |

本轮模型使用毫米、Delta T=0.005 mm、厚度2 mm。Gradient2 的 n0 单元格为1.5，轴上实际折射率为 sqrt(1.5)；Gradient3 的 n0 为1.5，另设轴向系数。现有 `update_surfaces` 调用形式如下：

```json
{
  "changes": [{
    "surface": 1,
    "surface_type": "Gradient3",
    "parameters": {"1": 0.005, "2": 1.5, "3": -0.02, "4": 0.001, "5": 0, "6": 0.003, "7": -0.0004, "8": 0.00005},
    "solves": {"parameter_3": {"mode": "variable"}},
    "replace_solves": true
  }]
}
```

建议直接复用现有接口，补充按面型名称显示的参数映射、公式、单位和专用回归测试。若提供命名参数便利接口，保持现有局部修改语义。OptiVibe 将省略项置零和固定 Delta T=1.0 的策略，与当前接口分别处理。

## 7. 接入顺序

1. Gradient2 / Gradient3：现有接口已经可用，补能力说明、参数表和本次模型对应的回归用例。
2. 曲面镀膜直接读取：添加有类型查询和 R/T/A 返回，复用现有薄膜参考。
3. Detector Viewer：扩展显示请求，处理来源条件、枚举别名、不同结果类型及显示网格。
4. System Drawing：待取得正式创建/展开/导出入口后恢复；普通布局继续使用现有原生导出。

## 8. 资料

- [Atto tolerance_tools.py](https://github.com/attoyuan/zemax-opticstudio-mcp/blob/main/tools/tolerance_tools.py)
- [Yonggang nsc.py](https://github.com/YonggangG/Zemax_MCP_Server/blob/main/src/zemax_mcp/zos/subsystems/nsc.py)
- [Joey GetCoatingRtaTool.cs](https://github.com/joeyijun/OpticStudioMCPServer/blob/main/src/ZemaxMCP.Server/Tools/Analysis/GetCoatingRtaTool.cs)
- [OptiVibe grin_surface.py](https://github.com/chuang44-tiff/optivibe-mcp/blob/main/packages/optivibe-harness/src/optivibe_harness/tools/grin_surface.py)
- [官方2024 R1 API成员索引](https://developer.synopsys.com/docs/zos-api-interface-2024-r1/functions_g.xhtml)
- [官方Gradient2定义，2024 R2](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Gradient_2.html)
- [官方Gradient3定义，2024 R2](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Gradient_3.html)
- [官方Detector Viewer说明](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v251/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Detector_Viewer.html)
