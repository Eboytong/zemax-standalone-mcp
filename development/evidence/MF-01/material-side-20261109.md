# D008 SagTable材料侧、去除方向与光阑斜率副本

2026-11-09，MF-01.SagTable与MA-01.SagTable共同范围；源码0.1.62工作树，Python3.14，OpticStudio24.2.0/build240529/PremiumEdition，Sequential/Millimeters。原生串行，COMPLUS_LoadFromRemoteSources=1，项目src导入。

## 计划、依据与输入

本机2024R2手册1307—1309页：MinimumVolume根据材料侧选择毛坯，ReverseDirection改选另一侧；其他两种RMS准则允许/固定顶点偏移。DSAG Data10在1086—1087页定义为局部坐标中的BFS顶点Z偏移，所列BFS为0/1/2。SSAG的BFS3正式提供反向最小体积曲线。本轮不将未文档化的DSAG3接入产品。

控制假设：保持几何不变，仅切换目标面前后N-BK7/空气，可区分BFSD制造偏移是否含材料侧，以及其能否直接由DSAG局部偏移替代。四模型为正/负`z=±.0126r²`（R=±40、conic=-1、二次项±.0001、半口径5），目标曲面2；前一面1厚5，目标厚20。分别设置前面N-BK7/目标空气与前面空气/目标N-BK7。每模型读取8项BFSD和SSAG四种准则；DSAG仅正式0/1/2。实际设置、原生参数、上下文及回执保存。

控制命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/MF-01/sag_vertex_conventions.py .local/evidence/development/MF-01/vertex-conventions-20261109`；exit0，无error。四模型系统/曲面/评价函数均保持，最终shutdown回执native.closed=true、forced=false、error=null，无活动原生实例。原始probe.json和state/close_receipt.json保留。直接操作数查询未创建分析工具或任务。

## 控制结果与实现修复

| 几何符号 | 材料侧 | BFSD半径mm | BFSD顶点偏移mm | 逐行去除方向 |
| --- | --- | ---: | ---: | ---: |
| 正 | 空气入玻璃 | 39.84003968253968 | 0 | +1 |
| 正 | 玻璃出空气 | 39.83997689339438 | .00031230931139912093 | -1 |
| 负 | 空气入玻璃 | -39.83997689339438 | -.0003123093113991211 | +1 |
| 负 | 玻璃出空气 | -39.84003968253968 | 0 | -1 |

DSAG/SSAG的同一几何结果在材料侧改变时保持，而BFSD半径、偏移和去除摘要发生上表变化，因此不能直接把DSAG偏移替换BFSD制造偏移。RMS/反向准则原来的偏移缺口保留。

实际产品错误：旧去除行固定为`sag-sphere_sag-BFSD_offset`，出玻璃面的数值为负。修复保持原局部坐标和BFSD原值，新增signed_vertex_deviation；由已有三个径向GetSag见证与原生毛坯球/偏移确定direction，再返回direction乘有符号偏差。制造方向、见证、公式和容差附在manufacturing_direction。见证在毛坯两侧均有超容差数据或后续行穿过毛坯时返回INVALID_RESULT_DATA并保留数据。方向判断容差沿用行数据1e-8+1e-6×最大去除深度；原半径、统计容差均保持。

首轮真实stdio发现光阑面清除孔径为None后，原生自动恢复FloatingAperture；斜率副本回读拒绝。改为显式CircularAperture的第二轮仍复现，两个失败XML和原始目录sag_material_side_c051442393/ddd8c5edc9保留。副本均已关闭。修复限定在任务自有副本：None恢复Floating时，采用内径0、偏心0、外半径大于完整查询区间的同心圆，回读类型及全部四值；失败保持拒绝。所有GetSag/BFSD和源模型孔径保持原来源。该路径以unclipped_method及actual_copy_circle记录。

## 定向检查与数值参考

普通命令：`.venv/Scripts/python.exe -B -X utf8 -m pytest tests/unit/test_sag_table.py tests/unit/test_sag_fit.py tests/unit/test_sag_removal_direction.py tests/unit/test_contracts.py tests/unit/test_task_artifact_metadata.py tests/unit/test_development_status_report.py -q --junitxml=.local/evidence/development/MF-01/material-side-unit-final-20261109.xml`；108 passed/1.23s。

覆盖正负方向、零深度、毛坯交叉、非有限见证、行符号、包围圆采用/拒绝/错误回读、取消关闭，以及现有准则/参数/错误/部分行和关闭失败测试。公开请求schema保持，结果新增方向和原始有符号偏差，能力说明和专题文档已同步。

首轮修复后原生命令选`tests/native/test_sag_material_side_live.py`；material-side-native-r3-20261109.xml为1 passed/17.77s。四组合148项数值对照全通过，最大绝对误差5.759281940243e-16。原始`.local/runs/runs/sag_material_side_de2209c9a2/`保留。解析面为±.0126r²，球面按原生曲率解析计算；去除量按真实材料侧确定正负方向，行门槛1e-8+1e-6×参考值。原生BFSD最大/RMS/体积独立使用1001含端点径向节点复算，统计门槛1e-6+1e-5×参考值、体积绝对门槛1e-5。

最终追加实际取消、重载、复用及受影响孔径回归，命令与结果见下续记。查询复合任务没有独立分析工具句柄；自有斜率系统关闭以slope_query_copy.closed回读，应用关闭以实际disconnect及stdio进程退出记录。无需重连的成功与取消后复用分别检查。

最终命令：`.venv/Scripts/python.exe -B -X utf8 -m pytest tests/native/test_sag_material_side_live.py tests/native/test_sag_table_live.py::test_sag_table_parabola_reference tests/native/test_sag_table_applicability_live.py -q --run-zemax --junitxml=.local/evidence/development/MF-01/material-side-native-final-20261109.xml`；5 passed/64.98s。覆盖四材料侧、既有抛物面解析、非对称拒绝后复用、偏心孔径完整毛坯和实际副本取消关闭。最终材料侧原始目录`.local/runs/runs/sag_material_side_4d30cc8d77/`，148项数值对照最大误差仍5.759281940243e-16。保存重载rows/summary一致；在包围圆斜率副本已打开且sampling_rows阶段取消，任务cancelled、copy.closed=true；随后复用成功。最后disconnect.connected=false、warnings=[]、requires_reconnect=false；五用例串行进程均终态退出，无活动原生会话。

## 状态与下一步

本轮修复两个现有实现缺陷。SagTable完整范围仍为implemented：RMS带偏移的制造基准、反向制造摘要、Zernike与独立RMS拟合半径约3.84e-5mm超原5e-6mm门槛保留。四材料侧结果进一步排除了DSAG偏移直接替代BFSD的路径；取得新依据后再处理相应范围。完整累计7/10，89组剩余。继续D009正式格式/层号及前序条目新依据，已确认同条件空出口不重复运行。
