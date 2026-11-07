# Zemax Standalone MCP 0.1.61

通过本机 OpticStudio 2024 R2 的 ZOS-API 提供 100 个 MCP 工具和 110 种通用分析请求。服务使用 stdio 协议，通过独立工作进程管理自有后台实例。

[能力说明](能力说明.md) · [工具清单](docs/tools.md) · [请求模型](docs/tool-schemas.json) · [调用约定](docs/usage.md) · [使用示例](examples/README.md)

## 当前状态

发行与源码0.1.61，100工具/110分析；B005已完成10/10并发行。B006仍5/10，目标0.1.62。剩余130条源记录、122个不同编号、120组共同功能；38条历史范围另列。 发行证据见 [release061.json](verification/development/BASE-04/release061.json)。

本批已完成几何壁厚、接触关系、介质区域、源表示、间隙、图像模拟、NSC 镀膜扫描、点云导出及 Universal 1D/2D。各专题的适用条件见能力说明及对应文档。

## 运行环境

- Windows x64、Python 3.14。
- 本机 OpticStudio 2024 R2 及有效 ZOS-API 许可。
- 默认安装目录：`C:\Program Files\ANSYS Inc\v242\Zemax OpticStudio`。

## 安装

在项目根目录运行，PythonExe 填写实际 Python 3.14 x64 可执行文件：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -PythonExe 'C:\Users\tonge\anaconda3\python.exe' -WithReports -WithGeometry
```

脚本使用随包 0.1.61 wheel 创建或复用 `.venv`，安装依赖并生成使用实际绝对路径的 `mcp.config.json`。`-WithReports` 安装绘图/PDF依赖，`-WithGeometry` 安装实体几何依赖；按需使用这两个选项。

## 启动与调用

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\start.ps1
```

将生成的 `mcp.config.json` 中的 `mcpServers` 配置加入支持 stdio 的 MCP 客户端。`mcp.config.example.json` 提供路径模板。服务等待 JSON-RPC 请求，正常启动时保持标准输出用于协议通信。

调用顺序：`connect` → `new_system` 或 `open_lens` → 读取、修改、分析 → `save_lens_as` → `disconnect`。

`run_*` 返回任务编号；通过 `get_task_status` 查询至终态，再调用 `get_task_result`。几何量使用当前镜头单位，波长使用微米，550 nm 输入 `0.55`。默认输出目录为 `outputs/runs`，运行时自动创建。

## 源码使用

修改源码后，在现有环境安装可编辑包：

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[reports,geometry]'
```

## 目录

| 路径 | 内容 |
| --- | --- |
| `src/zemax_mcp/` | MCP 接口、原生适配、任务、几何、绘图与报告 |
| `docs/` | 工具、请求模型、单位及功能专题 |
| `examples/` | 调用脚本和请求模板 |
| `wheels/` | 当前 0.1.61 安装包 |
| `.venv/` | 本机运行环境 |
| `install.ps1`、`start.ps1` | 安装与启动入口 |
| `requirements-*.lock.txt` | 依赖版本约束 |

OpticStudio 商业软件由本机安装提供。


当前开发见[交接](docs/development-handoff.md)，历史材料见[归档索引](docs/history-archive.md)。
