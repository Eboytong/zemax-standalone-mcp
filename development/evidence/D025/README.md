# D025：稳定compact模式

2026-11-11，Windows x64、Python3.14、MCP SDK2.3.0。full提供原有107工具，compact提供11入口，进程启动时由ZEMAX_TOOL_MODE选择。安装和启动脚本支持ToolMode，显式启动参数覆盖环境默认。

两种模式复用MCP函数与SDK参数元数据；query/execute沿原函数进入Bridge，未再套一层Backend.dispatch。请求ID、任务ID、模型修订、busy、超时观察、取消和恢复沿用原实现。query采用显式审查的读取清单，分析与模型/文件操作进入execute。所有107工具、146种分析和7个候选action可定位和派发。

真实stdio首测compact目录12,862字节，full目录1,432,668字节。搜索前后tools/list保持相同顺序和集合。未知能力、冲突kind、未知字段、错误参数和query写操作在派发前返回具体错误；失败后状态和搜索可继续使用。

定向检查见[D024–D026 XML](../D024-26-targeted.xml)。原生对照由[compare.py](../D027/compare.py)串行执行，每个场景独立MCP/Standalone会话，记录输入、响应、数值检查、终态与disconnect。后续最终统计见D027记录。

wavefront使用analysis能力ID，工具使用tool能力ID，候选分支使用action能力ID。详情使用原MCP参数包装；调用时保留显式默认与省略字段的差别。输出继续使用现有任务摘要、rows/series/grids分页和文件。
