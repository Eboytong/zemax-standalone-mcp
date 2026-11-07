# 屈光力与有效焦距分布

run_analysis新增power_field_map、power_pupil_map，当前implemented；使用明确参数的正式POWF/POWP查询，非专题窗口设置。原生444已确认全部参数身份。当前配置与系统波长编号；surface必填并选最后有光焦度曲面。

共同参数：wavelength=1；data_type=Spherical，可选Cylinder/Maximum/Minimum/Tangential/Sagittal/Y/X/Astigmatic；quantity=Power或EFL；offset=0；x_points/y_points默认11，3–129。Field Map必填正的x_field_width/y_field_width，为物理视场总宽度；Pupil Map使用field=1，入口瞳[-1,1]网格且圆外为null。

Power单位diopters，EFL单位为当前镜头单位。Cylinder是原生极值差；Astigmatic是X−Y。EFL差值直接查询原生对应Data，不从屈光力差取倒数。Field Map默认按物理视场线性采样；`use_tangent_of_field_angle=true`时按tan(angle)均匀采样，限Angle视场且两轴总宽度均小于180度。显示轴是无量纲正切，`physical_field_x/y`保留实际角度；rows的`field_x/y`及原生参数保留对应角度和归一化视场。总宽度仍以度指定。全零归一化轴或超出当前归一化范围的视场宽度会拒绝。

结果grids[0].values[y][x]为端点采样；原始操作数参数、数值、参考光线逐点放入rows。valid_mask与区域分页一致。中央参考光线追迹失败或截断时显示null；原生环形光线的完整状态未公开，raw零值不会被推断为无效。非有限查询结果保留具体失败。offset由适配层加到原值。

446：真实stdio Cooke两种7×5网格、分页、PNG及曲面/系统/MFE保持通过，关闭正常。447：Paraxial焦距100mm四次轴上Power/EFL参考通过，预设abs1e-6+rel1e-6。474：单球面N-BK7界面的POWF和POWP均通过；用原生材料工具取得n=1.5168000345005883，以EFL=R*n/(n-1)、Power=1000/EFL建立参考。两种Map覆盖Power/EFL及Spherical/Maximum/Minimum/Tangential/Sagittal/X/Y/Cylinder/Astigmatic，共22项，最大绝对差1.934985890557074e-4，容差abs2e-4+rel2e-5。该参考是截至选择面的整个系统结果；早先10.336 D薄透镜假设未计入折射率，已作为诊断记录，不改变实现容差。该执行时尚缺离轴、柱面、切线采样与生命周期；本轮增量结果见下文。

原生默认专题文本和网格见probe442-b005；接口确认probe444-power。执行汇总见.local/evidence/development/CV-02/progress448-power.json。

2026-11-07 B006增量：Biconic单界面用独立主曲率参考`EFL_x/y=nR_x/y/(n−1)`检查两种Map。覆盖R_x/R_y=100/50、50/100、−100/−50 mm，以及X、Y、Astigmatic、Maximum、Minimum、Cylinder的Power和EFL，共72次数值检查通过，最大绝对差0.0001934985891409724，容差沿用`2e-4 + 2e-5×参考值`。曲面、设置保持；任务及会话结束。首轮测试误读复合任务的`close_attempted`键而失败，复合任务自身无该原生句柄，后续按任务终态、cleanup_warnings及子追迹所有者记录检查，原失败保留在native486-biconic.xml，通过记录为native487-biconic.xml。

切线采样5×3用例的61次数值/坐标检查、区域分页、PNG和模型设置保持通过，见native488-tangent.xml。采用平面Paraxial曲面核对采样身份与轴上10 D；此模型的离轴POWF返回极端数值，不用于证明离轴数值参考。轴对称瞳环、偏置、取消、重载和复用通过，见`.local/runs/power475_lifecycle_ec56c0e21f`。仍待完成：离轴球面/双轴系统的独立方向参考、单位切换及零/无穷状态，以及原生周边环光线有效性。原生未公开周边环半径、节点和逐光线状态，当前只声明中心参考光线检查；零值保留其原始身份。

