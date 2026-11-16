# OpticStudio 2026 R1 本机兼容性试验

本文保留最初26个工具的发布版冒烟试验。后续全量回归、补测结果和问题定位见 [全功能试验报告](FULL_COMPATIBILITY_2026R1.md)。

试验日期：2026-11-15（Asia/Shanghai）。

结论：发布版 zemax-standalone-mcp 1.4.0 在本机 OpticStudio 2026 R1 上通过下列功能试验。适配方式为将 `ZEMAX_INSTALL_DIR` 指向本机 v261 安装目录；本次使用仓库附带的正式 wheel，产品源码保持原样。

## 环境与方法

- 仓库：https://github.com/Eboytong/zemax-standalone-mcp
- 检出提交：`6182dd035b51730a71002a04a55b2320cb67ac7d`
- 安装目录：`C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio`
- API 实际返回版本：`26.1.0`；Build：`260127`；许可：`EnterpriseEdition`。
- Python：本项目独立环境中的 CPython 3.14.10 x64。
- 依赖：按仓库 `requirements/all.lock.txt` 安装，包含 MCP 2.3.0、pythonnet 3.2.1、pywin32 312。
- 调用链：MCP Client → stdio 服务 → worker → 本机 .NET Framework ZOS-API → 新建 Standalone 实例。
- 工具发现返回 107 项；实际调用 26 个不同工具，共 62 次调用，最终一轮响应全部 `ok=true`。13 个异步任务均到达 `succeeded`，并取回结果。

## 通过项目

| 项目 | 实际操作与结果 |
| --- | --- |
| 连接与许可 | 创建后台实例，读取版本、许可及系统摘要，正常断开 |
| 顺序建模 | 新建系统、插入曲面、设置孔径与波长、设置曲率/厚度/N-BK7 材料、读取曲面 |
| 镜头文件 | 保存测试 ZOS，并通过服务重新打开 |
| 光线追迹 | 两条光线的批量追迹、单光线追迹 |
| 调焦和像质 | 快速调焦、标准光斑、64×64 FFT MTF |
| 通用分析 | 基点、Seidel 系数、标准 Zernike 系数、相对照度 |
| 图像导出 | 原生截面布局 PNG，1000×600 |
| 优化 | 设置厚度变量、生成 RMS spot 评价函数、运行一轮 DLS 局部优化 |
| 物理光学 | 64×64 POP 传播，取得网格、原生文本和 ZBF 输出 |
| 非序列 | 创建 SourceRay 和 8×8 DetectorRectangle，运行 10 条分析光线并读取探测器 |

## 数值检查

- N-BK7 对称双凸测试镜片：R1=50 mm、R2=-50 mm、中心厚度 5 mm、波长 0.55 μm。基点分析返回焦距 **49.05139286997028 mm**；用 N-BK7 Sellmeier 色散式和厚透镜公式独立计算得到 **49.05139286997028 mm**，通过 1e-6 mm 绝对容差检查。
- FFT MTF 的每组返回曲线在零空间频率处归一化为 **1**，通过 1e-8 绝对容差检查。
- 非序列源功率为 1 W；探测器接收功率为 **0.9999999999999999 W**，通过 1e-8 W 绝对容差检查。
- 局部优化前后评价函数分别为 0.000603378947813533 和 0.0006033789478135297。本案例已先调焦，优化测试记录的是变量、评价函数和优化任务调用流程。

本轮冒烟试验的功能覆盖如表所列。全局/Hammer 优化、公差、STAR、CAD/Speos 导出及其他分析类型已纳入后续全量回归，具体结果见全功能试验报告。

## 配置与复现

客户端配置：`.local/compatibility-2026r1/mcp.config.json`。配置已写入本机 Python 绝对路径及 v261 安装目录，可以将其中的 `zemax` 项加入 MCP 客户端。

直接启动 stdio 服务：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "<REPO>\start-2026r1.ps1"
```

全量回归复现步骤见 [2026 R1 测试说明](docs/compatibility/2026r1/README.md)。

## 记录

- 最终完整调用：`.local/compatibility-2026r1/calls.json`
- 测试汇总及数值检查：`.local/compatibility-2026r1/summary.json`
- 工具完整 schema：`.local/compatibility-2026r1/tools.json`
- 服务日志：`.local/compatibility-2026r1/probe.log`
- 镜头：`.local/compatibility-2026r1/test_lens.zos`
- 布局：`.local/compatibility-2026r1/layout.png`
- 分析原生文本、JSON、ZBF：`.local/compatibility-2026r1/runs/`

早期试验记录保留在同目录。初始脚本使用了错误的分析入口和大小写参数，并遇到客户端 GBK 日志编码错误；这些调用脚本问题均已修正，最终试验进程退出码为 0。试验结束已通过 disconnect 关闭所创建的后台实例。
