# SagTable制造数据

当前为implemented。三准则及反向全口径曲线已接入，最新证据见 `.local/evidence/development/MF-01/progress622-dsag-fit.json`。默认MinimumVolume提供原生BFSD摘要；MinimumRMS的物理顶点偏移固定为0，带偏移和反向曲线的物理偏移继续待补。

2026-11-09等形面控制：Zernike归一化半径5/10及项数1/4均保持同一拟合半径；解析矢高/斜率通过，但与独立带偏移RMS半径仍差3.8385445e-5mm，超过5e-6mm。DSAG/SSAG在同一模型内一致；面型间拟合差异、制造偏移及反向摘要继续待确认。详见[本轮证据](../../../development/evidence/MF-01/manufacturing-controls-20261109.md)。

```json
{"request":{"kind":"sag_table","surface":2,"minimum_radius":0,"maximum_radius":5,"samples":51}}
```

曲面编号从1开始；半径使用镜头单位。默认两端半径0表示使用0至当前净半口径；显式区间必须非负且递增。samples为2–10001，包含两端，默认51。采样沿局部x=0、正Y轴。

`summary` 来自BFSD的八项正式查询：曲率、半径、顶点偏移、最大去除深度、去除体积、最大斜率差、RMS去除深度及RMS斜率差。criterion为MinimumVolume，原生参数和当前配置写入actual_settings/native_query_arguments。拟合区间使用请求范围。

`rows`返回Y、sag、BFS sag、偏离量、去除深度、曲面斜率、BFS斜率及斜率差。sag使用原生LDE.GetSag，曲面斜率使用SSLP，BFS逐点sag/斜率使用原生拟合球曲率的解析式。所有坐标沿用原始曲面局部坐标。

MinimumVolume的 `signed_vertex_deviation=sag−BFS sag−顶点偏移` 保留原始符号；`removal_depth=direction×signed_vertex_deviation` 给出材料去除深度。`manufacturing_direction` 记录方向（+1或−1）、原生BFSD球面/偏移和三个径向GetSag见证、容差及公式。玻璃出空气面可采用−1；材料侧导致的原生拟合球和偏移变化均保留原值。见证同时出现超容差的正负深度，或后续输出行穿过拟合毛坯时返回具体结果错误。零去除时两方向等价，结果记录该状态。曲面几何偏离和斜率继续保留局部坐标符号。

原生专题文本使用自身差分斜率，凹面顶点附近与SSLP查询存在差异，结果注明来源。

长度、斜率和体积单位分别为镜头单位、无量纲及镜头单位立方。平面BFSD可返回1e12有限半径，原值保留并标记curvature_state=planar；实际返回无限半径时用null和radius_state=infinite表示。

rows支持start/count分页，三个series分别提供sag、去除量和斜率曲线，支持既有图像导出。查询过程保持模型修订及编辑器状态；取消保留已完成行。原生异常保留操作数/参数及原始消息，点查询失败保留已完成行。有孔径时使用任务自有模型副本计算未截断斜率，副本在成功、失败和取消时关闭。

光阑面的原生 `None` 孔径可自动恢复为 `FloatingAperture`。斜率自有副本在此条件下采用同心圆包围全部查询半径，外半径为查询上限加 `max(上限,1)×1e-6` 镜头单位；内半径和X/Y偏心均为0。最终类型及四项实际值须回读一致，记录在 `slope_query_copy.actual_copy_circle`；源模型孔径保留。副本不能采用该设置时继续返回具体拒绝。

抛物面独立解析与径向积分、平面/球面零去除、凹面符号、曲面2选择、环形区间、分页/绘图/取消复用及保存重载通过。行容差1e-8+1e-6×参考值；统计容差1e-6+1e-5×参考值，体积绝对容差1e-5。原生专题文本已取得并保存。平面测试对无限半径的旧假设和实际1e12输出保留在native371-sag.xml，修正测试见native373-lifecycle.xml。

仍待完成：SagTable专用设置的正式写入/回读和完整准则范围；离轴口径、非对称/Composite及配置/单位条件。SurfaceSlopeCross的三种BFS设置可写入并回读，导出CFG后SagTable.LoadFrom均返回false，文本仍为默认曲面1/MinimumVolume；见probe374-cfg-transfer。解除条件为可确认采用的SagTable专用设置入口或对应完整计算等价路径。MF-01与MA-01共享同一条目和证据，当前不增加B005完成计数。


2026-11-07 SagTable准则推进425：四种SSAG/SSLP准则查询均已自然完成；类型化SurfaceSlopeCross三准则/ReverseDirection的设置回读及四份半径报告取得，全部工具和两会话正常关闭。新增sphere-data识别/残差检查，80项相关普通通过；4种重建半径与原生报告显示精度一致。确认反向SSLP(BFS3)仍使用BFS0球面，和SSAG/typed反向报告不同；带偏移RMS的SSAG顶点0无法作为制造物理偏移0。保留原始结果，现有BFSD最小体积入口保持原定义，完整准则的制造偏移/全局统计及其他条件继续implemented，不增加计数。证据MF-01/progress425-criteria.json。B0054/10、剩余131组保持；当前无运行原生句柄。

