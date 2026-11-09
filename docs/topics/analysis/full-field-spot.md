# 全视场光斑

2026-11-09：当前配置通过原生选择器`Configuration=1`计算，物理配置编号保留在`task.settings.resolved_configuration`，两者分别记录。标准/ThroughFocus消费者的双配置真实stdio回归已通过。FullField本身的空出口及共同参考缺口继续按本页记录处理，见[配置修复证据](../../../development/evidence/CV-01/spot-current-configuration-20261109.md)。

`run_analysis.kind=full_field_spot` 已接入本机 `FullFieldSpot/AS_Spot` 的有类型请求、设置写入/回读、执行和关闭。支持视场/波长0表示全部、指定曲面、现有光斑采样/参考/显示参数、`plot_scale` 和正数 `exaggerate`；使用当前配置、DeltaFocus=0。公共参考点把各视场画在同一尺度；ChiefRay以视场1主光线为参考。

当前状态 implemented，结果出口待完成。Cooke下单色单场、多色全场、ChiefRay及三倍显示放大均执行，GetTextFile=false、SpotData=null、曲线/网格/散点计数均0。返回 RESULT_UNAVAILABLE，保留原生消息、设置、结果计数和文本导出失败；三个失败任务关闭、曲面保持，stdio断开成功。原生诊断用例通过表示上述限制可复现，光斑数值验收仍未通过。解除条件：取得正式图形/专用数据出口，或实现有来源标识且符合共同参考和放大定义的工作副本追迹路径。证据 .local/evidence/development/CV-01/acceptance074.json。


2026-11-07 执行529/533：本机手册确认所有视场共用参考，ChiefRay为field1；Centroid/Middle及Exaggerate坐标映射仍待正式定义。修正DirectionCosines模式的半径和参考坐标单位为dimensionless，增加coordinate_quantity；空间模式继续返回µm半径和镜头单位参考坐标。负半径与非有限值拒绝并保留原始行。普通533共54通过，其中新增收集器用例使用模拟SpotData；真实原生出口仍沿用074的空结果证据。详见CV-01/progress533-full-field.json。

2026-11-07 执行591/592：进一步检查正式RayData、RGB曲线和消息，Cooke的Centroid、ChiefRay三倍放大、Middle符号三组均为八类计数0，SpotData为空、文本导出false。设置已回读，三工具关闭，曲面/系统/MFE保持并断连。错误详情现保留八类完整计数。普通592共42通过；最终597受影响分析/状态71通过。结果可用性和数值验收继续待完成，证据CV-01/progress591-formal-outlets.json。
