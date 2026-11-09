# 非序列路径与单光线专题


## 路径分析

path为现有ZRD或PAF绝对路径，复制到工作模型目录后UpdateFileLists，并核对AvailableRayDatabaseFiles。默认first_ray=1、last_ray=-1（全部剩余光线）、filter为空、relative_minimum_flux=0、sort_by=TotalEndingFlux、generate_path_filters=false。本机PAF分析仅支持全路径默认读取：first_ray=1、last_ray=-1、relative_minimum_flux=0、filter为空。非默认范围、阈值及追加filter在执行前拒绝；ZRD支持范围、筛选和阈值。公开NumberOfUniqueObjectsStruck映射本机枚举NumberOfUniqueObjectsStruct，按枚举值最终回读。

GeneratePathFilters会生成并保存_n命名筛选器；显式启用时先建立检查点并增加修订号。取消后保留检查点用于恢复。分析复用任务查询、取消及终态关闭。

通过IAR_PathAnalysisData/Entry返回总输入/输出功率（W）、光线/命中数、每路径对象编号和面序列、支路数、末对象/面、输出功率及其占总输入功率的百分比。rows为分类路径，uncategorized单独保留。Native PathObjectAndFaceList两个维度按原样保留；有序object.face采用原生PathSequence字符串，方形数组的方向不作猜测。rows支持get_task_result分页及报告表格。

2024 R2手册说明每序列最多100次对象交互、最多10000条唯一路径，低于相对阈值及超量部分进入uncategorized。结果保留原生头、消息与文本导出；文本失败保留有效结构化结果及原始导出错误。Paths长度和NumPaths、对象数组、读取上限、非有限值及重复编号均检查。NumPaths与Paths长度按原生分类条目核对；对象列表与面交互矩阵分别保留。

## 关键光线

critical_ray_trace接受CRS绝对路径并暂存工作副本，position_tolerance默认0.01镜头单位、angle_tolerance_deg默认0.01度，rays_to_display为AllRays/FailedRays/PassedRays，默认AllRays。显示初始/目标/实际位置和方向，原生标识、波长、终止对象及Pass逐光线保留。统计明确针对返回的显示范围。

采用IAS_CriticalRayTracer及IAR_CriticalRayData/Info。完整静态清单中存在专用设置接口，修正0.1.16文档的遗漏。原生CRT会临时插入目标探测器；Pass同时要求正确目标终止、位置及角度条件。按原生定义忽略错误，关闭偏振/分裂/散射；实际临时对象恢复由准备的原生用例核对。

## NSC单光线

nsc_single_ray_trace默认从(0,0,0)沿(0,0,1)发射，wavelength=1，reference_object=0表示NSC全局坐标。参考对象非零时输入采用该对象局部坐标；结构化命中输出为全局坐标。方向须为单位方向余弦，split_rays要求use_polarization=true；先启用偏振再写分裂，最终回读组合。

原生ReadSegmentFull参数名通过DLL反射确认，证据single-ray-signature027.json。返回段级parent/level、对象/面、状态、位置、方向、复电场、强度、物理路长、法线、折射率和探测器相位。max_segments默认及上限100000，超过时保留truncated及总数；原生ZRD存在时作为文件结果，可继续read_zrd分块。native_segment_index按本机实际接口从1开始。SaveRaysFile使用工作模型目录内文件名；native_database_file保留原生临时路径，artifacts优先返回实际生成的配置ZRD。




单光线直达坐标(0,0,10)、参考对象输入后的(.2,-.3,10)、方向、10mm路长和强度通过独立对照；偏振、截断、分页、保存重载及模型保持通过。关键光线CRS采用本机生成器确认的列顺序：位置、方向、强度、波长、视场、类型、目标位置及方向。两条光线分别通过及失败，AllRays/PassedRays/FailedRays均检查。原生专用数据返回全部行，适配器按请求筛选，native_data_scope保留原始统计。位置/方向容差1e-8+1e-7×参考值。两项运行中取消均cancelled、closed，后续分析成功。

路径直达1W及双源.25/.75W通过，功率最大误差3.36e-8W。PathObjectList对重复对象去重，NumberOfObjectsInPath及对象/面矩阵保留每次交互；分别保留native_object_list_length与native_object_face_shape。无未分类路径时uncategorized为null并保留原生消息。

N-BK7平板ZRD末端功率0.9167180210351944W在阈值0时可读；阈值1时分支被剔除，GetPathUncategorized仍报告无未分类路径，备用编号查询为空，文本也无相应功率行。历史失败和最终成功分别列于acceptance063.json。
