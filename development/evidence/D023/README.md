# D023：宿主与上下文基线

2026-11-11。固定源码83b5ea7（1.3.0），Windows x64、Python3.14、MCP SDK2.3.0；Codex CLI0.166.0，桌面App26.1103.7773.0。60条任务见[tasks.json](tasks.json)，12条端到端子集见[end_to_end.json](end_to_end.json)。用例、目标能力和副作用已在模式对照前固定。

执行：`.venv/Scripts/python.exe -B -X utf8 development/evidence/D023/observe.py`。程序从固定提交提取源码到本机构建目录，六个独立stdio进程各执行tools/list、搜索和状态读取，退出时关闭MCP及后台进程。原始结果：`.local/evidence/development/D023/observations.json`。六次均正常关闭，状态connected=false。

本会话宿主将zemax作为延迟工具命名空间提供，支持按名称/描述发现工具。MCP侧能够观测tools/list、工具请求、结果、传输字节和时间；宿主内部实际注入、缓存命中和模型usage没有MCP可读字段，按null记录。Responses独立API实验条件为未配置推理会话；其tool_search配置不套用为Codex服务器配置。

1.3.0完整107工具为1,431,740字节；输入schema映射1,340,906字节；146种分析。数据来自真实stdio紧凑UTF-8 JSON，保留在[原始测量](../PLAN-20261111-DISCLOSURE/README.md)。六条小试固定同样查询和本机Python，每次冷启动，观测延迟独立于光学计算。

正式资料：OpenAI工具搜索`https://developers.openai.com/api/docs/guides/tools-tool-search`、Codex MCP`https://learn.chatgpt.com/docs/extend/mcp?surface=cli`。本机未取得独立模型总token，D027以可观测的目录、精确详情、完成输出和时间选型；token门槛在取得usage时评估。

完成：任务集、端到端子集、六次小试、固定基线、宿主事实及观测来源齐全。下一项D024。
