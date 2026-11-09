# 屈光力与有效焦距分布

run_analysis新增power_field_map、power_pupil_map，当前implemented；使用明确参数的正式POWF/POWP查询，非专题窗口设置。原生444已确认全部参数身份。当前配置与系统波长编号；surface必填并选最后有光焦度曲面。

共同参数：wavelength=1；data_type=Spherical，可选Cylinder/Maximum/Minimum/Tangential/Sagittal/Y/X/Astigmatic；quantity=Power或EFL；offset=0；x_points/y_points默认11，3–129。Field Map必填正的x_field_width/y_field_width，为物理视场总宽度；Pupil Map使用field=1，入口瞳[-1,1]网格且圆外为null。

Power单位diopters，EFL单位为当前镜头单位。Cylinder是原生极值差；Astigmatic是X−Y。EFL差值直接查询原生对应Data，不从屈光力差取倒数。Field Map默认按物理视场线性采样；`use_tangent_of_field_angle=true`时按tan(angle)均匀采样，限Angle视场且两轴总宽度均小于180度。显示轴是无量纲正切，`physical_field_x/y`保留实际角度；rows的`field_x/y`及原生参数保留对应角度和归一化视场。总宽度仍以度指定。全零归一化轴或超出当前归一化范围的视场宽度会拒绝。

结果grids[0].values[y][x]为端点采样；原始操作数参数、数值、参考光线逐点放入rows。valid_mask与区域分页一致。中央参考光线追迹失败或截断时显示null；原生环形光线的完整状态未公开，raw零值不会被推断为无效。非有限查询结果保留具体失败。offset由适配层加到原值。




切线采样5×3用例的61次数值/坐标检查、区域分页、PNG和模型设置保持通过，见native488-tangent.xml。采用平面Paraxial曲面核对采样身份与轴上10 D；此模型的离轴POWF返回极端数值，不用于证明离轴数值参考。仍待完成：离轴球面/双轴系统的独立方向参考、单位切换及零/无穷状态，以及原生周边环光线有效性。原生未公开周边环半径、节点和逐光线状态，当前只声明中心参考光线检查；零值保留其原始身份。






球面R50mm对应R5cm，N-BK7参考波长.5875618um；独立EFL=nR/(n−1)，Power=1000/EFL_mm。8次独立数值比较通过原物理容差：EFL绝对2e-4mm、Power绝对2e-4diopters，均加2e-5相对项。EFL输出随镜头单位缩放，Power保持diopters。平面控制保留原始零值与unresolved_native_zero_semantics，不将EFL0推断为无穷。
