# 系统检查

调用 `run_analysis`，请求 `{"request":{"kind":"system_check"}}`。本机 SystemCheck 返回 AS_Default 基础设置，没有业务设置参数。任务记录实际基础设置、模型修订、版本和许可。

结果保留原生 UTF-16 文本及逐行 `rows`；行号从1开始。`get_task_result` 的 `start/count` 使用现有零起始分页规则。配置范围、警告及错误均保留原生报告表述。任务成功表示报告生成完成，报告中的诊断内容单独读取。

2026-11-05：空顺序系统及 Cooke 样例的原生文本、零孔径警告、分页、模型设置与曲面保持、关闭及 disconnect 通过。相关普通25项、真实stdio原生1项通过。证据 `verification/development/TO-01/acceptance080.json`。B002累计5/10，本项未执行全量回归或构建wheel。
