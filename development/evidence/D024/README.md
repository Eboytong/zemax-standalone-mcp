# D024：精确契约与轻量目录

2026-11-11，源码基线1.3.0加本轮工作区修改，Python3.14/MCP2.3.0。调用契约来自MCP处理函数元数据，覆盖107工具、146分析kind和7个候选action；使用MCP外层参数形状。

单kind/action以原schema分支为来源，保留可达$defs、discriminator映射、数组/组合及递归引用。`analysis_kinds`可选择复合评价中的分析联合；完整tool契约通过detail显式读取。默认短目录提供ID、用途、影响、读写分类和详情入口；include_metadata=true提供完整资料。

wavefront默认详情为1,145字节，保留其全部字段、默认值、枚举和边界。原始完整详情151,046字节。107/146均可定位，候选list详情不包含create分支；嵌套wavefront评价不包含GlassTrials定义。

定向普通检查见[XML](../D024-26-targeted.xml)：43通过，包括schema递归闭包、全目录、60题检索、实际stdio搜索与失败后复用、包装/默认值/省略字段、原有玻璃合同。冻结60题59通过，超过57门槛；Q43为跨域“读取波前再保存候选设计”，Top5返回候选/保存能力，波前分支排位在其后，原始结果保留。

命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_disclosure.py tests/unit/test_capability_index.py tests/unit/test_glass_trials.py tests/unit/test_joint_glass.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d024-26 --junitxml=development/evidence/D024-26-targeted.xml`。stdio正常关闭，本阶段目录检查未创建OpticStudio。
