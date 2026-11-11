# Agent自主调用、工程工具与渐进式披露调研

日期：2026-11-11。代码基线：1.3.0，源码提交`83b5ea7`，107个工具、146种分析请求。调研与执行计划分开维护；本文件记录判断依据，[plan.md](plan.md)登记后续任务。

## 1. 结论与取舍

建议保留原生能力和已验证的确定性计算，让Agent自主选择目标、方法与执行顺序。候选管理、数值聚合、任务控制和恢复继续作为服务；联合搜索和去敏感化作为可选工程流程。优先解除与当前任务无关的前置条件，减少首次披露和重复schema。

本轮采用五个工作包D023—D027：客户端实测、精确schema、渐进式执行入口、工程流程解耦、对照验收与统一发行。子Agent工具路由进入条件实验，是否采用由相同任务集的完成率、总token与延迟决定。

## 2. 工程工具如何影响自主性

模型需要目标、可选动作和准确反馈。固定流程适合重复且定义明确的任务；开放的设计问题需要模型能够更换目标、采样、变量、优化器和停止策略。当前底层建模、MFE、公差、光线及优化入口仍然存在，六项工程功能属于附加入口。

| 当前能力 | 已实现的价值 | 对模型决策的实际影响 | 建议 |
| --- | --- | --- | --- |
| 能力检索 | 离线找到工具、分析kind及详情 | 提供候选；调用顺序由Agent选择 | 保留；缩小详情，只返回选中类型的依赖 |
| 候选管理与评价 | 保存/切换/恢复、父子归属、冻结条件比较 | 评价规格在创建候选时确定 | 保留；由Agent显式选择规格和比较对象 |
| 联合玻璃搜索 | 同基线候选、cartesian/one_at_time/beam、预算及最佳模型 | 固定候选策略；当前强制先做近轴贡献分析 | 将贡献分析改为独立可选项；保留显式材料组合和逐项原生评价 |
| 评价函数构建 | 原生向导、OPDC/OPDM/OPDX、尺度、权重、约束、预览 | 高层目标模板有范围；已有底层MFE编辑可组合 | 保留模板，继续提供直接MFE编辑和原生优化 |
| 设计去敏感化 | 原生制造良率向导、固定公差、灵敏度和独立MC对照 | 固定DLS路线、半径/厚度变量、统一分布及样本流程 | 明确为该路线的可选流程；自主方案使用既有MFE/优化/公差入口 |
| 顺序逐面损耗 | 原生带权偏振追迹、几何渐晕配对、逐面聚合 | 执行请求指定光线和范围，决策很少 | 保留；返回计算定义和逐项来源 |

代码依据：`src/zemax_mcp/desensitization.py:DesignDesensitize.fixed_contract`要求制造良率向导、拒绝额外波前targets，执行中采用DLS；`glass_trials.py:contributions`要求无穷远物方、角度视场、三波长、同轴Standard面和完整玻璃段；`run_glass_trials`在材料试验前无条件调用贡献分析。`joint_glass.py:available_slots`也把Standard条件用于槽位筛选。

这些限制中，材料目录身份、solve保护、实际回读和原生有效性条件应保留。Standard、三波长、Y场等贡献模型条件应只约束贡献结果；材料赋值与原生评价分别按自身条件运行。去敏感化已有一条原生验收路线，其他策略由底层工具组合，并按具体需要补缺失动作。

近期的减法落实在三处：默认检索优先展示可组合原生动作；工程流程按需展示；减少不属于本次计算的强制前置步骤。现有工具保留兼容调用，删除入口以实际重复维护成本与使用数据为依据。

## 3. 当前工具描述的实际大小

使用主仓源码、项目Python和真实stdio读取`tools/list`，服务正常关闭。没有创建OpticStudio应用。序列化方式为UTF-8、`ensure_ascii=False`、紧凑JSON。原始JSON、测量程序和命令见[测量证据](evidence/PLAN-20261111-DISCLOSURE/README.md)。

| 测量项 | UTF-8字节 |
| --- | ---: |
| 107个完整工具描述，含inputSchema/outputSchema/说明/annotations | 1,431,740 |
| 全部输入schema，以工具名为键 | 1,340,906 |
| 最大7项输入schema合计 | 1,185,606 |
| 上述7项占全部输入schema | 88.4183% |
| run_analysis输入schema | 160,957 |
| 单独wavefront请求及必要定义 | 830 |
| 当前wavefront能力详情，含元数据 | 151,046 |
| 同一详情裁剪为可达定义后 | 1,247 |
| 搜索“计算波前和泽尼克像差”的Top-5结果 | 3,744 |
| 现有9个引导/控制工具描述合计 | 10,275 |

