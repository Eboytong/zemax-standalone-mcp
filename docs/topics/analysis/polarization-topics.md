# 偏振专题与全瞳透射

2026-11-09补充：原生32×32全瞳平板透射在X/Y偏振和非偏振下与独立Fresnel、批量圆瞳及逐面主光线参考一致，最大误差3e-9；专题选择器和渐晕/吸收组合仍列为后续范围。相位传播分离诊断及具体条件见[数值控制记录](../../../development/evidence/PO-01/numerical-controls-20261109.md)。

四个专题均保留只传`kind`的原生报告入口，实际输入从报告表头返回。全瞳透射另外提供正式归一化批量追迹路径，支持视场、波长、采样及Jones选择；其余专题继续按各自设置入口推进。

## 相位像差输入选择

```json
{"request":{"kind":"phase_aberration","field":2,"wavelength":1,"polarization":{"jx":1,"jy":1,"x_phase":17,"y_phase":73}}}
```

`method=auto`在显式传入field、wavelength或polarization时采用`system_copy`路径。field/wavelength为正整数编号；省略field使用第1视场，省略wavelength使用源模型主波长，省略polarization沿用系统Jones。`method=system_copy`可强制此路径；`method=native`使用原生默认专题，与显式选择字段并用时返回UNSUPPORTED_SETTING。

系统副本固定当前已求值的几何依赖solve，交换所选视场至副本第一槽，把所选波长设为副本主波长，并写入Jones。实际值从正式系统数据和原生报告头核对。结果来自完整原生PhaseAberration专题，保留原生文本、rows和四条series。源系统的几何、solve、主波长及配置保持。

每次执行核对所有活动光学单元格及三条源/副本光线的位置、方向和状态。主波长改变导致瞳映射或光线瞄准差异时明确拒绝并关闭副本。`actual_settings.frozen_cells`记录副本固定的单元格，`geometry_before_analysis/geometry_after_analysis`记录几何核对，`ray_mapping_check`保留原始见证。最终关闭情况从`get_task_status.settings.resource_close`读取；结果文件可能在关闭前保存。

Cooke保留源主波长时的视场和非零Jones选择已与独立工作模型原生报告对照。切换到另一波长会改变代表光线映射，返回SETTING_REJECTED并保留原始比较，副本关闭；不能仅凭单元格几何相同认定波长选择等价。完整条目继续保留波长映射、有限共轭、坐标变换和镜面独立数值参考；见[选择证据](../../../development/evidence/PO-01/phase-copy-selection-20261109.md)。

偏振光线新增平板/球面受控参考：三种Jones下逐面Fresnel、归一化相干矩阵、坐标/方向、rows分页及保存重载通过。总透射解析误差最大3.045e-9；相干矩阵消去共同传播相位，绝对相位基准另行验收。正式任意光线/波长选择仍待接口确认。见[逐面参考记录](../../../development/evidence/PO-01/ray-topic-reference-20261109.md)。

| kind | 原生分析 | 结构化结果 |
| --- | --- | --- |
| `phase_aberration` | PhaseAberration | 瞳坐标表及弧矢/子午、X/Y相位四条曲线 |
| `polarization_ray_trace` | PolarizationRayTrace | 逐曲面角度、复场、振幅系数、相位及总透射 |
| `polarization_transmission` | Transmission | 视场与波长透射、视场总值及主光线逐面数据 |
| `fiber_coupling_settings` | FiberCouplingSettings | 系统、接收与总耦合效率，以及报告中的接收器设置 |

[请求示例](../../../examples/requests/polarization-topics.json)中的四个请求分别提交，沿用任务查询、`rows`/`series`分页和结果文件入口。相位单位按手册定义标记为waves，结果同时返回`phase_unit_verified=false`和单位来源；原生数值比较完成后再更新验收状态。

2026-11-08主区重放四份保留的真实原生文本，分别得到401行/4条曲线、7行逐面光线、9行视场波长透射和3行耦合效率。重放记录在`.local/evidence/development/BASE-04/parallel-01/polarization-retained-replay.json`。本次未创建原生实例；输入选择、Fresnel/复场参考及原生生命周期验收继续记录于D001。

