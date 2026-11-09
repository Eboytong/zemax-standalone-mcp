# 偏振瞳图

`run_analysis` 新增 `kind="polarization_pupil_map"`。本机 OpticStudio 2024 R2 通过正式 `IAS_.SaveTo/ModifySettings/LoadFrom` 配置 `PPM_*` 键，执行原生 PolarizationPupilMap，并解析其 UTF-16 原生文本。专题运行时为 `AS_Default`，原生曲线和网格数量均为零。

请求必填曲面 `surface`；`field=1`、`wavelength=1`，均为从 1 开始编号。`sampling=5` 表示瞳直径上 5 点，支持 3 至 101 的奇数；原生配置值为 `(sampling-3)/2`。每次执行通过有效瞳点间隔核实密度，有效点不足时返回 `SETTING_UNCONFIRMED`。`jx=1`、`jy=0`，两个非负振幅不得同时为零；`x_phase=0`、`y_phase=0` 使用度，回读按 360 度周期比较。

分析使用当前配置，Add/Sub 配置列表显式设为 0。执行后从原生文本核对曲面、配置、波长、Jones 振幅、相位和视场坐标，保留显示精度。文本提供单个 Y 位置或 X/Y 两个分量，返回 `field_position={x,y}` 和系统 `field_type`。相同坐标对应多个视场时不能从原生文本唯一确认编号，返回具体条件错误。

结果 `rows` 提供 `px/py/ex/ey/intensity/relative_phase_deg/orientation_deg`，支持既有 `start/count` 分页。瞳坐标归一化；Ex/Ey 为原生电场振幅；强度采用原生横向定义 `abs(Ex)^2+abs(Ey)^2`，批量偏振光线的总强度还包含 Ez。相位为原生 Ex/Ey 相对相位；单分量为零或圆偏振时，相位或方向角有退化条件。原生透射百分比、消息、实际设置、CFG 和原始文本保留。强度散点可通过 `export_analysis_image` 绘制。

原生验收覆盖 3、5、7、9、101 点、X/Y 线偏振和椭圆/圆偏振、两种波长、轴上/Y 离轴/斜向/负视场及配置 2。Ex/Ey、横向强度与独立批量偏振光线参考逐点比较，容差 `1e-8+1e-7×参考值`；相位模 360 度误差容差 `1e-6°`；中心强度另用本机 N-BK7 Sellmeier 系数及 Fresnel 公式比较。原生关闭、模型状态、分页及图像导出已执行；历史报告子进程曾超过同步 45 秒时限，保留 `REPORT_TIMEOUT` 记录。独立标准输入及工作目录调整后，配置 2、负视场、450° 相位的小采样报告通过；报告散点 PNG 已纳入验收。101 点采样完成全部逐点数值和模型状态检查，其完整报告没有在修复后复跑。

证据：`.local/evidence/development/PO-01/native-acceptance054.json`、`native054-final3.xml`；首次强度参考定义和双分量视场解析失败记录分别保留。其余四项偏振专题仍按逐项台账继续探查。调用示例见 `examples/requests/polarization_pupil054_requests.json`。

最终独立安装包证据：`.local/evidence/development/PO-01/acceptance054/summary.json`。6 组请求共 31,767 次数值比较，振幅/强度最大绝对误差低于 `5e-10`，相位最大误差低于 `5e-8°`，中心 Fresnel 误差约 `4.06e-10`。原生文本、CFG、调用回执和图像副本已保存。
