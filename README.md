# Zemax Standalone MCP

**1.4.1** 默认使用 **OpticStudio 2026 R1（v261）** 和 **compact** 工具目录。发行包等待整合与回归完成后生成。升级前原生测试记录为845通过、48失败、11跳过或预期限制，见 [2026 R1 测试与升级计划](docs/compatibility/2026r1/README.md)。

**1.4.1** defaults to **OpticStudio 2026 R1 (v261)** and the **compact** tool catalog. Distribution artifacts will be built after integration and regression testing. The pre-upgrade native baseline recorded 845 passed, 48 failed, and 11 skipped/expected limitations. See the [2026 R1 test report and roadmap](docs/compatibility/2026r1/README.md).

[中文](#中文) · [English](#english)

<a id="中文"></a>

## 中文

Zemax Standalone MCP 是运行于 Windows x64、Python 3.14 与 OpticStudio 2026 R1 的 stdio MCP 服务。当前源码版本为 **1.4.1**，提供 **107 项工具操作**与 **146 种 `run_analysis` 请求类型**；接口、适用条件和结果格式见使用文档与工具参考。

提供两种工具披露模式：默认`compact`提供11个搜索、执行和任务控制入口，按需读取单项schema，全部能力保持可调用；显式选择`full`直接提供107个工具。Agent可自行组合原生建模、评价、优化和公差工具，也可选择候选管理、材料搜索等工程快捷流程。

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

1.4.1 Windows ZIP 的生成与目录布局见[发行包指南](docs/guides/windows-distribution.md)。

准备 Windows x64、Python 3.14 x64、OpticStudio 2026 R1 和适用的 ZOS-API 许可。解压发行 ZIP，进入其中的 `zemax-standalone-mcp-1.4.1-windows-x64` 目录，在 PowerShell 中安装：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -PythonExe python
```

`python` 应指向 Python 3.14 x64；也可将它替换为该版本 `python.exe` 的绝对路径。需要报告和几何相关可选依赖时，在命令末尾添加 `-WithReports -WithGeometry`。脚本安装 `releases/1.4.1/` 中的 wheel，按锁定依赖下载所需包，并生成 `.local/config/mcp.config.json`。源码安装使用相同命令，需先由发行构建流程生成 wheel。

默认使用`compact`。需要直接披露全部工具时，在安装命令末尾添加`-ToolMode full`。模式优先级为显式`-ToolMode`、`ZEMAX_TOOL_MODE`环境变量、默认值；安装目录、输出目录和状态目录也采用已有环境值。客户端配置变更后重启MCP连接。调用方式与示例见[能力搜索及渐进式披露](docs/guides/capability-search.md)。

将生成配置中的 `zemax` 项添加到 MCP 客户端配置；安装目录不同时修改 `ZEMAX_INSTALL_DIR`。客户端启动后调用 `connect`；通过 `execute_capability` 调用 `tool:open_lens`，通过 `query_capability` 调用 `tool:get_system_summary`。执行分析后，通过 `get_task_status` 查询至终态，再用 `get_task_result` 读取结果；结束时调用 `disconnect`。完整调用与分页规则见[使用指南](docs/guides/usage.md)。

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

`.local/runs`为默认运行目录；`.local/state`为状态目录。显式环境变量优先采用。1.4.1 wheel生成于`releases/1.4.1/`。`start-2026r1.ps1`默认使用`.local/runs-2026r1`和`.local/state-2026r1`，并采用已有环境值。

## 许可证与参考

本项目采用 [MIT 许可证](LICENSE)，版权所有 © 2026 Tongeb。运行需要单独安装 Ansys Zemax OpticStudio，并具备适用的 ZOS-API 许可。第三方依赖遵循各自许可证。

接口与方法参考包括 [Yonggang Zemax MCP](https://github.com/YonggangG/Zemax_MCP_Server)（MIT）、[Joey OpticStudio MCP](https://github.com/joeyijun/OpticStudioMCPServer)（MIT）、[OptiVibe MCP](https://github.com/chuang44-tiff/optivibe-mcp)（Apache-2.0）和 [OptiForge](https://github.com/zhaopeizhao41-ops/optiforge)（MIT）。出处及采用方式见[源码参考记录](development/github-references.md)。

---

<a id="english"></a>

## English

Zemax Standalone MCP is a stdio MCP server for **Windows x64, Python 3.14, and OpticStudio 2026 R1**. Source version **1.4.1** provides **107 tool operations** and **146 `run_analysis` request types**. The references describe exact parameters, results, and operating conditions.

Two tool disclosure modes are available. The default `compact` mode exposes 11 discovery, invocation, connection, and task-control tools; agents retrieve individual schemas as needed and can access the same capabilities. Explicit `full` mode exposes 107 tools directly. Agents can compose native modeling, evaluation, optimization, and tolerancing tools or select optional engineering workflows.

### Capabilities

Read and modification tools return responses directly. Long-running operations return task IDs for status polling and result retrieval.

| Category | Available capabilities |
| --- | --- |
| Connections and projects | Connect to and close Standalone instances; create, open, save, copy, and archive lens files; inspect units, wavelengths, fields, configurations, and external dependencies. |
| Sequential modeling | Read, insert, copy, delete, and update surfaces; control radii, thicknesses, materials, apertures, coordinates, pickups, and solves; manage configurations, variables, and merit functions. |
| Non-sequential modeling | Read, insert, copy, delete, and modify NSC objects; perform sequential/non-sequential conversions; read object geometry and detector data. |
| Ray tracing and propagation | Batch sequential and NSC ray tracing; ZRD reading and replay; POP propagation and convergence analysis; ZBF complex-field reading. |
| Imaging and optical quality | Spot diagrams, FFT MTF, relative illumination, wavefront, RMS, distortion, field curvature, PSF, FWHM, Seidel, polarization, and material analyses; curves, grids, text, and paginated results. |
| Optimization and design | Local, global, Hammer, and multistart optimization; optimization wizards and merit-function editing; quick focus, parameter scans, and catalog lens search and evaluation. |
| Tolerancing and manufacturing | TDE tolerances and compensators; sensitivity, inverse sensitivity, and Monte Carlo analysis; yield and quantile summaries. |
| Exports and reporting | Layouts, analysis images, CAD, Speos, point clouds, reports, detector data, merit and tolerance files; completed analysis results exported as Markdown, JSON, or CSV. |
| Engineering search and design improvement | Capability discovery, including Chinese queries; candidate snapshots, branches, restoration, and comparison; joint glass replacement; OPD targets and geometric constraints; fixed-tolerance design optimization with independent yield validation; surface-by-surface polarized ray loss. |
| Engineering calculations | Manufacturing geometry thresholds, POP fiber alignment, fixed-stack coating optimization, NSC efficiency and uniformity, glass trials, scan-pupil conjugacy, ghost paths, confocal pinhole response, uniform-temperature focus compensation, multiobjective candidates, tolerance cost budgets, and dual-FSM offline control. |
| Task control | Task status, historical results, supported cancellation, and pagination for curves, rows, and two-dimensional grids. |

### Installation

Prepare Windows x64, Python 3.14 x64, and OpticStudio 2026 R1 with an applicable ZOS-API license. Extract the Windows ZIP, open its `zemax-standalone-mcp-1.4.1-windows-x64` directory, and run in PowerShell. See the [distribution guide](docs/guides/windows-distribution.md) for build instructions and package layout.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -PythonExe python
```

`python` must resolve to Python 3.14 x64; an absolute path to its executable can also be supplied. Add `-WithReports -WithGeometry` for optional reporting and geometry dependencies. The installer installs the wheel from `releases/1.4.1/`, downloads dependencies using the included locks, and writes `.local/config/mcp.config.json`. Repository installation uses the same command after the release build produces the wheel.

Compact is the default. Add `-ToolMode full` to expose every tool directly. Mode precedence is explicit `-ToolMode`, then `ZEMAX_TOOL_MODE`, then the default. The installer also honors existing install, output, and state directory environment values. Restart the MCP connection after changing client configuration. See [capability discovery and progressive disclosure](docs/guides/capability-search.md).

### Client configuration and first use

Add the generated configuration's `zemax` entry to your MCP client's server configuration. Adjust `ZEMAX_INSTALL_DIR` if OpticStudio is installed elsewhere. The [configuration template](examples/config/mcp.config.example.json) shows the executable, arguments, and environment settings. Clients with another configuration format should use the same executable, arguments, and environment values.

1. Call `connect`.
2. Invoke `tool:open_lens` through `execute_capability` with an absolute lens-file path, or invoke `tool:new_system`.
3. Invoke `tool:get_system_summary` through `query_capability` and run the required analysis through `execute_capability`.
4. Poll `get_task_status` until the task reaches a terminal state, then retrieve its output with `get_task_result`.
5. Call `disconnect` when finished.

In compact mode, use `search_capabilities` and `get_capabilities` to obtain an individual contract, then invoke it through `query_capability` or `execute_capability`. Task-control tools remain directly available.

The stdio server can also be started with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

The default output directory is `.local/runs`; state is stored in `.local/state`. Explicit environment variables take precedence. The 1.4.1 wheel is built under `releases/1.4.1/`. `start-2026r1.ps1` defaults to `.local/runs-2026r1` and `.local/state-2026r1` and honors existing environment values.

### Documentation and repository layout

Detailed guides and topic documentation are currently primarily in Chinese. Tool names, schemas, and request examples provide the exact callable interfaces.

- [User documentation](docs/README.md) · [Tool reference](docs/reference/tools.md) · [Request schemas](docs/reference/tool-schemas.json)
- [Capabilities and conditions](docs/reference/capabilities.md) · [Usage and pagination](docs/guides/usage.md)
- [Examples](examples/README.md) · [Tests](tests/README.md)

| Directory | Contents |
| --- | --- |
| `src` | Product source code |
| `docs` | User guides, interfaces, and topics |
| `development` | Development records and evidence |
| `tests` | Unit and native tests with shared references |
| `scripts` | Maintenance, probes, and release utilities |
| `examples` | Workflows, requests, and controlled inputs |
| `requirements` | Locked dependencies |
| `releases` | Released wheels |
| `.local` | Local runs, state, reproduction data, and archives |

### License and acknowledgments

This project is licensed under the [MIT License](LICENSE). Copyright © 2026 Tongeb. Running it requires a separately installed Ansys Zemax OpticStudio and an applicable ZOS-API license. Third-party dependencies retain their own licenses.

Interface and method references include [Yonggang Zemax MCP](https://github.com/YonggangG/Zemax_MCP_Server) (MIT), [Joey OpticStudio MCP](https://github.com/joeyijun/OpticStudioMCPServer) (MIT), [OptiVibe MCP](https://github.com/chuang44-tiff/optivibe-mcp) (Apache-2.0), and [OptiForge](https://github.com/zhaopeizhao41-ops/optiforge) (MIT). See the [source reference register](development/github-references.md) for provenance and how each reference was used.
