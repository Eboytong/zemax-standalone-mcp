# 均温响应与焦点补偿

`run_analysis` 的 `thermal_compensation` 读取已有 MCE 温度配置，计算热变形后的折射率、曲率、厚度、空气间隔、EFL、RMS 光斑和波前；可调用原生多配置局部优化，为每个温度计算一个空气间隔补偿位置。

```json
{
  "request": {
    "kind": "thermal_compensation",
    "configurations": [1, 2, 3],
    "reference_configuration": 1,
    "compensation_surface": 2,
    "minimum_gap": 40,
    "maximum_gap": 60,
    "field": 1,
    "wavelength": 1,
    "rings": 3,
    "optimize": true,
    "replace_compensation_solves": true,
    "cycles": "Fixed_10_Cycles",
    "budget_seconds": 120
  }
}
```

先通过 `update_system_settings` 设置材料目录、环境折射率修正和机械 TCE，通过 `update_configurations` 建立 TEMP、CRVT、THIC 等配置行及 thermal pickup。创建配置和写入 pickup 分别调用，使用实际回读的配置编号。`configurations` 接受 2–20 个不同编号，至少含两个不同温度；`reference_configuration` 须属于该列表。

补偿面须位于像面之前，且其后为空气间隔；MCE 中须有唯一对应的 THIC 行。`minimum_gap` 和 `maximum_gap` 是正的绝对间隔边界，使用系统镜头单位。基线间隔须在范围内。`replace_compensation_solves=true` 显式允许在工作副本中将该间隔的拾取改为变量。其他热拾取继续生效。该补偿表示各温度的独立执行器位置。

`optimize=false` 读取各温度响应并保存模型。开启优化时，以指定视场和波长的 RSCE 为目标，调用原生 DampedLeastSquares；每个温度使用一个 MCE 变量，并加入 CTGT/CTLT 间隔边界。返回后再检查实际间隔和其他几何参数。预算用于原生优化步骤。

结果中的 `before`、`after` 包含每个温度的几何、折射率及像质；`compensation_displacement` 是相对该温度基线间隔的位移。RMS 光斑、EFL 和位移使用镜头单位，RMS 波前使用 waves，温度为 °C，TCE 为 ppm/°C。`series` 提供补偿前后光斑曲线，`rows` 支持现有分页，`summary.recommended_model` 指向保存的原生模型。源模型的配置、solve、MFE 和修订号保持原值。
