# Windows发行包 / Windows distribution

1.4.2发行构建生成以下产物：

- `releases/1.4.2/zemax_standalone_mcp-1.4.2-py3-none-any.whl`
- `releases/1.4.2/zemax-standalone-mcp-1.4.2-windows-x64.zip`

ZIP中只有一个同名顶层目录，包含`install.ps1`、`start.ps1`、`start-2026r1.ps1`、双语README、MIT LICENSE、`requirements/*.lock.txt`、`examples/config/mcp.config.example.json`、本指南和`releases/1.4.2/`中的wheel。解压后进入顶层目录运行安装。安装需要访问Python包索引以取得锁定依赖。

默认安装路径为`C:\Program Files\ANSYS Inc\v261\Zemax OpticStudio`，工具目录为compact。已有`ZEMAX_INSTALL_DIR`、`ZEMAX_OUTPUT_DIR`、`ZEMAX_STATE_DIR`和`ZEMAX_TOOL_MODE`环境值会被采用，显式`-ToolMode full`可选择直接工具目录。

## 构建

完成各工作分支整合和发布回归后，从项目根目录使用Python 3.14 x64运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\release\build_windows.ps1 -PythonExe python
```

构建脚本在临时目录创建独立环境，按`requirements/build.lock.txt`安装固定版本的构建依赖，将源码复制到临时目录，再调用setuptools构建wheel。项目版本来自`pyproject.toml`。已有同名产物时停止，由发行负责人先移走旧产物后再构建。

固定源码、Python 3.14补丁版本、构建依赖及`SOURCE_DATE_EPOCH`可复现构建。默认时间戳为2026-11-16 00:00:00 UTC；可通过`SOURCE_DATE_EPOCH`指定其他发行时间。ZIP条目按名称排序，时间戳和文件属性固定，使用stored方式写入。

`scripts/release/export_contracts.py`显式导出full和compact两份目录；`scripts/development/export_tool_schemas.py`显式导出full目录。`scripts/release/installed_schema_smoke.py`默认检查compact的11入口，显式full时检查107入口。最终构建后在独立安装目录执行已安装包检查。

## English

After integration and release regression testing, run the PowerShell command above with Python 3.14 x64. The script builds in a temporary environment using pinned build dependencies and places the wheel and Windows ZIP under `releases/1.4.2/`. Existing artifacts are preserved and cause the build to stop.

For reproducible output, keep the source, Python patch version, build dependencies, and `SOURCE_DATE_EPOCH` fixed. The default timestamp is November 16, 2026, 00:00 UTC. ZIP entries use stable ordering, timestamps, attributes, and stored compression.

Extract the ZIP, enter its top-level directory, and run `install.ps1 -PythonExe python`. The bundle includes the installer, both launchers, pinned runtime requirements, sample client configuration, bilingual README, license, this guide, and the wheel at the path expected by the installer. Installation downloads locked dependencies from the package index. The defaults are OpticStudio 2026 R1 and compact mode. Existing directory and mode environment values take precedence; an explicit `-ToolMode full` takes precedence over the mode environment value.
