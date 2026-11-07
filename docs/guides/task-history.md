# 0.1.12 任务追溯与历史结果

更新日期：2026-11-05。BASE-03交付请求回执、历史任务发现、版本化结果及长结果分页。当前90个工具、42种run_analysis请求。全量950项普通检查通过，450项原生未执行；本批新增24项检查，包含真实stdio进程重启流程。

## 工具与编号

| 工具 | 请求 | 返回 |
| --- | --- | --- |
| `list_task_history` | `request.session_id/request_id/kind/state`可选；`start=0,count=50`，每页最多200 | 当前工作进程及已落盘历史任务、来源、执行状态、结果位置和读取错误 |
| `get_historical_result` | 必填`request.session_id/task_id`；行/曲线/网格区域参数 | 指定历史结果的分页内容、版本、历史来源及原始计算上下文 |
| `get_request_status` | 必填`request.request_id` | 请求开始与返回回执、原始参数、错误、会话、修订、任务编号及产物引用 |

会话和任务编号为32位小写十六进制；请求编号接受1–128个字母、数字、下划线或短横线。MCP桥接层生成唯一请求编号，正常响应在`context.request_id`返回，等待超时在`error.details.request_id`返回。

## 请求状态

工作进程在分派前写入`dispatching`回执，命令返回后写入`returned`。returned表示该次命令已经返回；异步任务还需按其task_id检查任务状态。回执保存ok、原始错误、任务编号、模型修订和产物，不复制整个大型分析结果。

当前桥接进程仍在等待的请求可直接从回执查询状态，查询不进入被原生调用占用的工作队列。回执尚未写出时返回`queued_or_dispatching`。其他进程遗留的dispatching记录返回`unknown_after_worker_exit`；已有证据据此保留执行不确定性，后续修改应先核对模型状态。

回执位于配置输出目录的`_requests/<request_id>.json`。回执写入失败加入响应warnings，原始命令结果保持可读。读取请求本身也会有独立请求编号；忙碌期间的直接回执查询返回被查询的原请求编号。

## 结果版本、发现与分页

新结果包含`result_schema_version=1`；没有该字段的既有JSON视为版本0，支持读取。未知结果版本返回具体版本错误。历史记录基于配置的ZEMAX_OUTPUT_DIR，支持该目录下会话子目录中的既有结果；独立安装后要继续读取原目录，可显式设置同一个输出根目录。

每个新任务在启动时写入`_task_index/<task_id>.json`元数据，终态及关闭后更新。索引包含最终任务状态、关闭尝试和cleanup_warnings。失败任务在没有完整结果文件时保存最小结果及原始错误。JSON通过临时文件与原子替换保存；结果目录缺失时仍返回既有保存错误。

发现工具优先使用新索引，既有结果通过旧格式读取。当前工作进程内存中的任务覆盖同身份历史条目。历史非终态任务显示`unknown_after_worker_exit`，结果中的原始状态和计算条件继续保留。读取历史结果会使用最后一次索引元数据补充关闭信息。

- 行结果使用`start/count`，返回`total/next_start`。
- 曲线指定`series`后按点使用`start/count`，返回对应x/y及标签；series是结果中的0基位置。
- 网格使用`grid/x_start/y_start/width/height`，每次最多10000个值，与当前任务共用区域读取逻辑。
- 散点完整坐标及大型曲线默认通过既有产物读取；历史JSON当前读取上限为256MiB，超过时返回明确错误。

历史结果增加history来源及`live_native_state=not_observed`，读取过程不创建原生OpticStudio实例。损坏或不支持的记录在发现结果errors中单独报告。结果和回执仅使用配置输出根目录中的记录。

## 检查与证据

`tests/unit/test_history.py`包含23项普通检查，覆盖请求边界、版本0、重启读取、当前/历史优先级、损坏记录、关闭警告、失败任务、曲线/网格分页、原始请求错误、进程中断未知状态及忙碌请求查询。

`tests/unit/test_history_stdio.py`实际启动并关闭两代stdio工作进程，检查请求回执、历史发现、结果分页、重启读取及未连接状态。数据来自明确的历史夹具，原生光学任务仍沿用各功能包验收记录。

全量结果：`.local/evidence/development/BASE-03/ordinary022-final.xml`，950通过、450原生未执行，18.73秒。首次回归发现目录创建语义变化，现已保持既有错误行为；原始失败保留在ordinary022.xml。安装包stdio检查及汇总见`development/evidence/task-history022-summary.json`。