最大7项为`run_multistart_optimization`、`run_catalog_evaluation`、`manage_candidates`、`run_parameter_scan`、`run_configuration_evaluation`、`run_batch_evaluation`和`run_analysis`。共用`Evaluation.analyses: list[AnalysisRequest]`使整套分析联合在多个入口中重复出现。减少工具个数时应同时测量每个schema，否则可能将多个小工具合并成更大的联合。

`capability_index.build_index`为每个分析详情附加全部分析`$defs`，所以查询单一波前仍会带入其他分析定义。本次仅在测量副本中递归保留`$ref`可达定义，得到上述1,247字节。正式实现还应遍历discriminator映射等schema引用，并保持默认值、互斥条件、枚举和数值范围。

这些数字描述MCP传输内容。模型实际上下文由宿主决定：宿主可缓存目录、选择工具、延迟加载或转换schema。本次没有取得目标模型的tokenizer或客户端逐请求usage，实际token在D023测量，UTF-8字节保持为共同可复现指标。文档引用文件本身的缩进与磁盘大小也单独于模型输入统计。

## 4. 渐进式披露的层次

建议按三层提供资料：L0为领域和短说明；L1为选中功能的准确参数、单位、默认值、调用例子和条件；L2为按请求分页的结果、文件和详细诊断。Agent可直接使用已知能力ID，也可检索后读取详情。

### 4.1 宿主原生工具搜索

OpenAI Responses API提供`tool_search`与`defer_loading`；搜索后将所需工具定义加入模型上下文。MCP服务器标签和简介可用于选择整个服务。它属于API/宿主的模型工具加载机制。[S1]

Codex官方配置文档提供`enabled_tools`/`disabled_tools`，可用于固定任务的工具范围。[S2] 本机Zemax配置当前启用了整个服务，未配置这两项。官方Codex页面未提供可直接套用的服务器级`defer_loading`配置；Responses API示例应在其对应客户端使用。本机Codex的目录缓存、按需加载粒度及usage需实际记录。

优先复用当前宿主的原生发现。一个问题是加载`run_analysis`会连带146种请求；因此宿主已具备工具搜索时，分析级精确schema仍有价值。可选的精简执行入口能让Agent单独取得一个kind的契约。

### 4.2 稳定精简入口

候选结构为9个现有引导/控制工具，加`query_capability`和`execute_capability`两个小入口，共11个。两入口按调用对模型状态的实际影响划分。保留`get_request_status`，使请求超时后能继续查询实际执行状态。

```text
Agent自主计划
  → search_capabilities：短候选列表
  → get_capabilities(detail)：一个工具/kind/action的精确契约
  → query_capability / execute_capability：校验后执行
  → get_task_status / get_task_result / cancel_task：沿用现有任务链
```

建议请求包含`capability_id`和JSON对象`arguments`。外层schema保持小型通用结构；实际参数由同一份有类型请求模型校验。执行前复用现有MCP处理函数到Backend的映射，保留`exclude_unset`和包装层，避免将工具的MCP参数与COMMAND_MODELS内部参数混用。结果、错误、修订、任务归属和关闭机制保持一致。

精简入口的取舍是模型生成参数前需要读一次详情，宿主的通用外层schema无法预先提供全部内层字段约束；服务器负责精确校验，并返回字段路径及修正信息。默认模式通过D027对照结果决定，完整模式持续可选。

### 4.3 固定profile与动态列表

固定profile可限定一次会话的顺序、NSC或POP工具，但跨领域任务仍需额外发现与可调用路径。作为用户自选配置模板即可，先复用Codex白名单能力。

MCP规范提供`tools/list`分页和`listChanged`。分页解决目录传输；模型按需获得schema由宿主决定。2026-07-28规范要求工具列表保持确定性，且不得因连接内其他请求产生连接专属变化。[S3] 因此，本项目采用启动时固定的full/compact注册表；按请求披露能力详情，不用“搜索后向本连接追加工具”作为加载机制。真实软件目录变化再使用列表变更通知。

### 4.4 代码编排与结果披露

有代码执行环境的Agent适合自行写循环、条件、搜索策略和数据聚合，通过MCP调用原生动作。Anthropic给出的官方方案把工具说明放在可读取文件中，并在代码中筛选大结果后返回摘要。[S4] 本项目先提供稳定的结构化发现和调用，复用Agent已有的执行环境；MCP继续负责原生对象、类型、状态和资源。

原始光线、网格和MC样本继续落盘和分页。摘要应包含单位、有效/失败数、关键指标、结果句柄和下一页；数据裁剪要明确总数与返回数。避免为解决schema问题引入另一个通用代码执行服务。

