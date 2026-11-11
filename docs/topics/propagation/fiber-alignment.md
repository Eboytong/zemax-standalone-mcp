# POP 光纤对准与容差

`run_analysis: fiber_alignment` 使用原生 POP 的复场耦合积分，扫描接收模式的横移、轴向束腰位置和倾角，可进行有界局部寻优，并提取相对最佳效率的 1 dB、3 dB 交点。

## 请求示例

```json
{
  "request": {
    "kind": "fiber_alignment",
    "settings": {
      "beam_parameters": {"0": 0.1, "1": 0.1},
      "fiber_type": "AstigmaticGaussian",
      "fiber_parameters": {"0": 0.1, "1": 0.1},
      "x_sampling": "S_128x128",
      "y_sampling": "S_128x128",
      "x_width": 1,
      "y_width": 1
    },
    "axes": [{"axis": "x", "values": [-0.1, 0, 0.1]}],
    "optimization": {
      "bounds": [{"axis": "x", "minimum": -0.1, "maximum": 0.1}],
      "max_iterations": 30,
      "relative_step_tolerance": 0.001
    },
    "tolerance_axes": [{"axis": "x", "values": [-0.15, -0.1, -0.05, 0, 0.05, 0.1, 0.15]}],
    "max_evaluations": 250,
    "refine": true,
    "save_best": true
  }
}
```

`settings` 沿用 `run_pop` 请求，指定系统、视场、波长、输入光束、采样及窗口。需要 `fiber_type="AstigmaticGaussian"`、正的束腰半径参数0/1、`data_type="Irradiance"` 和 `save_output_beam=true`。

## 原生参数与坐标

AstigmaticGaussian 参数0/1为 X/Y 束腰半径，2/3为 X/Y 束腰位置，4/5为偏心。省略的2—5参数取0。`x/y/z/tilt_x/tilt_y` 均表示相对于 `settings` 的增量：

| 扫描轴 | 原生设置 | 单位 |
| --- | --- | --- |
| x、y | 接收参数4、5 | 镜头单位 |
| z | 接收参数2、3同时增加相同值 | 镜头单位 |
| tilt_x、tilt_y | TiltAboutX、TiltAboutY | 度 |

横向坐标采用原生 POP 的输出平面坐标系，`fiber_position` 沿用 ChiefRay 或 SurfaceVertex。Z改变接收高斯场在该评价面上的束腰位置，正号采用原生束腰位置约定；输入与接收束腰位置同为+5 mm时，已取得相同复场的单位耦合。倾角采用原生轴约定。接收场设置随各自分析对象关闭，光学曲面、solve和当前配置保持。

束腰半径采用原生高斯场的振幅降至峰值1/e、强度降至峰值1/e²的半径。在均匀介质中的理想圆对称高斯模型，可由真空波长、介质折射率与束腰计算发散角及等效NA；本请求直接指定模式尺寸和原生传播条件。

## 扫描、寻优与容差

`axes` 包含1或2个不同轴，每轴2—101个严格递增坐标，形成一维曲线或二维笛卡尔采样。均匀二维坐标生成 `values[y][x]` 网格；非均匀坐标通过 `rows` 和 `scan_coordinates` 返回。默认 `refine=true`，在每相邻坐标间增加中点。

`optimization` 可为最多5个轴给出边界。外层使用有界坐标模式搜索，每个候选通过原生 POP 评价；从满足边界的扫描最佳点开始，每轮尝试正负方向，无改善时减半步长。返回迭代终态、最终步长和边界标志。每个候选都从同一 `settings` 构造，重复姿态复用结果。

`tolerance_axes` 指定最佳姿态处的单轴切片，其余四个分量固定；省略时沿用扫描轴，空列表表示只执行扫描与寻优。返回相对选定最佳效率的 1/3 dB 左右交点、偏移量和宽度。使用最近的相邻括区，在损耗dB空间线性插值；零端点改用效率插值。范围未包含两侧交点时，状态为 `range_not_bracketing`。粗细切片宽度相对变化不超过0.5%时，`converged=true`。

`max_evaluations` 为2—2000，控制实际原生评价次数；`budget_seconds` 默认600秒，上限3600秒。预算用尽保留已完成候选并返回 `evaluation_or_time_budget`，未执行的容差切片保持缺省。运行中可用 `cancel_task`，随后继续查询至终态。

## 结果与复算

`rows` 包含姿态、阶段、接收/系统/总耦合效率、输入功率、子任务编号、实际设置和关闭结果；`summary.best` 为选定最佳姿态。长结果使用现有行分页、网格区域分页及 `export_analysis_image`。

`save_best=true` 时保存独立 ZOS 模型和同名 JSON 请求。JSON包含 `run_pop` 的完整接收设置、最佳姿态、效率及模型路径。打开候选模型后，执行其 `tool/arguments` 即可复算；文件型光束等依赖保留在请求的显式路径中。

当前原生对照包括五个扫描分量、偏心和离焦高斯复场、二维寻优、1/3 dB宽度、采样加密、候选重载、失败后复用及取消。效率参考绝对容差为5e−4。
