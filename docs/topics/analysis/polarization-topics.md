# 偏振专题与全瞳透射


四个专题均保留只传`kind`的原生报告入口，实际输入从报告表头返回。全瞳透射另外提供正式归一化批量追迹路径，支持视场、波长、采样及Jones选择；其余专题继续按各自设置入口推进。

## 相位像差输入选择

```json
{"request":{"kind":"phase_aberration","field":2,"wavelength":1,"polarization":{"jx":1,"jy":1,"x_phase":17,"y_phase":73}}}
```

`method=auto`在显式传入field、wavelength或polarization时采用`system_copy`路径。field/wavelength为正整数编号；省略field使用第1视场，省略wavelength使用源模型主波长，省略polarization沿用系统Jones。`method=system_copy`可强制此路径；`method=native`使用原生默认专题，与显式选择字段并用时返回UNSUPPORTED_SETTING。

系统副本固定当前已求值的几何依赖solve，交换所选视场至副本第一槽，把所选波长设为副本主波长，并写入Jones。实际值从正式系统数据和原生报告头核对。结果来自完整原生PhaseAberration专题，保留原生文本、rows和四条series。源系统的几何、solve、主波长及配置保持。

每次执行核对所有活动光学单元格及三条源/副本光线的位置、方向和状态。主波长改变导致瞳映射或光线瞄准差异时明确拒绝并关闭副本。`actual_settings.frozen_cells`记录副本固定的单元格，`geometry_before_analysis/geometry_after_analysis`记录几何核对，`ray_mapping_check`保留原始见证。最终关闭情况从`get_task_status.settings.resource_close`读取；结果文件可能在关闭前保存。



| kind | 原生分析 | 结构化结果 |
| --- | --- | --- |
| `phase_aberration` | PhaseAberration | 瞳坐标表及弧矢/子午、X/Y相位四条曲线 |
| `polarization_ray_trace` | PolarizationRayTrace | 逐曲面角度、复场、振幅系数、相位及总透射 |
| `polarization_transmission` | Transmission | 视场与波长透射、视场总值及主光线逐面数据 |
| `fiber_coupling_settings` | FiberCouplingSettings | 系统、接收与总耦合效率，以及报告中的接收器设置 |

[请求示例](../../../examples/requests/polarization-topics.json)中的四个请求分别提交，沿用任务查询、`rows`/`series`分页和结果文件入口。相位单位按手册定义标记为waves，结果同时返回`phase_unit_verified=false`和单位来源；原生数值比较完成后再更新验收状态。






## 全瞳透射选择

```json
{"request":{"kind":"polarization_transmission","field":2,"wavelength":0,"sampling":32,"polarization":{"jx":1,"jy":1,"x_phase":30,"y_phase":120},"include_chief_ray":true}}
```

`method=auto`且只传kind时运行原生Transmission报告；显式传入选择参数时使用正式归一化真实光线追迹。`method=ray_trace`强制此路径；`method=native`与显式选择参数组合返回UNSUPPORTED_SETTING。原生专题设置对象仍为AS_Default，追迹路径记录实际调用参数及系统读回。

视场/波长0为全部，正整数为原生一基编号。`sampling`为8、16、32、64、128个直径区间，圆周包含在采样内；32区间为33×33格点中的797点，已用五种圆孔与本机原生32×32标签对照。polarization省略或null时使用当前系统偏振状态；显式Jones振幅归一化为单位入射强度，相位使用度。

积分透射为各光线出射功率之和除以入射功率之和。入射功率通过正式LDE.GetApodization(px,py)取得；几何追迹标识孔径截断和追迹错误，损失光线留在积分分母中。波长总值按所选系统波长权重计算。rows保留逐光线坐标、状态、入射功率、出射功率及单光线透射；这些功率是归一化量。零入射功率的单光线透射为null。

结果包含逐场/波长积分、可选逐面主光线总透射及相邻面相对透射、波长曲线和分页明细。默认返回主光线表；`include_chief_ray=false`可减少追迹任务。系统设置保持原值。



## 光纤积分方法归属


## 相位参考插值控制




## 可选择的FICL光纤耦合

`fiber_coupling_settings`默认保留原生文本报告。`method=operand`使用正式MFE.GetOperandValue(FICL)；auto收到显式参数时选择此路径，native收到显式参数返回UNSUPPORTED_SETTING。参数为sampling=32/64/128/256、正整数field/wavelength、ignore_source、有限正source_na/receiver_na、integration=fast/huygens及use_polarization。操作数参数顺序依据本机2024 R2手册1116—1117页，并已核对实际列类型。

结果包含总耦合功率、复耦合振幅、三次原生查询参数、视场/波长身份及当前配置；rows分页分别返回power、real和imaginary。计算使用原生默认对准条件和圆形NA；椭圆NA、去心、倾斜与对准选择仍列入完整功能的剩余范围。源位于无穷远时，source NA变化须按原生适用条件解释。


## 可选择的偏振光线数据

`polarization_ray_trace`默认保留原生逐面文本报告。显式请求光线选择字段时，`method=auto`使用CODA操作数；`method=operand`强制选择；`method=native`与显式选择器并用时返回UNSUPPORTED_SETTING。字段包括正整数field/wavelength、surface（0表示像面，其余采用顺序曲面编号）及[-1,1]内的归一化pupil_x/pupil_y。

CODA逐项返回S/P反射、透射、吸收、复振幅以及Ex/Ey/Ez复分量和相位；结果携带每个数据码的原生参数、系统Jones、视场/波长、曲面和配置，支持rows分页。参数顺序依据本机2024 R2手册1130页，实测列为Surface、Wave、Field、Data、Px、Py。


CODA相位数据码110—113的原生值按弧度保存于native_queries；公开phase_*_deg结果换算为度，native_phase_unit明确为radians。逐面膜层系数、复振幅和非零电场相位已与原生逐面报告对照。

两视场、两波长及37/90度Jones相位的选定面验证已通过；phase_xy_deg为X相位减Y相位（周期360度）。取消后可复用，保存重载24种结果保持。任意选择下完整逐面几何、基底和传播字段及全局坐标仍待正式出口。

CODA返回29种量，另含累计`polarized_transmitted_intensity`和`unpolarized_transmitted_intensity`，以及`ellipse_major_axis`、`ellipse_minor_axis`、`ellipse_angle_deg`。椭圆由局部XY电场投影定义；长短轴保留原生电场振幅，方向角原生为度，`native_ellipse_angle_unit`明确记录。新增五行追加于原24行之后，rows分页可读取。
