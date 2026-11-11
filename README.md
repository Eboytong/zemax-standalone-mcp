# Zemax Standalone MCP

Zemax Standalone MCP 是运行于 Windows x64、Python 3.14 与 OpticStudio 2024 R2 的 stdio MCP 服务。当前发布版本为 **1.4.0**，提供 **107 个工具**与 **146 种 `run_analysis` 请求类型**；接口、适用条件和结果格式见使用文档与工具参考。

提供两种工具披露模式：默认`full`直接提供107个工具；`compact`先提供11个搜索、执行和任务控制入口，按需读取单项schema，全部能力保持可调用。Agent可自行组合原生建模、评价、优化和公差工具，也可选择候选管理、材料搜索等工程快捷流程。

## 可以用它做什么

通过 MCP 客户端连接后，可以调用本机 OpticStudio 完成下列工作。读取和修改类工具直接返回结果；长时间运行的任务返回任务编号，供后续查询状态和结果。

| 工作类别 | 可用能力 |
| --- | --- |
| 连接与工程管理 | 连接或关闭 Standalone 实例；新建、打开、另存、复制和归档镜头；读取系统摘要、单位、波长、视场、配置和外部依赖。 |
| 顺序系统建模 | 读取、插入、复制、删除和批量修改曲面；设置曲率、厚度、材料、孔径、坐标、拾取与求解；管理多重结构、变量和评价函数。 |
| 非序列系统建模 | 读取、插入、复制、删除和修改 NSC 对象；执行顺序/非序列转换；读取对象几何和探测器数据。 |
| 光线追迹与光束传播 | 执行顺序批量光线追迹、非序列光线追迹、ZRD 回放与读取；执行 POP 物理光学传播及收敛分析；读取 ZBF 复场文件。 |
| 成像与像质分析 | 运行光斑、FFT MTF、相对照度、波前、RMS、畸变、场曲/畸变、PSF、FWHM、Seidel、偏振和材料相关分析；结果支持曲线、网格、文本报告和分页读取。 |
| 优化与设计辅助 | 运行局部、全局、Hammer 与多起点优化；生成或编辑优化向导和评价函数；执行快速调焦、参数扫描、目录镜头检索与评价。 |
| 公差与制造分析 | 编辑 TDE 公差与补偿器；运行灵敏度、逆灵敏度和 Monte Carlo 公差分析；汇总通过率和分位数结果。 |
| 数据、图像与交付 | 导出布局、分析图像、CAD、Speos、点云、报告、探测器数据、评价函数和公差文件；以 Markdown、JSON 或 CSV 导出已完成的分析结果。 |
| 工程搜索与设计改进 | 按中文需求搜索能力；保存、分支、恢复和同条件比较候选；多镜片联合换玻璃；构建OPD目标和几何约束；固定公差优化设计并独立验证良率；逐面统计偏振光线损耗。 |
| 工程计算 | 制造几何阈值、POP光纤对准、固定膜系优化、NSC效率与均匀性、材料替换试算、扫描瞳共轭、鬼像路径、共焦针孔响应、均温焦点补偿、多目标候选、公差成本预算及双FSM离线控制。 |
| 任务控制 | 查询任务状态、读取历史结果、取消可取消任务，并对曲线、行数据和二维网格进行分页读取。 |

能力搜索、候选比较、材料搜索和鲁棒设计的调用流程见[工程指南](docs/README.md)。

完整工具名、参数、单位和适用条件见 [工具参考](docs/reference/tools.md)、[请求 schema](docs/reference/tool-schemas.json) 与 [能力说明](docs/reference/capabilities.md)。


- [使用文档](docs/README.md) · [工具参考](docs/reference/tools.md) · [请求schema](docs/reference/tool-schemas.json)
- [调用示例](examples/README.md) · [测试说明](tests/README.md)

## 安装和连接

[下载1.4.0安装包](https://github.com/Eboytong/zemax-standalone-mcp/releases/tag/v1.4.0)

准备 Windows x64、Python 3.14 x64、OpticStudio 2024 R2 和适用的 ZOS-API 许可。在仓库根目录的 PowerShell 中运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -PythonExe python
```

`python` 应指向 Python 3.14 x64；也可将它替换为该版本 `python.exe` 的绝对路径。需要报告和几何相关可选依赖时，在命令末尾添加 `-WithReports -WithGeometry`。脚本安装 `releases/1.4.0/` 中的 wheel，并生成 `.local/config/mcp.config.json`。

需要精简初始工具目录时，在安装命令末尾添加`-ToolMode compact`。已有配置可在env中设置`ZEMAX_TOOL_MODE=compact`并重启MCP连接。调用方式与示例见[能力搜索及渐进式披露](docs/guides/capability-search.md)。

将生成配置中的 `zemax` 项添加到 MCP 客户端配置；安装目录不同时修改 `ZEMAX_INSTALL_DIR`。客户端启动后依次调用 `connect`、`open_lens`（使用镜头文件的绝对路径）、`get_system_summary`。执行分析后，通过 `get_task_status` 查询至终态，再用 `get_task_result` 读取结果；结束时调用 `disconnect`。完整调用与分页规则见[使用指南](docs/guides/usage.md)。

也可运行 `powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1` 启动 stdio 服务，供 MCP 客户端连接。

| 目录 | 用途 |
| --- | --- |
| src | 产品源码 |
| docs | 使用指南、接口和专题 |
| development | 计划、台账、证据和交接 |
| tests | 普通/原生测试与共享参考 |
| scripts | 开发统计、探查和发行工具 |
| examples | 工作流、请求和输入资源 |
| requirements | 锁定依赖 |
| releases | 已发行wheel |
| .local | 本机运行、状态、复现数据和历史归档 |

`.local/runs`为默认运行目录；`.local/state`为状态目录。显式环境变量优先采用。当前默认wheel位于`releases/1.4.0/`。
