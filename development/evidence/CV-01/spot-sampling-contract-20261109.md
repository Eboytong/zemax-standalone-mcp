# D004 光斑逐光线采样正式合同补查

2026-11-09；CV-01.FullFieldSpot、CV-01.MatrixSpot、CV-01.ConfigurationMatrixSpot。源码0.1.62；本机OpticStudio24.2公开接口程序集。目标为确认既有空结果之外，是否存在完整标准光斑采样与逐光线数据出口，决定正式替代路径的可实现范围。

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/CV-01/spot_sampling_contract.py .local/evidence/development/CV-01/spot-sampling-contract-20261109`。已执行、exit0；原始成员保存在该目录`contracts.json`。探查仅加载正式程序集，`application_created=false`，没有创建或连接应用实例，没有任务或模型修改。

正式成员结果：`IComputeRMSSpotSize`提供GaussianQuad/RectArray方法、rings/arms、GridSampling、DeleteVignetted、IgnoreLateralColor和配置/视场半径统计，未提供逐光线坐标。`IBatchRayTrace`提供归一化/直接、偏振/非偏振追迹，所列公开签名没有标准光斑采样网格和顺序ScatterRays控制。`IAR_SpotDataResultMatrix`按视场/波长返回15项坐标和统计，未见逐光线索引；`IAR_RayData`有Rays/GetRay，但已有矩阵专题执行时RayData集合为空。IAS_Spot有采样与显示设置，没有采样点枚举出口。

原生标准光斑定义中的Square/Hexapolar/Dithered、波长权重采样、apodization、scatter、共同/独立参考点及Airy显示均属于原范围。仅拼接RMS统计或自行构造未验证的瞳网格不足以覆盖完整声明，当前状态保持implemented，不增加完整计数。此前六个原生任务的设置、空出口、恢复和关闭沿用[创建方式对照](spot-factory-outlets-20261109.md)，本次未重复执行。

解除条件：取得有效矩阵逐光线/图形出口，或取得能够覆盖上述全部采样、参考点和散射选项的正式等价路径；FullField另需共同参考与Exaggerate的坐标定义。取得新依据后运行分面数值和生命周期验收。本轮继续D005至D009可执行项。
