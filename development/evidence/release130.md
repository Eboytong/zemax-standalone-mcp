# 1.3.0 发行记录

2026-11-11。Windows x64、Python3.14、OpticStudio2024R2/API24.2.0/build240529 Premium Standalone。107个MCP工具、146种run_analysis请求。D017—D022共6/6功能验收完成。

## 功能证据

[能力索引](D017/README.md)、[候选管理](D018/README.md)、[联合玻璃](D019/README.md)、[评价函数](D020/README.md)、[去敏感化](D021/README.md)、[逐面损耗](D022/README.md)。各记录包含模型、原生设置、数值参考、门槛、误差、恢复及关闭。全部六项完成后统一构建本版。

## 检查

- 全量普通：3765通过，57.79秒；release130-ordinary-final.xml。命令：`.venv/Scripts/python.exe -B -m pytest tests/unit -q -p no:cacheprovider --basetemp .local/tmp/pytest-release130-final --junitxml=development/evidence/release130-ordinary-final.xml`。
- 串行原生首轮：8通过、3项查询超时，511.06秒；release130-native.xml。超时位于目录全扫描和加密OPD单次批量读写，未出现数值超限。
- 修复后串行复测：联合搜索、联合取消、评价函数3通过，601.68秒；release130-native-retry.xml。命令为上述pytest，选tests/native/test_joint_glass_live.py和test_merit_program_live.py，追加--run-zemax。9组合45项独立比较全部通过，实际原始目录d019_joint_glass_c04d641038、d019_joint_glass_cancel_c520a0294e及d020_merit_program_0c3163d5d1。
- 三面截断归属：1通过，20.20秒；D022/native-clipping-provenance.xml。复合任务保留6个已完成子任务，真实截断面去重为[1]。
- 原生首轮其余成功场景：候选d018_candidates_aa2681f983；相位/配置d020_phase_mce_wizard_842d01ac9f；去敏感化d021_desensitization_a051604b1e与d021_failure_budget_cancel_10a9613a7d；损耗d022_target_surface_probe_6c42738418、d022_energy_cancel_c89d9b6734、d022_decentered_multifield_30f35af18d、d022_absorption_film_mirror_50eb9c665d。均位于.local/runs/runs/。

## 构建与安装

`.venv/Scripts/python.exe -B -m pip wheel . --no-deps --wheel-dir releases/1.3.0`成功，wheel为zemax_standalone_mcp-1.3.0-py3-none-any.whl，600229字节。初次使用--no-build-isolation因环境缺少setuptools而失败，采用pyproject声明的隔离构建成功。

通过pip --no-deps --target独立安装至.local/builds/release130-installed。`scripts/release/installed_schema_smoke.py .local/builds/release130-installed .local/evidence/release130-schema 1.3.0 107 146`通过：实际版本1.3.0、107工具、146分析、离线搜索、未创建光学实例及stdio正常关闭。导出的请求schema来自当前MCP服务。

独立安装原生4通过，155.64秒，见release130-installed-native.xml：候选分支/评价/分页/报告/取消/恢复；相位及多配置/向导；固定公差去敏感化与独立Monte Carlo；吸收/薄膜/MIRROR、图像和报告。实际服务boot断言从独立安装目录导入，原生执行串行且正常disconnect。原始目录依次为d018_candidates_5e16cb70aa、d020_phase_mce_wizard_143889affc、d021_desensitization_6af40b599f、d022_absorption_film_mirror_3600367a49。

打包差异审查发现全局版本替换误改cadquery可选依赖号，恢复为锁定的8.0.1.1.0后重新构建、升级独立安装，元数据和stdio schema复验通过，见release130-installed-summary.json。随后以最终wheel另运行三面损耗、双波长、截断定位原生用例：1通过、20.27秒，见release130-installed-final.xml，原始目录d022_target_surface_probe_1d05e643a3。最终产物600229字节，产品Python源码保持本页各原生用例的实现。

版本、逐面损耗和状态工具定向普通28通过，见release130-version.xml。使用指南本地链接与三个新增请求模板检查通过；原始输出路径均位于.local/runs/runs/。本轮原生会话已正常断开。

## GitHub发布

正式Release：[v1.3.0](https://github.com/Eboytong/zemax-standalone-mcp/releases/tag/v1.3.0)。publishedAt=2026-11-11T10:26:48Z（北京时间18:26:48），draft=false、prerelease=false，设为Latest，沿用仓库当前公开可见性。

源码及tag提交：3cb8ae6d50568aec762fa4c0f6cefb45ee308878。附件zemax_standalone_mcp-1.3.0-py3-none-any.whl，600229字节，GitHub状态uploaded。源码main及v1.3.0均已推送。发布后的证据与交接更新另作维护提交，Python代码和wheel沿用此tag。

D017—D022全部完成，6/6，集中尾检及安装包验收完成。本计划状态为完成；后续维护按具体问题执行定向检查。
