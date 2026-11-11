# 鬼像与杂散光路径诊断

`run_analysis` 的 `ghost_diagnostics` 在各自的系统副本中运行偏振分光追迹，读取原生 ZRD 父子段树，按到达指定探测器的功率排序实际路径，并比较材料、镀膜或位置修改的结果。系统采用纯非序列模式、DetectorRectangle、无前缀 Watts。

```json
{
  "request": {
    "kind": "ghost_diagnostics",
    "detector": 3,
    "expected_paths": [[
      {"object": 2, "face": 1},
      {"object": 2, "face": 2},
      {"object": 3}
    ]],
    "rays_per_source": 1000,
    "random_seed": 42,
    "candidates": [{
      "name": "另一材料",
      "changes": [{"object": 2, "material": "N-F2"}]
    }]
  }
}
```

期望路径省略源起点，按顺序列出每次交互的对象和可选面号，以目标探测器结束。省略 `face` 表示接受该对象任意面。结果中的 `sequence` 保留实际面号；面号由当前对象原生定义。`allowed_objects` 可指定额外允许的交互对象。

分类按以下顺序执行：期望路径、含原生散射交互的路径、含反射的鬼像、允许对象路径、其他路径。反射由父段入射方向及子段出射方向分别与表面法线点积的符号变化判定。`reflection_faces` 给出按发生顺序排列的反射面；一次分光交互的原生反射/透射标志可能同时为真，因此方向和法线参与支路判定。散射类表示祖先段经过散射交互，保留原生标志的归属。

每个候选可修改 `material`、`x/y/z`、`tilt_x/tilt_y`，或同时提供 `face/coating`。位置使用镜头单位，倾角使用度。修改前检查 solve，完成全部修改及原生更新后回读最终设置。单个候选失败保留具体错误并继续后续候选；基线失败时整体返回失败。

`power` 分列探测器总功率、读到的到达功率、保留路径、阈值排除、祖先缺失及剩余未分类功率。`unclassified = detector - retained`，包含筛选、读取上限和祖先缺失等贡献。ZRD 强度字段使用原生单精度存储，小量负残差按原值返回。`read_summary` 保存原生筛选及截断信息；`native_trace_limits` 保存系统的最小相对/绝对强度和最大交互/段数。原生在追迹中终止的弱支路按这些条件解释。

| 参数 | 默认值与范围 |
| --- | --- |
| `rays_per_source` | 1000，1—100000；所有光源合计最多1000000条 |
| `scatter_rays` | false |
| `max_segments` | 20000，1—100000；读取段数上限 |
| `max_paths` | 1000，1—10000；保留路径数 |
| `minimum_relative_power` | 0，0—1；路径功率/探测器总功率阈值 |
| `filter` | 空字符串；原生 ZRD 读取筛选，完整追迹总功率保留 |
| `minimum_expected_fraction` | 0.9，0—1；候选期望路径功率相对基线的保留比例 |
| `trace_budget_seconds` | 120，最大3600；每次原生追迹预算 |
| `save_best` | true；在摘要公开推荐模型路径 |

合格候选按鬼像、散射、其他路径和正未分类功率之和从低到高排序，再按期望路径功率从高到低排序。基线参与比较。每个追迹保留独立 ZOS/ZRD 作为可复现输入，`save_best=false` 时省略摘要中的推荐模型路径。

路径明细通过 `get_task_result` 的 `start/count` 分页；功率曲线可用 `export_analysis_image` 导出。源模型、修订号和探测器累积缓冲保持原状态。成功、失败、取消均关闭追迹工具、ZRD 读取器和系统副本。