实现及普通检查见[开发交接](../../../development/handoff.md)；完整请求以[运行时schema](../../reference/tool-schemas.json)为准。

2026-11-09原生控制确认：系统Jones设置会被相位像差、偏振光线和透射三个专题采用。透射结果支持非偏振说明及四行Jones偏振头两种格式，`input_header.jones`保留偏振输入。`update_system_settings`按活动条件及非零分量顺序写入偏振，核对最终组合并保留原有Unpolarized值。四专题执行后系统设置恢复通过。相位与直接复场参考仍约0.501 waves偏差，详细状态见[原生控制证据](../../../development/evidence/PO-01/controls-20261109.md)。

2026-11-09非恒定瞳补充：球面—平面无镀膜模型，X/Y逐光线独立Fresnel最大误差3.035e-9；X/Y/非偏振全瞳均值差8.303e-7，原生用例通过，设置和曲面恢复。见[验收记录](../../../development/evidence/PO-01/nonconstant-transmission-20261109.md)。


## 全瞳透射选择

```json
{"request":{"kind":"polarization_transmission","field":2,"wavelength":0,"sampling":32,"polarization":{"jx":1,"jy":1,"x_phase":30,"y_phase":120},"include_chief_ray":true}}
```

`method=auto`且只传kind时运行原生Transmission报告；显式传入选择参数时使用正式归一化真实光线追迹。`method=ray_trace`强制此路径；`method=native`与显式选择参数组合返回UNSUPPORTED_SETTING。原生专题设置对象仍为AS_Default，追迹路径记录实际调用参数及系统读回。

视场/波长0为全部，正整数为原生一基编号。`sampling`为8、16、32、64、128个直径区间，圆周包含在采样内；32区间为33×33格点中的797点，已用五种圆孔与本机原生32×32标签对照。polarization省略或null时使用当前系统偏振状态；显式Jones振幅归一化为单位入射强度，相位使用度。

积分透射为各光线出射功率之和除以入射功率之和。入射功率通过正式LDE.GetApodization(px,py)取得；几何追迹标识孔径截断和追迹错误，损失光线留在积分分母中。波长总值按所选系统波长权重计算。rows保留逐光线坐标、状态、入射功率、出射功率及单光线透射；这些功率是归一化量。零入射功率的单光线透射为null。

结果包含逐场/波长积分、可选逐面主光线总透射及相邻面相对透射、波长曲线和分页明细。默认返回主光线表；`include_chief_ray=false`可减少追迹任务。系统设置保持原值。


2026-11-09：PO-01.Transmission完整验收完成。默认原生报告、可选择批量追迹、GetApodization归一化、渐晕因子、吸收、Jones、多波长、分页/PNG、取消/复用/重载和关闭均有证据。详见[完整验收](../../../development/evidence/PO-01/transmission-complete-20261109.md)。

## 光纤积分方法归属

光纤结果的`integration_method`从原生首个非空标题识别，取`huygens`、`ray_based`或`null`；`integration_method_source`保留标题、来源和声明状态。未知标题的报告继续返回原生效率及文本。2026-11-09 Cooke报告识别为Huygens，保存重载和分页通过；默认专题方法归属沿用；可选择的圆形光纤参数另由FICL操作数提供。见[方法归属证据](../../../development/evidence/WP-01/fiber-method-identity-20261109.md)。

## 相位参考插值控制

2026-11-09：手册描述用主光线两侧光线插值参考相位。轴上Cooke以独立批量复场和逐段光程构造±0.005瞳点参考，两方向800个非中心点最大误差5.83e-10 waves，通过原2.78e-9门槛，并已新建原生会话复现。中心零值单独记录，零振幅分量为indeterminate。结果phase_reference补充插值定义，原生表值保持原样。正式输入选择及任意模型相位范围继续验收，见[详细证据](../../../development/evidence/PO-01/phase-neighbor-reference-20261109.md)。

