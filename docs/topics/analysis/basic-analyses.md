# AN-03 基础分析

四项功能通过run_analysis调用，返回任务编号；用get_task_status查询终态，get_task_result按start/count分页读取rows。请求示例见examples/requests/basic-analyses.json。

| kind | 参数 | 结果 |
| --- | --- | --- |
| single_ray_trace | wavelength=1，hx/hy/px/py=0，use_global=false，ray_type=DirectionCosines | 逐面真实/近轴光线、位置、方向数据、原始列与文本 |
| cardinal_points | wavelength=1，start_surface=1，end_surface默认像面前一面，orientation=both | YZ/XZ分别12类基点数据 |
| seidel_coefficients | wavelength=1 | 逐面及系统Seidel、横向、纵向和波前系数 |
| grid_distortion | 必填field_width；wavelength=1，reference_field=1，aspect=1，scale_factor=1，symmetric_magnification=true；grid_number可选 | 视场、预测像点、实际像点、畸变百分比及像面散点图 |

前三个文本专题使用原生分析，基点通过原生CARD操作数直接求值，保留computation_method=native_CARD_operand。CARD不插入或修改评价函数操作数。物方位置相对起始面，像方位置相对结束面；原生非有限值返回value=null及native_value和undefined状态。默认结束面可能是空白面，需要对指定镜片组求值时显式传入end_surface。

Single Ray Trace使用任意归一化光线，ray_type还可选择TangentAngle、YmUmYcUc。后者的坐标输入及全局选项按原生定义忽略；原生表头随结果保留。DirectionCosines中的方向是折射/反射后的方向，路径长度可为负。无限远物面及异常说明保留在原生文本中。

Seidel的coefficients保留原生名称；波前W系数以waves计，其余系数采用镜头单位。光阑、像面和累计行均保留row_label。applicability记录面型和偏心/倾斜条件，辅助判断三阶分析范围；具体面型仍需结合原生定义。默认波长1。

Grid Distortion的field_width为X方向总宽度，aspect为Y/X比。网格初始化采用原生Reset默认，可显式传入原生grid_number并回读。绘图表示像面预测与实际像点；原生窗口包含物方逆变换及显示缩放，二者坐标定义分别保留。畸变百分比保持原生符号。结果保存原生文本及尾部异常说明。

位置采用镜头单位，波长以编号选择。角度视场的网格数据用度表示。原生文本解析失败返回具体错误及文本文件路径。


全局光线坐标相对系统全局参考面；验证时显式将global_reference_surface设为1。对不同曲面范围的CARD结果比较，应先统一物方和像方位置参考面。