2026-11-07 统计推进516–519：高阶曲面 `R=±40 mm, conic=-1, A4=±1e-5, A6=∓1e-8` 区分了摘要采样与连续面积积分。原生518的正、负整孔径及1–5 mm环形区间三项通过；519在实际MCP输出中复核新增采样元数据与环形统计通过。条件是使用原生BFSD曲率及物理顶点偏移，再用独立解析sag/斜率核对统计；本轮不据此声明独立BFS拟合通过。

在这些受控条件下，原生摘要对应1000个等长区间、1001个含两端的节点 `r_i=lo+i*(hi-lo)/1000`。RMS为 `sqrt(sum(r_i*d_i²)/sum(r_i))`，体积为 `2*pi*delta_r*sum(r_i*removal_depth_i)`。体积采用含端点矩形和；内边界项对环形区间不可省略。手册描述“1000等间距Y点”，本机观察到的离散节点定义另存于 `statistics_sampling.observed_reference`，其验证范围明确列出。请求的 `samples` 控制rows，与原生摘要采样独立。原生摘要数值继续原样返回。

516无权RMS假设失败；517省略内边界的体积少2.78566424e-5 mm³，正负整孔径通过、环形失败；518含端点预测三项通过原统计/体积容差，519最终输出复核通过。普通519共21通过。详见 `.local/evidence/development/MF-01/progress519-statistics.json`。完整准则的制造偏移/摘要出口及非对称/Composite等条件仍保留implemented；MinimumVolume对应BFSD的明确正式定义，其他准则的曲率识别沿用425。


2026-11-07 执行537–542：补齐MinimumVolume的毫米/厘米、R40/R60两当前配置，以及零间隔EvenAspheric Add-on/Base叠加面检查。两种单位保存重载后仍采用配置2，长度/体积单位及解析sag/斜率/BFS半径正确；Composite采用总sag=.003*r²及其解析斜率和拟合球。native541的三组SagTable用例共319个数值检查通过，最大绝对误差1.1979751e-11；第四个受影响MCE扫描回归通过。所有会话断连，查询任务终态成功、无独立分析句柄，曲面/solve、配置、系统、MFE保持。537首次在MCE精度检查阶段失败，538探查及542共用修复后通过，原失败保留。

本轮证明上述条件下的MinimumVolume行数据及BFS半径。高阶摘要统计沿用519；完整准则制造偏移/统计、非对称与偏轴口径继续保留。别名MF-01/MA-01同为implemented，不计新增完成项。证据MF-01/progress542-units-configurations-composite.json。

执行552–558补齐旋转截面与偏心孔径条件。`rotational_symmetry_check`保留三半径、八方位的原生GetSag检查；检测到非对称见证时返回UNSUPPORTED_MODEL。有限采样的通过范围写入结果。Biconic的Rx100/Ry50被拒绝，同会话改为Rx=Ry50后通过解析球面参考。

制造统计采用完整径向毛坯区间，偏心孔径作为实际设置返回。原生SSLP会将孔径外斜率置零；有孔径时在CopySystem副本中清除目标面孔径与拾取，并回读当前配置和孔径类型，再查询SSLP。每行同时返回有效`slope`、`slope_source`和`active_model_native_slope`，`slope_query_copy`记录副本身份与关闭结果。源模型GetSag和BFSD摘要继续使用活动系统。清除被拒绝时保留原生失败，关闭失败触发重连并保留原始错误。

native553首次偏心孔径用例暴露SSLP截断，原失败保留。修复后的native555通过；native557的13项定向回归通过，覆盖孔径、非对称拒绝、单位、配置、Composite、高阶统计、符号、分页、绘图及重载。native558在副本已打开、逐行采样时取消，确认关闭、源模型/solve/系统/MFE/MCE保持并可复用；1项通过。斜率与sag沿用1e-8+1e-6×参考值。

正式2024R2 Sag Table说明：Y截面用于旋转对称面，去除深度和体积摘要仅在MinimumVolume时报告。因此剩余动作按准则区分输出：取得完整准则选择、设置采用及曲线/物理偏移契约；其他准则的去除统计按原生适用条件记录。MF/MA两入口共享此状态，B006仍3/10。


2026-11-07 执行576–582：请求新增`best_fit_sphere`（MinimumVolume/MinimumRMS/MinimumRMSWithOffset，默认MinimumVolume）和`reverse`（默认false，仅MinimumVolume）。新增曲线路径要求两个半径均为0，拟合范围为原生完整净半口径；显式局部区间返回参数错误。示例见`examples/requests/sag-table-criteria.json`。

默认MinimumVolume沿用BFSD八项摘要。其他两准则及反向MinimumVolume使用正式SSAG的Remove=2、BFS=1/2/3，从四个原生坐标恢复球面，检查球面残差，再返回完整采样曲线与解析球面斜率。`native_query_arguments`保留每次参数及原值；`sphere_reconstruction.samples`保留原生GetSag/SSAG样本。采用原始SSLP曲面斜率，从恢复曲率解析计算球面斜率，避开425已记录的SSLP反向球面差异。