2026-11-09离轴控制：四组轴上/5°、两种Jones及0.55/0.4861327µm工作副本实验中，沿光线起始参考与相邻点插值使5600个非中心点通过原相位门槛，最大6.45e-10 waves。模型状态保持及四次恢复通过，36任务成功并正常关闭；正式分析选择器及其他模型适用性继续验收。见[离轴参考记录](../../../development/evidence/PO-01/phase-conditions-reference-20261109.md)。


## 可选择的FICL光纤耦合

`fiber_coupling_settings`默认保留原生文本报告。`method=operand`使用正式MFE.GetOperandValue(FICL)；auto收到显式参数时选择此路径，native收到显式参数返回UNSUPPORTED_SETTING。参数为sampling=32/64/128/256、正整数field/wavelength、ignore_source、有限正source_na/receiver_na、integration=fast/huygens及use_polarization。操作数参数顺序依据本机2024 R2手册1116—1117页，并已核对实际列类型。

结果包含总耦合功率、复耦合振幅、三次原生查询参数、视场/波长身份及当前配置；rows分页分别返回power、real和imaginary。计算使用原生默认对准条件和圆形NA；椭圆NA、去心、倾斜与对准选择仍列入完整功能的剩余范围。源位于无穷远时，source NA变化须按原生适用条件解释。

Cooke的0.55µm、64×64、Huygens结果0.14806083709504725，与专题六位小数0.148061相符；36个直接查询与临时行一致。独立复场参考及完整参数范围继续验收，详见[操作数证据](../../../development/evidence/WP-01/fiber-operand-contract-20261109.md)。

## 可选择的偏振光线数据

`polarization_ray_trace`默认保留原生逐面文本报告。显式请求光线选择字段时，`method=auto`使用CODA操作数；`method=operand`强制选择；`method=native`与显式选择器并用时返回UNSUPPORTED_SETTING。字段包括正整数field/wavelength、surface（0表示像面，其余采用顺序曲面编号）及[-1,1]内的归一化pupil_x/pupil_y。

CODA逐项返回S/P反射、透射、吸收、复振幅以及Ex/Ey/Ez复分量和相位；结果携带每个数据码的原生参数、系统Jones、视场/波长、曲面和配置，支持rows分页。参数顺序依据本机2024 R2手册1130页，实测列为Surface、Wave、Field、Data、Px、Py。

Cooke受控平板模型中，按场1、波长1、瞳点(0,1)查询表面1、表面2及像面，CODA复电场与正式批量偏振追迹三个复分量逐项通过1e-6+1e-6×参考值门槛。任务分页、模型状态保持和正常关闭通过。该选择路径的原生记录见`.local/evidence/development/PO-01/polarization-operand-contract-r2-20261109/probe.json`，MCP交叉验收由`tests/native/test_polarization_topic_reference_live.py::test_polarization_ray_coda_selects_field_wave_surface_and_matches_batch_field`执行。完整逐面原生专题仍保留；任意模型的相位基准沿用独立验收状态。

CODA相位数据码110—113的原生值按弧度保存于native_queries；公开phase_*_deg结果换算为度，native_phase_unit明确为radians。逐面膜层系数、复振幅和非零电场相位已与原生逐面报告对照。

两视场、两波长及37/90度Jones相位的选定面验证已通过；phase_xy_deg为X相位减Y相位（周期360度）。取消后可复用，保存重载24种结果保持。任意选择下完整逐面几何、基底和传播字段及全局坐标仍待正式出口。

CODA返回29种量，另含累计`polarized_transmitted_intensity`和`unpolarized_transmitted_intensity`，以及`ellipse_major_axis`、`ellipse_minor_axis`、`ellipse_angle_deg`。椭圆由局部XY电场投影定义；长短轴保留原生电场振幅，方向角原生为度，`native_ellipse_angle_unit`明确记录。新增五行追加于原24行之后，rows分页可读取。