## 5. 子Agent工具选择的比较

子Agent可以读取工具目录与资料，只向主Agent回传候选能力和必要参数；主Agent再读取选中的精确契约并执行。Codex官方说明这种分工能把探索日志和中间输出移出主会话。[S5] Claude Code也支持子Agent独立上下文和专属MCP范围。[S6] 具体配置随宿主而定。

| 方法 | 主Agent上下文 | 额外推理/交接 | 适合任务 | 本项目取舍 |
| --- | --- | --- | --- | --- |
| 本地词法检索+精确详情 | 短候选与被选schema | 通常为检索、详情各一次工具调用 | 名称明确、常见光学任务 | 默认基础 |
| 宿主原生工具搜索 | 由宿主加载匹配工具 | 宿主负责搜索 | 已支持发现机制的客户端 | 优先复用，实测大联合开销 |
| 固定工具白名单 | 仅预选范围 | 启动前配置 | 重复、领域固定任务 | 提供可选模板 |
| 子Agent只选工具 | 返回能力ID/理由/缺失输入 | 子Agent推理、请求摘要及交接 | 模糊跨领域问题、需查大量资料 | 条件实验 |
| 子Agent完成整段研究或诊断 | 主Agent接收结构化结论 | 执行成本随子任务变化 | 大量模型/结果阅读、方法比较 | 比只选工具更有独立价值 |

子Agent和主Agent若各自加载全目录，总token可能增加。目录仅放子Agent侧可降低主会话占用；主Agent继续需要执行所选工具时，仍需准确契约或可信调用包装。评估同时统计父子Agent的总token、完成率、端到端延迟和重试。

本项目建议宿主提供可选领域顾问，返回`capability_ids`、缺失输入、依据与建议步骤。MCP服务器保持确定性，不增加模型密钥、内部嵌套推理或Agent生命周期。光学原生执行继续由一个所有者串行调度。

## 6. 成本与完成率如何判断

先冻结60条任务：30条已有检索题扩展校核，加30条稀有能力、同义词、跨域多步、参数约束和未知能力。标注可接受工具集合、成功输出、模型允许的决策空间及调用副作用。挑选12条作为端到端子集，至少覆盖顺序、NSC、POP、优化、公差和逐面损耗。

比较A：当前full；B：当前宿主原生发现；C：精简入口；D：条件子Agent路由。宿主不提供的模式记录实际支持状态。冻结模型、任务、输入和工具预算，冷启动与复用分别记录；对照顺序交替，原生模型每次从同一基线开始。

主要指标：最终完成率、工具集合召回、首次选择、参数错误、模型状态/资源终态、初始schema字节、实际注入schema、整段交互schema与结果字节、父子总token（可取得时）、延迟中位数/P95、发现轮次和原生评价次数。

建议预设门槛：固定任务集Top-5召回至少57/60；可自动判定任务完成数至少达到full；compact启动目录不超过20,000字节；单分析详情只含可达定义且146个kind全部可定位；12条端到端结果满足既有数值容差。token可观测时比较中位数减少至少50%，P95延迟增加不超过20%；达不到门槛时保留为可选模式并记录具体任务。子Agent需在模糊任务子集新增至少2条成功，或在成功数相同时使总token中位数减少至少20%，才进入推荐配置。

上述门槛用于这组冻结任务的工程选型。当前实测为工具内容体积与源码审查；模型完成率和token改进在后续任务中取得。

## 7. 一手资料

检索与打开日期均为2026-11-11。

- S1：[OpenAI Tool search](https://developers.openai.com/api/docs/guides/tools-tool-search)，动态模型侧工具加载、namespace及MCP配置；[MCP服务器接入](https://developers.openai.com/api/docs/guides/tools-connectors-mcp)。
- S2：[Codex MCP配置](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)，白名单、黑名单及stdio配置；[配置参考](https://learn.chatgpt.com/docs/config-file/config-reference)。
- S3：[MCP 2026-07-28 Tools规范](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)，工具目录、分页和变更通知。
- S4：[Anthropic Code execution with MCP](https://www.anthropic.com/research/code-execution-with-mcp)，按需读取定义和代码内筛选；[Advanced tool use](https://www.anthropic.com/research/advanced-tool-use)，工具搜索与程序化调用。
- S5：[Codex Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)，上下文隔离与结果汇总。
- S6：[Claude Code Subagents](https://code.claude.com/docs/en/sub-agents)，独立上下文、专属工具和MCP范围。
- S7：[OpenAI Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)，工具定义的缓存与按需加载。缓存命中率与输入上下文分别测量。

外部资料用于机制选型；本机客户端行为、请求语义和光学结果按本项目实际运行记录。
