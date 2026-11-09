# 重点面型求解支持
适用本机 OpticStudio 2024 R2（24.2.0、build 240529、PremiumEdition）。完整机器可读记录见 [solve-support.json](../../reference/solve-support.json)。
原生 available_solves、当前模式能否采用、光学数值是否符合请求分别判断。get_capabilities.solve_validation 返回紧凑摘要和详细记录位置，原生支持列表保持原样。
## 数值检查
| 面型 | F-number | 边缘光线高度 | 主光线高度 | 边缘厚度 | 位置 |
|---|---|---|---|---|---|
|Biconic|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|
|CoordinateBreak|原生未采用（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|
|EvenAspheric|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|
|GridPhase|原生未采用（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|
|GridSag|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|
|OddAsphere|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|
|Paraxial|原生未采用（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|
|Standard|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|
|Toroidal|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|数值通过（历史参考）|

CoordinateBreak parameter_1..4 的主光线拾取均通过位置或方向归零及保存重载检查。
数值通过包含模式与参数回读、独立追迹或Sag/厚度关系、替换保护、保存重载及再次计算。MarginalRayHeight覆盖0、±0.7瞳区；Position覆盖前向、自身与后向参考。Toroidal/Biconic记录X/Y两主方向，F-number按Y方向近轴边缘光线斜率 -1/(2F) 验证。模型使用F=4、高度0.1/1 mm、径向1 mm处边缘厚度2 mm及明确区间长度；实际处方见各基线。
GridSag/GridPhase夹具具有明确的非零数据文件。每个组合从独立工作基线开始，官方Cooke镜头和手册未修改。
## 当前状态下原生拒绝
Paraxial、CoordinateBreak、GridPhase 半径F-number求解未被原生采用；不能将该半径列的原生枚举当作有效曲率控制。其余10个拒绝项如下，直接原生API与MCP逐项对应：
| 面型 | 单元格 | 模式 |
|---|---|---|
|CoordinateBreak|conic|surface_pickup（历史参考）|
|CoordinateBreak|conic|variable（历史参考）|
|CoordinateBreak|radius|surface_pickup（历史参考）|
|CoordinateBreak|radius|variable（历史参考）|
|CoordinateBreak|semi_diameter|fixed（历史参考）|
|CoordinateBreak|semi_diameter|surface_pickup（历史参考）|
|GridPhase|radius|surface_pickup（历史参考）|
|GridPhase|radius|variable（历史参考）|
|Paraxial|radius|surface_pickup（历史参考）|
|Paraxial|radius|variable（历史参考）|

## 验收级别
936个登记组合中：46个特殊组合有光学数值依据；279个有状态、值和保存重载依据；13个有当前状态下原生拒绝对照；580个不在原生支持列表；18个不适用。49个专项待验组合已逐项归入46个数值通过与3个原生未采用，不能将全部936个组合称为光学数值通过。
## 执行
在项目目录执行 .venv/Scripts/python.exe -B -m pytest tests/native/test_solve_support_live.py --run-zemax -q。使用 -k 配合面型或组合ID可单独执行。直接原生对照在MCP实例启动前完成并关闭；原生用例串行运行，禁止与GUI或其他原生进程并发。

请求示例见[solve_requests.json](../../../examples/requests/solve_requests.json)。每条示例须先打开对应组合的独立baseline.zos，不连续叠加于另一组合结果。

## 官方顺序样例参数范围

有限清单为`tests/reference_data/official-surfaces.json`的22个原生TYPE，涵盖普通、GRIN、DLL和混合模式。`tests/native/test_official_surface_scope_live.py`从独立工作副本读取原文件参数，逐活动数值单元格检查Fixed/Variable的实际采用与保存重载。参数传递及模式持久化不代替Sag、出射方向和求解目标的光学依据；混合模式不套用九类普通面型矩阵。

官方样例450次单元格/模式请求的原生记录包含438次模式与重载一致、11次原生拒绝、1次Hologram2状态相关的重载差异。公共入口对该差异执行下述持久化保护。11条拒绝分别绑定官方样例及其单元格；既有13项矩阵结论保留各自基线，详表分别追溯。

## Hologram2 模式持久化

本机2024 R2的Hologram2 `parameter_13` 是 `Volume Hologram?`：0选择表面全息，1选择体全息。该值改变物理模型，应按设计要求选择；不能仅为保持Variable而从0改为1。手册依据为2.3.1.2.49的参数定义，体全息的附加参数仍须按模型配置。

| parameter_13值 | Fixed | Variable |
| --- | --- | --- |
| 0 | 值与模式可保存重载 | 原生即时采用，但重载为Fixed；公共入口返回UNSUPPORTED_SOLVE |
| 1 | 值与模式可保存重载 | 原生即时采用，值与模式均可保存重载 |

`MakeSolveVariable`与`CreateSolveType/SetSolveData`的独立原生对照在`.zos`、`.zmx`上结果一致；连续参数`parameter_1`在两种标志值下均可保持Variable。原生对照及真实stdio依据（历史参考）限定于该参数、样例和本机版本，未将该结论扩展到其他面型或求解。

`update_surfaces`按本批请求的目标面型、参数值和模式预检查，`set_variables`按当前值预检查。已知不可靠请求在检查点和任何写入前拒绝，修订号不变，`partial_changes_possible=false`。已有Variable时将值改为0，须在同一曲面修改中显式设置Fixed。`get_surfaces`保留原生`available_solves`，在该单元格另返回`solve_persistence`；`get_capabilities.solve_validation.persistence_limits`给出状态限制。

显式启用体全息并设置Variable：

```json
{"changes":[{"surface":1,"parameters":{"13":1},"solves":{"parameter_13":{"mode":"variable"}},"replace_solves":true}]}
```

关闭体全息并设为Fixed：

```json
{"changes":[{"surface":1,"parameters":{"13":0},"solves":{"parameter_13":{"mode":"fixed"}},"replace_solves":true}]}
```

已启用体全息时，亦可调用`set_variables`：`{"variables":[{"surface":1,"cell":"parameter_13","variable":true}]}`。普通连续参数继续使用原有接口。仅设置与重载通过不代表该体全息模型的效率或光学数值已验收。
