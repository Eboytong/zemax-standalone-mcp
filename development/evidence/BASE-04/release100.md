# 1.0.0 本地正式发行记录

日期：2026-11-09。运行基线：Windows x64、Python 3.14.6、OpticStudio 2024 R2 Premium（24.2.0 build 240529）。项目停止新增功能开发并进入维护阶段。

发行接口包含 101 个 MCP 工具、132 种 run_analysis 请求类型。历史原生计划 96 组中，7 组有完整验收记录，89 组保持未完成并冻结；发行说明不将这 89 组列为完成能力。

## 验证

- 全量普通测试：3496 passed, 854 skipped, 0 failed，48.38 秒。命令：.venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider --basetemp .local/tmp/pytest-1.0.0。跳过项按各自测试条件记录；其中包括需要本机原生条件的测试。
- wheel：releases/1.0.0/zemax_standalone_mcp-1.0.0-py3-none-any.whl，492,949 字节。构建命令：C:/Users/tonge/anaconda3/python.exe -B -m pip wheel . --no-deps --no-build-isolation --wheel-dir releases/1.0.0。该解释器为 Python 3.14.6，使用 setuptools 83.0.0。
- 独立安装：安装到 .local/builds/1.0.0/venv，核心依赖采用 requirements/core.lock.txt，reports extra 采用 requirements/all.lock.txt。installed_schema_smoke.py 从隔离环境安装位置启动服务，检查到 101 个工具、132 种请求，并确认 stdio 正常关闭。结果见 .local/evidence/development/BASE-04/installed100-isolated-r2/summary.json。
- 原生 wheel 冒烟：通过隔离环境已安装的 wheel 和真实 MCP stdio 打开 Cooke 40 degree field 样例副本，执行 relative_illumination。请求设置回读成功，任务状态 succeeded；分页读取、PNG 导出、任务关闭和应用 application_close 均通过，断开后 connected=false 且无运行任务。结果见 .local/evidence/development/BASE-04/native-stdio-wheel-1.0.0-r2/result.json。

## 发行使用

仓库根目录运行 install.ps1，建议带 -WithReports -WithGeometry 安装对应可选依赖。完整命令见本目录 README.md。schema 清单已更新为 service_version=1.0.0，工具数与安装包冒烟结果一致。

## 已知状态

原生连接阶段输出 FRU__delta_init(): Attempt to start when running! 警告；本次发行 wheel 的分析任务、原生分析关闭及 stdio 断开均正常完成。其余历史未完成条目、各专题输入限制及原生接口缺口保留在 development/ledgers/、development/remaining-ranked.md 和专题文档中。当前不安排新增功能工作。
