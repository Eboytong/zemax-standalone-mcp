# CO-01.DiffEfficiency2D：原生 Hologram1 证据矩阵（阶段一）

- 声明范围：原生 Hologram1 体全息二维网格（角度×波长），S/P 双偏振；角度 20.16505117707799–32.96505117707799°、波长 0.45–0.65 µm，效率无量纲。依据 `scope.json` 原生声明与 D010 item 3。
- 证据运行：`…\.local\runs\runs\diff_efficiency_offaxis059_native_bdfaeee137`（会话 `d5946d8262334d3cb2ff2ca6358a2622`）。
- 参考/容差：网格逐点独立 Kogelnik 参考（抽样），`atol=1e-6, rtol=1e-5`。

| 维度 | 既有证据（文件 / 定位） | 结论 | 缺口 / 复测条件 |
| --- | --- | --- | --- |
| 当前声明 | `scope.json`、`development-groups.json` D010 item 3 | 仅原生 Hologram1 计入 | 无 |
| 输入身份 | calls.json：同一 Hologram1 模型与 Angle 场；请求同给 `min_angle/max_angle` 与 `min_wavelength/max_wavelength` | 两轴区间同时生效 | 用例未断言两轴各自回读 |
| 设置写入 | `configure_diff_efficiency` → `SampleSize='S_64x64'`、`MinAngle/MaxAngle`、`MinWavelength/MaxWavelength` | 只写请求字段 | — |
| 设置回读 | `task.settings.native`：`SampleSize='S_64x64'`、`MinWavelength=0.45`、`MaxWavelength=0.65`、`MinAngle=20.16505117707799`、`MaxAngle=32.96505117707799`，其余 −1 默认、`IsValid=true`；`evaluation_conditions.surface_type='Hologram1'` | 回读完整 | 未断言四个边界与 SampleSize |
| 结果（网格） | 任务 `65879ef9acd24bfa8a3cc71b47177a89`（S）、`672d09570c814f4b93452ee621f11eaa`（P）：grid 0，`nx=ny=64`，`dx=0.19999999999999996`、`min_x=20.16505117707799`（度）；`dy=0.003125`、`min_y=0.45`（µm）；末列 x=32.76505117707799、末行 y=0.646875（两轴均不含上界）；`x_label='Angle'`、`y_label='Wavelength'`、`value_label='Diffraction efficiency'`；`array_order='native Values dimension 0, dimension 1'`，取值为 `values[行=波长][列=角度]` | 网格尺寸、起点、步长、轴对应明确 | 未断言 nx/ny 与 `S_64x64` 对应、未断言 `value_unit`、轴对应仅由参考抽样隐式成立 |
| 单位 | grid `x_unit='degrees'`、`y_unit='micrometers'`、`value_unit='dimensionless'`；保留 `native_axes` | 两轴单位与量纲明确 | 未断言 `value_unit='dimensionless'` |
| 数值 / 参考 | checks.json：`S/P diff_efficiency_2d angle=<x> wave=<y>` 各 64 条，共 128 条全部 passed（x,y 索引 0,8,…,56），最大绝对差 5.385047963102352e-11（label `S … angle=23.36505117707799 wave=0.475`） | 抽样点与独立参考一致 | **覆盖 64/4096 节点 = 1.56%**，不得表述为全网格验证 |
| 切片一致性 | 本 Hologram1 运行**未**做「网格中央列 vs 波长扫描、中央行 vs 角度扫描」比对；该类比对仅存在于 `diff_efficiency056_probe_e9ebda7239`（192 检查，1e-8/1e-7，最大 5.69e-11），其 `evaluation_conditions.surface_type='Hologram2'` | Hologram2 方法可信，但**不能**充当 Hologram1 切片证据 | 需在 Hologram1 用例中补切片断言（同一运行内用网格与一维结果比对，无需新增原生作业以外资源） |
| 分页 | `get_task_result(grid=0,x_start=2,y_start=1,width=3,height=2)` 调用成功（S/P 各一次） | 网格分页可用 | 未与全量 grid 对应子块比对 |
| 图像 | `S/P_diff_efficiency_2d.png` | 两偏振各一张 | 未校验文件 |
| 恢复 / 重载 | `offaxis_saved.zos` 重开后 `get_surfaces` 与 settings 相等 | 重载保持 | — |
| 任务失败 | ObjectHeight 失败用例为角度 kind；2D 未单独失败 | 失败机制成立 | 若审查要求 2D 专属失败证据，可追加一次（非必需） |
| 取消 | 2048×2048 `diff_efficiency_2d` 运行中取消 → `cancelled`、`close_attempted=true`（`cancellation.json`：active_at_request=true, closed=true） | 取消证据属 2D 本身 | — |
| 关闭 | 每任务 `close_attempted=true`；close_receipt `native.closed=true, forced=false`；`disconnect` 正常 | 关闭齐备 | — |

## 缺口（断言层面）

1. 四个边界与 `SampleSize` 回读断言；2. `nx=ny=64` 与 `S_64x64`、`dx/dy`、`min_x/min_y`、`value_unit='dimensionless'` 断言；3. 轴方向显式断言（行=波长、列=角度）；4. Hologram1 切片一致性断言（中央行/列与角度、波长扫描在对应点相等，容差沿用既有 1e-8/1e-7 的切片口径或按审查指定）；5. 分页子块等值；6. 结论中明示 1.56% 抽样覆盖。

## 判定

网格数值（128 抽样点）、单位、分页、图像、取消、关闭证据齐备 → **implemented**；切片一致性与断言补强在 Hologram1 用例内完成后转 done。Hologram2 的 056 探针证据仅作方法参考，不计入本项。
