# D011—D016 尾批与1.1.0安装包检查

2026-11-11，主仓Windows x64/Python3.14，OpticStudio24.2.0 build240529 Premium。D001—D012及D014—D016共15项完成。2026-11-11范围整理后D013已移出计划，现行统计为15/15。前十项集中检查见D010记录，本次覆盖最后五个完成项。

| 检查 | 实际结果 |
| --- | --- |
| 全量普通测试 | 3714 passed，26.22s |
| 受影响公差/热补偿/Pareto/FSM原生回归 | 4 passed，72.31s，串行 |
| D015原生专项 | 1 passed，18.19s，含独立样本、补偿及恢复 |
| 1.1.0版本与请求定向检查 | 42 passed，3.84s |
| 隔离构建与独立目录安装 | 成功；releases/1.1.0，574042字节 |
| 安装包真实stdio schema | 102工具/144分析请求，正常关闭 |
| 安装包真实stdio原生 | 公差成本预算及双FSM，2 passed，45.46s，串行；分页、图像、恢复及断开通过 |

D011双路径共焦1原生/383.11s、D012底层5原生及工作流/热光2原生、D014及D016各1原生沿用各自最后通过证据。尾批未改变这些算法；热补偿、Pareto和FSM另在本次回归复测。原始证据按各专题README关联。

## 命令与原始记录

- 全量：`.venv/Scripts/python.exe -B -X utf8 -m pytest tests/unit -q -p no:cacheprovider --basetemp .local/tmp/pytest-tail-unit --junitxml=.local/evidence/development/tail-unit.xml`
- 原生：同上改为`tests/native/test_tolerancing_live.py tests/native/test_thermal_compensation_live.py tests/native/test_pareto_live.py tests/native/test_fsm_control_live.py --run-zemax`；输出tail-native.xml/txt。
- 构建：`.venv/Scripts/python.exe -B -X utf8 -m pip wheel . --no-deps --wheel-dir releases/1.1.0`，使用pyproject隔离构建。
- 安装：`pip install --no-deps --target .local/builds/1.1.0/installed releases/1.1.0/zemax_standalone_mcp-1.1.0-py3-none-any.whl`；测试依赖来自当前环境，stdio通过`-I`显式从独立安装目录导入。
- schema：`scripts/release/installed_schema_smoke.py .local/builds/1.1.0/installed .local/evidence/development/installed110-schema 1.1.0 102 144`。
- 安装包原生：设置`ZEMAX_TEST_WHEEL_DIR`后运行`test_tolerance_budget_live.py test_fsm_control_live.py --run-zemax`；installed110-native.xml/txt。

所有日志位于`.local/evidence/development/`；构建/安装日志tail-build.txt及tail-install.txt，schema实际结果位于installed110-schema/summary.json。源码和文档的统一GitHub发布信息见release110.md。原生执行完成后均disconnect。
