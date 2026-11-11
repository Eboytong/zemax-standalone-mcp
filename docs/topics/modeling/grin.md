# Gradient2与Gradient3梯度折射率

使用`update_surfaces`设置面型与系数，`get_surfaces`读取实际单元格、solve及`grin`参数定义，`run_analysis(kind="grin_profile")`读取折射率曲线。`get_capabilities`的`grin_surfaces`提供两种面型的参数表。

设当前镜头长度单位为$L$，$r=\sqrt{x^2+y^2}$，$z$从介质前表面顶点起算。两类面型定义其后厚度区间的介质。

$$
\text{Gradient2:}\quad n^2(r)=n_0+N_{r2}r^2+N_{r4}r^4+N_{r6}r^6+N_{r8}r^8+N_{r10}r^{10}+N_{r12}r^{12}
$$

$$
\text{Gradient3:}\quad n(r,z)=n_0+N_{r2}r^2+N_{r4}r^4+N_{r6}r^6+N_{z1}z+N_{z2}z^2+N_{z3}z^3
$$

| 参数编号 | Gradient2 | Gradient3 | 单位 |
| --- | --- | --- | --- |
| 1 | Delta T追迹积分步长 | Delta T追迹积分步长 | $L$ |
| 2 | 常数项$n_0$，即轴上折射率平方 | 常数项$n_0$，即原点折射率 | 无量纲 |
| 3 | $N_{r2}$ | $N_{r2}$ | $L^{-2}$ |
| 4 | $N_{r4}$ | $N_{r4}$ | $L^{-4}$ |
| 5 | $N_{r6}$ | $N_{r6}$ | $L^{-6}$ |
| 6 | $N_{r8}$ | $N_{z1}$ | $L^{-8}$或$L^{-1}$ |
| 7 | $N_{r10}$ | $N_{z2}$ | $L^{-10}$或$L^{-2}$ |
| 8 | $N_{r12}$ | $N_{z3}$ | $L^{-12}$或$L^{-3}$ |

Gradient2常数项2.25对应轴上物理折射率1.5。系数按原生值写入；省略字段保持当前值。改变面型使用`replace_solves=true`确认参数和solve关系的改变。正积分步长控制数值追迹精度，按光线路径加密检查。

以下为`update_surfaces`的工具参数，适用于至少有一个内部曲面的毫米单位模型：

```json
{"changes":[{"surface":1,"surface_type":"Gradient2","thickness":2,"semi_diameter":0.5,"parameters":{"1":0.005,"2":2.25,"3":-0.02,"4":0.001,"5":0,"6":0,"7":0,"8":0},"solves":{"parameter_3":{"mode":"variable"}},"replace_solves":true}]}
```

工具`run_analysis`的请求：

```json
{"request":{"kind":"grin_profile","surface":1,"wavelength":1,"show_index_vs":"X","minimum_x":-0.5,"maximum_x":0.5,"y_value":0,"z_value":1}}
```

通过任务状态和结果工具读取`series`；曲线纵轴为物理折射率，横轴为当前镜头长度单位。`get_surfaces`的`cells.parameter_3.solve`返回实际Variable状态；`grin.parameters`给出名称、编号及单位，与分页选取的单元格对应。

这两类系数采用无色散定义，波长选择用于标记分析条件。检查计算区域内Gradient2多项式为正、Gradient3折射率为正，并使用原生消息与逐光线错误定位超出有效区域的输入。需要色散的梯度介质时，通过对应的原生材料/面型定义建模。
