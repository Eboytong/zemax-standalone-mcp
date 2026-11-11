# 1.4.0 发行检查

2026-11-11。Windows x64、Python3.14、OpticStudio2024R2 Premium。D023—D027的工作范围为精确能力契约、稳定compact模式、材料贡献解耦、模式对照和统一发行。full提供107工具和146分析；compact注册11入口，共享同一套原生操作。

功能与对照证据：[D023](D023/README.md)、[D024](D024/README.md)、[D025](D025/README.md)、[D026](D026/README.md)、[D027](D027/README.md)。条件宿主实验按实际可观测状态登记；默认full，compact可选。

## 已完成检查

- 普通全量：3775通过，70.37秒，release140-ordinary.xml。
- 最终注册/派发和玻璃合同：47通过，23.39秒，D025-final-targeted.xml。
- D026有限共轭非球面材料试验与独立原生组合：1通过，37.57秒，D026-native-final.xml。
- full/compact串行场景：各12/12；数值对照12/12，D027/summary.json。
- compact受影响原生回归：4通过，274.07秒，release140-native.xml。覆盖原贡献材料试验、联合优化取消、候选分支/恢复/失败/报告和逐面损耗取消。实际目录glass_trials_native_dc2f7e111a、d019_joint_glass_cancel_fc96903a85、d018_candidates_f482652d52、d022_energy_cancel_f869283684。
- 独立安装包原生：3通过，62.03秒，release140-installed-native.xml。full和compact各执行MTF/图像、真实光线分页和波前网格；单独执行有限共轭非球面材料试验。原始目录d025_disclosure_full_bca95789dc、d025_disclosure_compact_3ce2a5a444、d026_optional_contribution_f12fb12903；均以成功disconnect结束。
- 最终状态及合同检查：35通过，15.01秒，release140-tail.xml。
- busy/timeout原始响应及请求收据定向检查：10通过，22.01秒，release140-receipts.xml。
- 文档入口检查：123份文档、249个本地链接，失效链接0；覆盖README、用户指南与示例、本期开发入口和D023—D027证据。

## 构建与独立安装

构建命令：`.venv/Scripts/python.exe -B -m pip wheel . --no-deps --wheel-dir .local/builds/release140-candidate`。产物zemax_standalone_mcp-1.4.0-py3-none-any.whl，605030字节；通过pip --no-deps --target独立安装至.local/builds/release140-installed。

安装包schema命令：`scripts/release/installed_schema_smoke.py <target> <output> 1.4.0 <tool_count> 146 <mode>`。full=107工具、compact=11工具，两种模式均取得146分析合同、离线搜索和正常stdio关闭。摘要保存在.local/evidence/release140-schema-full与release140-schema-compact。原生测试设置ZEMAX_TEST_WHEEL_DIR并使用隔离boot断言从安装目录导入。

用户文档的full/compact schema由真实stdio目录导出；安装启动支持ToolMode及环境配置。光学解算沿用OpticStudio2024R2，公开原生参数、结果、任务和恢复语义保持。

## GitHub发行

发行检查已完成，下一动作是提交并推送源码及v1.4.0，创建正式Release并上传wheel。发布收据在完成后补入本节。
