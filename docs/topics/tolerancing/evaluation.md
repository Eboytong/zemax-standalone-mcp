# 顺序设计评估

本机 OpticStudio 2024 R2。`run_*` 返回任务编号，使用 `get_task_status` 等待终止状态，再用 `get_task_result` 读取结果。SDK 的工具参数 `request` 包含下列请求对象。

## 批量追迹

```json
{"request":{"rays":[{"hx":0,"hy":0.5,"px":0,"py":0.4,"wavelength":1}],"ray_type":"Real","opd":true}}
```

调用 `run_batch_ray_trace`。最多 10000 条光线，每块最多 1024 条。`target_surface` 省略时使用像面，曲面编号从 0 开始；波长编号从 1 开始。坐标为归一化 Hx/Hy/Px/Py，不自动从物理视场换算。支持 Real、Paraxial，使用 NormUnpol 接口。

返回逐光线输入、序号、错误码、渐晕码、目标面局部交点、方向余弦、法线、OPD 和强度。错误光线的几何数据为 null；未返回光线标记 missing。渐晕与追迹错误分别保留，summary 给出数量。未处理光线不计为成功。

OPD 默认关闭，仅真实光线终止于像面时可开启，采用 CurrentAndChief，单位为该波长的 waves。非偏振接口忽略体吸收、镀膜损耗和 Fresnel 反射，其强度不代表完整系统透过率。

## 单参数扫描

```json
{"request":{"surface":6,"cell":"thickness","values":[40.0,40.1,40.2],"evaluation":{"spot":{"reference":"Centroid"},"mtf":{"sampling":"S_64x64","maximum_frequency":50},"frequencies":[10,25],"merit":true}}}
```

调用 `run_parameter_scan`。surface 须按当前模型选择；示例数值不能直接视为设计建议。支持 radius、thickness、semi_diameter、conic、parameter_1..20，最多 200 个显式数值。数值使用当前镜头单位，系数按面型定义；半口径非负。原 solve/pickup 受保护，替换需要 `replace_solve=true`。

每点从基线镜头重新加载，默认保持像面。需要逐点对焦时显式增加 `evaluation.focus`，例如 `{"criterion":"SpotSizeRadial","use_centroid":true}`。对焦可能改变扫描的像面前厚度，结果须按该补偿策略解释。

`evaluation` 至少选择 spot、mtf、merit 或 analyses 中一项；spot 和 mtf 的参数与独立分析相同。analyses 复用 run_analysis 的类型化请求，analysis_metrics 按分析编号选择曲线插值或网格统计，并明确单位。指定频率使用范围内线性插值，超出实际频率范围将该点标记失败。只运行 MTF 而未指定 frequencies 时，曲线保存在子分析任务中。

## 多文件评估

`run_batch_evaluation` 接收 `{"request":{"paths":["绝对路径.zos"],"evaluation":{...}}}`。最多 100 个 .zos/.zmx，按列表顺序执行同一评估。输入源文件保持只读。

普通点/文件失败会记录错误后继续。工具关闭或基线恢复未确认时停止，要求重连。主任务 succeeded 表示流程结束，仍需检查 summary.failed 和各行 state。取消结果为不完整评估，保留已完成行。

扫描及批量评估在开始前保存基线，完成、失败或取消后恢复原设计、工作路径和来源；修订号递增。restoration.restored 明确表示恢复结果。运行期间禁止冲突操作；原生步骤不能即时取消时等待安全边界。

## 分页、比较与报告

`get_task_result(task_id,start=0,count=200)` 对逐光线/扫描点/文件行分页，count 最大 1000；返回 total、next_start。完整 JSON 位于 artifacts。原有 MTF/光斑任务保留原有返回行为。

`compare_results(left_task_id,right_task_id)` 比较评估结果，对应行按输入顺序配对；两边必须全部成功且行数、实际系统条件、分析采样、波长、配置、参考点、焦位策略及指标集合兼容。返回 compatible、differences 和数值差。不同条件不给出改善判断。评价函数的比较核对操作数编号、类型、目标、权重和参数；计算值与贡献率保存在各行的 `merit_operands` 中。评价函数出现非有限值时，该评估点失败并返回 `INVALID_METRIC_VALUE`。比较读取到非数值或非有限指标时，同样返回该错误及任务编号、行号和指标名。

`export_evaluation_report(task_ids,title)` 从已取得的数据生成 Markdown、JSON、CSV。报告保留基线、实际配置、软件版本、失败项、恢复状态和子分析任务引用，不重跑 Zemax。任务编号仅在当前服务进程中有效，文件会持续保留。

非序列累计功率表保存 trace_conditions 中各历史任务的状态、错误和追迹选项。导出时自动收集相关已结束任务，包含失败和取消项；关联任务不存在或尚未结束时，以 unavailable_trace_tasks 标明缺口并保留表内快照。model_matches_history 只核对模型，mixed_conditions 和 complete 还考虑追迹选项及历史状态，解释见[非序列数值条件](../nonsequential/nonsequential-validation.md)。

报告会读取关联的分析结果，支持 include_charts=true、formats=["markdown","pdf"]，建议同时 background=true。网格区域、扩展追迹、多结构、优化与专项分析的请求和约定见 [专项工具](../propagation/extended-tools.md)。

## 运行示例和验证

```powershell
& '.\.venv\Scripts\python.exe' -B examples/workflows/evaluate_design.py
& '.\.venv\Scripts\python.exe' -B -m pytest tests/unit/test_evaluation.py -q -p no:cacheprovider
```

普通测试覆盖参数、插值、分页、扫描失败继续、取消和恢复失败。真实stdio、Cooke扫描、追迹分块及REAX/REAY数值依据见验收索引（历史参考）。示例会修改工作设计并生成输出，运行前确认输入；GUI对照范围以对应验收记录为准。
