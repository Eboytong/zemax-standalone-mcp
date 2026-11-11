# 1.1.0 本地发行记录

2026-11-11，Windows x64、Python3.14、OpticStudio2024R2/API24.2.0/build240529 Premium。102工具、144种run_analysis请求，wheel为`releases/1.1.0/zemax_standalone_mcp-1.1.0-py3-none-any.whl`，574042字节。

交付Gradient2/3专项、指定面双向镀膜RTA、原生Detector Viewer、制造几何、光纤对准、固定膜系优化、NSC效率、材料替换、扫描瞳共轭、鬼像、双路径共焦、均温热补偿、多目标候选、公差成本预算及双FSM离线控制。具体设置、数值参考、输入条件及结果见D001—D012、D014—D016证据。

3714普通及4串行原生回归通过；独立安装真实stdio读取102/144，安装包2原生用例通过。命令和结果见[尾批检查](tail-checks.md)，前十专题集中证据见[D010](D010/concentrated-checks.md)。安装脚本默认指向1.1.0。

现行开发范围15/15项已完成。D013按用户要求移出计划，探查原文作为历史技术资料保留。原1.0.0发行产物继续保留。代码、文档和1.1.0 wheel已发布到GitHub。

## GitHub发布

- 仓库：Eboytong/zemax-standalone-mcp，沿用当前公开可见性。
- 正式Release：[v1.1.0](https://github.com/Eboytong/zemax-standalone-mcp/releases/tag/v1.1.0)，draft=false、prerelease=false。
- 源码提交：`a2a435c13b2216bcf846b13704fc01c1e764adf1`。
- 附件：`zemax_standalone_mcp-1.1.0-py3-none-any.whl`，574042字节，GitHub状态uploaded。
- 发布时间：2026-11-11T01:22:55Z。
- 本次D013移出当前计划，15/15项完成；开发状态汇总定向测试4项通过。数值实现和wheel沿用上列原生及安装包检查。