这些新增曲线的`summary.vertex_offset`及`rows.removal_depth`为null，`manufacturing_state=unavailable`。`data_piston`描述数值曲线的常量项；物理制造偏移继续等待正式契约。第二个series输出deviation，可分页并导出PNG。完整条目仍为implemented，MF/MA别名同步，B006保持5/10。

582正负抛物面各三种新增曲线，共402项检查通过；独立解析行数据最大差8.7153e-15，独立设置SurfaceSlopeCross的报告半径最大差4.1108e-7（容差5e-6）。7项原生包含既有MinimumVolume解析、符号、环形区间、分页/绘图/取消复用与重载回归；68项普通通过。新用例保存重载后检查曲面/solve、系统、MFE/MCE并正常断连，PNG已查看。测试阶段的产物类型、编码、复合任务资源字段和重名保存错误分别保留578–581；最终582通过。证据`.local/evidence/development/MF-01/progress582-criterion-curves.json`。


执行587–589补充当前契约：MinimumRMS（No Offset）按准则定义约束球面顶点不偏移，因此`summary.vertex_offset=0`、`vertex_offset_state=fixed_zero_by_criterion`；MinimumRMSWithOffset和反向MinimumVolume继续返回null。非MinimumVolume的去除统计标为`manufacturing_state=not_applicable`；反向MinimumVolume未取得的制造统计标为unavailable。`rows.removal_depth`在新增曲线中继续null，第二个series为deviation。

独立使用256点Gauss-Legendre圆盘面积权重与曲率最小化求解两种RMS准则，拟合半径与425原生曲线恢复半径通过5e-6mm门槛。带偏移准则的独立最优偏移约±0.00020837249mm作为待验证预测保存，生产结果保留null。最终587正负曲面两项原生通过，既有582七项回归证据沿用；589普通72通过。证据`.local/evidence/development/MF-01/progress589-offset-reference.json`。

2026-11-07 执行611–622：正式DSAG的Data9/10已接入两种RMS结果的`native_bfs_fit`，返回原生半径、原始`vertex_z_offset`、参数列身份及与四点SSAG球面重建的`curve_radius_check`。参数顺序为`[Surf,0,Data,Samp,Off-axis,Remove,BFS,0]`，当前Samp=1、Off-axis=0、Remove=2。半径对照绝对容差5e-6镜头单位；不一致时保留原值和失败标志。物理制造`summary.vertex_offset`沿用此前归属，原始DSAG值单列。

正负EvenAspheric在33/129两档采样的值一致；带偏移原始值分别−.0002083725005/+.0002083725027mm，与独立球面加法偏移符号相反。621以ZernikeFringeSag加入±.003mm已知piston，确认原始值还包含局部顶点基准。同形无piston的Zernike带偏移半径39.8400013026mm，与EvenAspheric39.8400396827mm相差3.8380e-5mm，超5e-6门槛；原生拟合的面型适用性仍待解释。反向DSAG BFS3只保留615直接诊断，当前DSAG手册列0–2，生产未据此新增反向合同。

普通620共75通过，真实stdio617正负两例通过；分页、PNG、保存重载、源曲面/solve/系统/MFE/MCE保持、六个原生参考分析关闭及断连通过。612六个专题结果探查、614元数据副本、615直接查询、621三个piston专题均关闭并断连。611结果头属性读取错误及613错位参数原记录保留，修正记录分别为612、614/615。完整MF/MA条目保持implemented，B0065/10。证据`.local/evidence/development/MF-01/progress622-dsag-fit.json`。

621保留文本进一步确认：默认SagTable/BFSD在piston+.003mm时仍报告制造偏移0、半径约39.46718mm；piston−.003mm时报告偏移−.003000003mm。DSAG BFS0保持半径约39.8401mm且偏移反向响应，两个出口在这些控制下采用不同基准/拟合合同。617带偏移deviation图已查看，轴、单位和图例清晰。


## 637–641证据同步（2026-11-07）

640普通45项、641正负原生2项通过；新增1001节点径向加权斜率摘要。继续制造偏移符号/基准、面型拟合适用性及反向制造摘要，保持implemented。

当前状态以[交接](../../../development/handoff.md)为准，历史计数属于对应执行记录。

斜率摘要返回`maximum_slope_difference`、`rms_slope_difference`、`slope_summary_source`。使用1000等长区间的1001个含端点SSLP节点，径向加权RMS为sqrt(sum(r*d²)/sum(r))；此来源与原生BFSD摘要分别标识。641十二项斜率摘要比较的最大绝对误差为1.6653345369377348e-15，门槛1e-6+1e-5×参考值。取消保留已完成采样。

2026-11-09等形面控制：R40/R80/Infinity三种基底和补偿二次项保持z=.0126r²，102个解析矢高通过。EvenAspheric带偏移RMS半径误差约5.5e-9mm；ZernikeFringeSag约3.84e-5mm，超原5e-6mm门槛。33至513五档DSAG采样没有改变半径或随后SSAG。能力查询已列出此受控范围，完整制造范围保持implemented；证据`development/evidence/MF-01/sag-fit-controls-20261109.md`。
