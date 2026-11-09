# SagTable制造数据



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





在这些受控条件下，原生摘要对应1000个等长区间、1001个含两端的节点 `r_i=lo+i*(hi-lo)/1000`。RMS为 `sqrt(sum(r_i*d_i²)/sum(r_i))`，体积为 `2*pi*delta_r*sum(r_i*removal_depth_i)`。体积采用含端点矩形和；内边界项对环形区间不可省略。手册描述“1000等间距Y点”，本机观察到的离散节点定义另存于 `statistics_sampling.observed_reference`，其验证范围明确列出。请求的 `samples` 控制rows，与原生摘要采样独立。原生摘要数值继续原样返回。





`rotational_symmetry_check`保留三半径、八方位的原生GetSag检查；检测到非对称见证时返回UNSUPPORTED_MODEL。有限采样的通过范围写入结果。Biconic的Rx100/Ry50被拒绝，同会话改为Rx=Ry50后通过解析球面参考。

制造统计采用完整径向毛坯区间，偏心孔径作为实际设置返回。原生SSLP会将孔径外斜率置零；有孔径时在CopySystem副本中清除目标面孔径与拾取，并回读当前配置和孔径类型，再查询SSLP。每行同时返回有效`slope`、`slope_source`和`active_model_native_slope`，`slope_query_copy`记录副本身份与关闭结果。源模型GetSag和BFSD摘要继续使用活动系统。清除被拒绝时保留原生失败，关闭失败触发重连并保留原始错误。

native553首次偏心孔径用例暴露SSLP截断，原失败保留。修复后的native555通过；native557的13项定向回归通过，覆盖孔径、非对称拒绝、单位、配置、Composite、高阶统计、符号、分页、绘图及重载。native558在副本已打开、逐行采样时取消，确认关闭、源模型/solve/系统/MFE/MCE保持并可复用；1项通过。斜率与sag沿用1e-8+1e-6×参考值。




默认MinimumVolume沿用BFSD八项摘要。其他两准则及反向MinimumVolume使用正式SSAG的Remove=2、BFS=1/2/3，从四个原生坐标恢复球面，检查球面残差，再返回完整采样曲线与解析球面斜率。`native_query_arguments`保留每次参数及原值；`sphere_reconstruction.samples`保留原生GetSag/SSAG样本。采用原始SSLP曲面斜率，从恢复曲率解析计算球面斜率，避开425已记录的SSLP反向球面差异。




非MinimumVolume的去除统计标为`manufacturing_state=not_applicable`；反向MinimumVolume未取得的制造统计标为unavailable。`rows.removal_depth`在新增曲线中继续null，第二个series为deviation。



正负EvenAspheric在33/129两档采样的值一致；带偏移原始值分别−.0002083725005/+.0002083725027mm，与独立球面加法偏移符号相反。621以ZernikeFringeSag加入±.003mm已知piston，确认原始值还包含局部顶点基准。同形无piston的Zernike带偏移半径39.8400013026mm，与EvenAspheric39.8400396827mm相差3.8380e-5mm，超5e-6门槛；原生拟合的面型适用性仍待解释。反向DSAG BFS3只保留615直接诊断，当前DSAG手册列0–2，生产未据此新增反向合同。


621保留文本进一步确认：默认SagTable/BFSD在piston+.003mm时仍报告制造偏移0、半径约39.46718mm；piston−.003mm时报告偏移−.003000003mm。DSAG BFS0保持半径约39.8401mm且偏移反向响应，两个出口在这些控制下采用不同基准/拟合合同。617带偏移deviation图已查看，轴、单位和图例清晰。





斜率摘要返回`maximum_slope_difference`、`rms_slope_difference`、`slope_summary_source`。使用1000等长区间的1001个含端点SSLP节点，径向加权RMS为sqrt(sum(r*d²)/sum(r))；此来源与原生BFSD摘要分别标识。641十二项斜率摘要比较的最大绝对误差为1.6653345369377348e-15，门槛1e-6+1e-5×参考值。取消保留已完成采样。
