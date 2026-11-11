# 多目标候选搜索

`run_multistart_optimization` 的 `pareto` 设置把多起点与权重网格组合，调用原生局部优化并保存每个候选。每个目标对应一行现有 MFE 操作数，目标方向统一为最小化 `abs(value-target)/scale`。请求显式给出目标值、尺度及可接受误差。

```json
{
  "request": {
    "starts": [[{"surface": 1, "parameters": {"1": 50}}]],
    "optimization": {"cycles": "Fixed_10_Cycles", "number_of_cores": 1},
    "evaluation": {"merit": true},
    "pareto": {
      "objectives": [
        {"operand": 1, "target": 40, "scale": 20, "name": "40mm target", "maximum_error": 12},
        {"operand": 2, "target": 60, "scale": 20, "name": "60mm target"}
      ],
      "weight_grid": [[9, 1], [1, 1], [1, 9]],
      "budget_seconds": 120
    }
  }
}
```

本例先建立焦距50mm的原生Paraxial面，将参数1设为变量，在MFE中建立两行EFFL（波长1）。两个目标分别为40/60mm，三个权重的解析折中为42/50/58mm。第一项目标的最大绝对误差12mm使58mm候选被列为不可行。

目标数量为2–8；每行权重数等于目标数，权重须为有限正数。原生行权重采用 `weight/scale²`。其他已有MFE行继续参与标量优化。起点×权重组合最多200个，权重网格最多50组。搜索按固定顺序枚举，参数与起点决定重复运行条件。

`maximum_error` 使用操作数原始单位，是候选可行性条件。返回各目标的原值、绝对误差、归一化误差和超限量。可行候选之间按各维误差计算支配关系；重复目标向量均保留。`summary.pareto_indices` 对应已评估可行候选中的非支配集合，`dominated_by` 列出支配它的候选编号。

`budget_seconds` 控制搜索预算，并传入当前原生优化任务的停止期限；原生工具确认停止后回收资源。预算失败和取消保留已完成行及其排名。所有候选通过 `path` 指向原生ZOS模型，`rows` 支持分页，`series` 可导出图像。结束时恢复起始模型、solve、配置及MFE。
