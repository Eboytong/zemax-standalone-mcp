# NSC 对象几何与探测器区域数据（0.1.19）

## 对象面几何

get_nsc_object_geometry读取一个对象的原生IFaceData；先通过update_nsc_objects显式设置type_settings.ObjectIsADetector=true。混合模式通过nsc_surface选择NSC组。object为对象编号，start为零基CurrentFace编号，count默认100且最大1000，frame为local/global，默认local。响应包含顶点、顶点法线、三角面积（适用时）、几何单位、可选面辐射数据以及next_start。

每页顶点上限100000，单面上限10000。原生面分割密度随对象及OpticStudio网格条件变化，代表三角面序列化，不代表解析CAD曲面或唯一几何拓扑。非三角面保留全部顶点及法线，不推算面积。请求include_radiometry时返回原生Flux/Irradiance/AbsorbedFlux/AbsorbedIrradiance及源/分析单位设置。

IFaceData由对象借用，不单独Close。读取期间设置ConvertToGlobal及CurrentFace，完成、失败均恢复原值并回读；恢复失败要求断开重连，返回恢复错误和原始读取错误。结果带模型修订/配置。2026-11-05完成长方体、偏心且Y倾斜30度的自建STL顶点/法线/面积、分页、保存重载与源保持验收，容差1e-8+1e-7×参考值。吸收长方体的面功率和吸收功率分别与独立1W输入一致。

本机ConvertToGlobal=true的GetVertexNormal带入对象平移量。vertex_normals采用对象旋转矩阵乘局部法线；native_vertex_normals保留原生全局返回值，normal_source记录计算来源。最大方向分量误差1.11e-16。局部法线直接来自原生接口。读取不隐式修改ObjectIsADetector。

## 大型探测器小区域

get_detector_data增加read_mode，full沿用既有读取；region只按NCE.GetDetectorData逐像素读取Rectangle/Volume请求区域，不创建完整探测器矩阵。Rectangle支持flux/irradiance/intensity且要求空间DataType=0；Volume支持flux/absorbed_flux/absorbed_density。最大单次100000个样本，宽高深原生总维度可超过此值但必须符合Int32一基像素索引。

请求坐标和页范围使用零基X/Y/Z；原生pixel编号为`1+x+nx*(y+ny*z)`。返回值为values[y][x]或values[z][y][x]，带区域轴中心/边界、next_x/y/z、非有限值计数、来源追迹历史和JSON区域文件。total_flux固定null；region_sum只代表所请求区域，incident volume flux沿路径在不同体素重复，不等于独立总能量。文件完整记录只包含请求区域及artifacts。

原生检查已覆盖矩形flux/irradiance/intensity及体积flux/absorbed_flux/absorbed_density与全量切片一致、独立点光线占用像素1W、保存重载及模型保持，并访问128^3体积中的单个角点像素。普通检查覆盖边界、单位/类型、快速索引、部分和、非有限值及大尺寸安全路径。

NS-04的Rectangle/Polar/Color/Volume/Surface全量读取及文件保存/加载沿用docs/nonsequential-validation.md和现有源测试。对象查看器继续按台账探查；Sag专题见nsc-surface-sag.md。

接口证据：verification/development/NS-04/probe029.json；示例examples/nsc029_requests.json；历史汇总verification/nsc-object-data029-summary.json。本轮154项相关普通检查及原生证据见verification/development/NS-04/acceptance065.json。