2026-11-07 执行492：毫米/厘米物理等价系统的两种Map共12次数值检查通过。50mm界面Power=6.814355276657183 D、EFL=146.7490260488084 mm；5cm对应Power=6.814355276657184 D、EFL=14.674902604880838 cm。平面界面的Power与EFL原生均返回0.0；零EFL保留原始值，解释仍需正式定义。设置/曲面保持与断连通过，见`.local/evidence/development/CV-02/progress492-units-planar.json`。切线PNG已查看，坐标和单位显示正确，Paraxial离轴极值按原值呈现。

2026-11-07 离轴参考523–526：指定选中界面为stop，球面与Biconic的Rx/Ry=50/50、100/50、50/100 mm，以20度Y入射，用独立Coddington局部曲率 `Et=n*Ry*cos(r)^2/(n*cos(r)-cos(i))`、`Es=n*Rx/(n*cos(r)-cos(i))` 和Snell角度检查两种Map的子午/弧矢Power/EFL。523球面8项、524三组24项通过原容差 `2e-4+2e-5*参考值`。526进一步用轴上平面波、球面Px0/Py±0.5的实际局部入射几何核对非中心瞳点，8项通过，最大差0.0001947681。中心追迹只提供局部入射坐标，曲率参考独立计算。

522初始模型stop仍在像面，20度光线在选中面被截断，输出null；修正受控模型stop位置后523通过。525测试误把圆内rows当作完整矩形数组，526按grid_x/grid_y选点修复测试。两次失败证据保留，生产有效掩码未改。成功会话均检查曲面/设置保持并显式断连。证据CV-02/progress524-oblique.json、progress526-pupil-curvature.json；本轮普通525共107通过。仍需原生周边环逐光线状态和零EFL正式定义，当前两条implemented。

2026-11-07 执行593/596：已明确valid_mask_scope为中心参考光线通过且查询有限；native_ring_validity=unavailable。rows.native_query_status区分已查询有限值与中心光线无效时未执行查询，raw_value_state区分native_zero/finite_nonzero/not_queried。原生零值在加入offset后仍保留原值身份，zero_interpretation明确为未解释；grid增加native_zero_count和invalid_reference_ray_count。数值及掩码沿用原结果。

593用R50mm界面逐步将孔径缩至.1/.001/.00001mm，所测外围光线依次截断，中心Power/EFL始终有限且相同。原生差分环节点未公开，本实验未确定该环的截断状态。596原生八组平面/球面×两种Map×Power/EFL通过，含offset7、行和区域分页、任务终态、保存重载及源状态保持、子工具关闭和断连。595首次测试误用分页参数，失败及显式断连记录保留，596按start/count修正。最终普通597共71通过。两条完整功能继续implemented，周边环及零EFL正式语义仍待补齐。证据CV-02/progress593-aperture-ring.json、progress596-value-states.json。

执行634–636：两种Map在毫米/厘米等物理模型中共16分析通过。球面R50mm对应R5cm，N-BK7参考波长.5875618um；独立EFL=nR/(n−1)，Power=1000/EFL_mm。8次独立数值比较通过原物理容差：EFL绝对2e-4mm、Power绝对2e-4diopters，均加2e-5相对项。EFL输出随镜头单位缩放，Power保持diopters。平面控制保留原始零值与unresolved_native_zero_semantics，不将EFL0推断为无穷。

区域分页、4组模型保存重载、源曲面/solve/系统/MFE保持与任务/光线子工具关闭通过，会话已断连。普通636的Power/GRIN定向46通过，原生634为1通过。内部环节点/状态及零EFL正式含义仍缺，完整两条保留implemented。证据CV-02/progress636-unit-scaling.json。
