# 加工成本与公差预算

`run_analysis`的`tolerance_budget`将用户提供的有限公差分配交给原生Tolerancing评价，按成本和目标良率选择候选。结果通过任务状态及`rows`分页读取。

## 输入

每个`processes`元素对应原模型一个活动的双界限TDE公差行：`operand`、名称、单位、允许半宽范围、参考半宽、固定成本、变动成本及指数。`allocations`每行按工艺顺序指定对称公差半宽，最多50个候选、8种工艺。成本定义为各项`fixed_cost + variable_cost × (reference_half_width / half_width)^exponent`之和；`currency`和`costing_unit`记录货币及计价基准。

`criterion`、`compensation`、`sampling`、`cycles`及`distribution`沿用原生公差工具。`criterion_unit`记录原生准则的单位，`threshold`和`pass_when`确定样本合格标准。原模型的其他公差和补偿行保留，活动STAT行须先整理为统一分布。每次运行插入正式SEED操作数；比较阶段共用`seed`，最终复验使用不同的`validation_seed`。

## 结果解释

先在工艺最小半宽上执行原生灵敏度分析，再对全部候选执行Monte Carlo。`interval`为指定置信水平的双侧Wilson区间，区间下限达到`target_yield`的候选通过筛选。最低成本候选追加独立样本，独立区间下限达标后生成推荐模型。所有候选的成本构成、原生参数身份、统计和子任务编号均保留；不可追迹样本计入失败，缺失或非有限准则返回错误。

`selected_index`记录筛选阶段最低成本候选，`recommended_index`记录通过独立复验的候选。有限候选集合中没有通过项时，这两个字段按实际结果返回空值。推荐ZOS保留最终公差和独立验证种子；`save_validation_samples`可保存最多100个验证模型。

所有执行路径恢复源模型、TDE和评价函数。`budget_seconds`约束搜索和原生子任务，失败结果保留已处理候选。

示例见[请求文件](../../../examples/requests/tolerance-budget.json)。示例成本是受控数学输入；实际加工预算使用供应商报价拟合出的参数与工艺边界。
