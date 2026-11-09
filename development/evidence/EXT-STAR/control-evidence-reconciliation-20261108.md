# STAR 控制接口与证据日期对账

2026-11-08为已保存资料和当前适配器的静态复核日期。本记录未启动新的STAR原生会话。readiness193的模块、材料数值及关闭数据采集于2026-11-06；probe037/038为2026-11-05接口材料。

STAR控制使用曲面STARData和系统STARSubsystem成员，正式接口已经存在。不能将专题分析工厂缺失套用于这些控制。

| 工作 | 正式对象 | 实际剩余条件 |
| --- | --- | --- |
| 组件、成员、RBM、坐标断点 | ISTAR_ComponentRBMs | 启用模块后，用受控FEA验证设置、拓扑、持久性和恢复。 |
| 形变导入、拟合、卸载 | ISTAR_Deformations、ISTAR_DeformationFits | 启用模块及受控形变输入，比较独立变形/法线参考。 |
| 温度导入、拟合、卸载及热控 | ISTAR_Temperatures、ISTAR_TemperaturesFits | 启用模块及温度/材料参考，验证插值和热参数。 |
| 直接折射率导入、拟合、卸载 | ISTAR_DirectIndex、ISTAR_DirectIndexFits | 启用模块及已知折射率FEA参考。 |
| 坐标、刚体 | ISTAR_CoordinateTransform、ISTAR_RBMs | 启用模块，验证独立矩阵、坐标基底与持久性。 |
| 读取、体积控制 | ISTAR_Data及其温度/直接折射率成员 | 启用模块及受控FEA，验证实际读取和控制采用。 |
| 更新模式 | ISTARSubsystem.UpdateMode | 启用模块，验证枚举采用、计算和重载。 |
| 材料折射率、dn/dT | ISTARMaterials | 历史GetRefractiveIndex/GetDNDT在明确材料及条件下返回0。需要有效正折射率输出及独立热光参考；仅有接口存在尚未完成数值验收。 |

依据：`development/evidence/EXT-STAR/probe037.json`、`probe038.json`、`readiness193.json`；当前实现`src/zemax_mcp/star_controls.py`、STAR读写适配及有类型请求。历史记录`IsSTARModuleEnabled=false`，无受控FEA实例；现阶段继续blocked。取得许可/输入后按原条目逐项验收，保留原有数值门槛。本次修正文案和日期，不增加批次完成数。
