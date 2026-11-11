# 候选模型与同条件比较

`manage_candidates`保存独立模型及索引。每次检查点生成新的候选编号，原基线和旧候选继续保留。文件位于`ZEMAX_OUTPUT_DIR/_designs/<design_id>/`；项目资源目录随模型保存。

创建基线时冻结评价条件：

```json
{"request":{"action":"create","label":"baseline","evaluation":{"spot":{"reference":"Centroid","ray_density":6}}}}
```

返回`design_id`及`candidate.candidate_id`。分支并选择后，用现有建模或优化工具修改模型：

```json
{"request":{"action":"branch","design_id":"设计编号","parent_candidate_id":"基线编号","label":"A"}}
```

```json
{"request":{"action":"select","design_id":"设计编号","candidate_id":"分支编号"}}
```

```json
{"changes":[{"surface":1,"radius":45}]}
```

将修改存为新候选：

```json
{"request":{"action":"checkpoint","design_id":"设计编号","candidate_id":"分支编号","label":"A radius45","modification_summary":"曲面1半径45mm","external_metrics":[{"key":"quote","value":180,"unit":"CNY","source":"供应商报价"}]}}
```

`run_candidate_evaluation`独立重载每个候选，按基线的分析、视场、波长、单位和采样评价，完成后恢复调用前模型。它返回任务编号；结果中的`rows`可通过`get_task_result`分页。开启`evaluation.merit`时，操作数定义也纳入冻结合同。

```json
{"request":{"design_id":"设计编号","candidate_ids":["基线编号","检查点编号"]}}
```

两候选成功评价后，使用`manage_candidates`的`compare`动作，填写`left_candidate_id`与`right_candidate_id`。结果包含指标差值、曲面/材料/结构差异及带来源的外部指标。旧工具`compare_results`继续采用其原有系统条件比较规则。

`restore`与`select`均加载已保存候选；切换前保存当前检查点。`list`可在服务重启后读取设计索引，连接后可直接选择候选。已有优化工具的算法、预算和取消参数继续使用；在选中候选上发起的任务会在context记录候选及父候选编号。把优化结果存为具名检查点后，再按冻结合同重载评价。
