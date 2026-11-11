# D017 能力索引与中文检索

2026-11-11，源码基于a099540加本轮未提交改动，Python3.14。本次从主仓src导入，产品发行基线1.1.0。

完成103个工具、144种分析类型的离线索引，24项带具体工程元数据。请求schema由现有模型生成；列表、详情、依赖条件及中文检索公开可调用。检索结果记录在[retrieval.json](retrieval.json)，固定30条中文查询Top-5命中30/30，预定门槛27/30。

命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_capability_index.py tests/unit/test_model_adaptation.py tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d017-final2 --junitxml=development/evidence/D017/ordinary.xml`。结果26通过，含真实stdio工具发现、搜索、schema详情和关闭。普通测试覆盖全入口、元数据、分页、错误编号、参数边界和无结果；原生连接次数0。

资源生命周期：stdio客户端退出后服务及工作进程正常关闭；状态保持未连接，未创建光学实例、未修改模型。使用指南见docs/guides/capability-search.md。新能力随请求注册表进入索引；候选能力的专门说明随D018接入。

结论：D017完成。随D018—D022注册新增入口，当前索引覆盖107个工具和146种分析；统一1.3.0安装包检查已通过，见发行记录。103/144为本项初验时的能力数量。
