# NSC 对象几何与探测器区域数据

## 对象面几何

get_nsc_object_geometry读取一个对象的原生IFaceData；先通过update_nsc_objects显式设置type_settings.ObjectIsADetector=true。混合模式通过nsc_surface选择NSC组。object为对象编号，start为零基CurrentFace编号，count默认100且最大1000，frame为local/global，默认local。响应包含顶点、顶点法线、三角面积（适用时）、几何单位、可选面辐射数据以及next_start。

每页顶点上限100000，单面上限10000。原生面分割密度随对象及OpticStudio网格条件变化，代表三角面序列化，不代表解析CAD曲面或唯一几何拓扑。非三角面保留全部顶点及法线，不推算面积。请求include_radiometry时返回原生Flux/Irradiance/AbsorbedFlux/AbsorbedIrradiance及源/分析单位设置。


本机ConvertToGlobal=true的GetVertexNormal带入对象平移量。vertex_normals采用对象旋转矩阵乘局部法线；native_vertex_normals保留原生全局返回值，normal_source记录计算来源。最大方向分量误差1.11e-16。局部法线直接来自原生接口。读取不隐式修改ObjectIsADetector。

## 大型探测器小区域

get_detector_data增加read_mode，full沿用既有读取；region只按NCE.GetDetectorData逐像素读取Rectangle/Volume请求区域，不创建完整探测器矩阵。Rectangle支持flux/irradiance/intensity且要求空间DataType=0；Volume支持flux/absorbed_flux/absorbed_density。最大单次100000个样本，宽高深原生总维度可超过此值但必须符合Int32一基像素索引。

请求坐标和页范围使用零基X/Y/Z；原生pixel编号为`1+x+nx*(y+ny*z)`。返回值为values[y][x]或values[z][y][x]，带区域轴中心/边界、next_x/y/z、非有限值计数、来源追迹历史和JSON区域文件。total_flux固定null；region_sum只代表所请求区域，incident volume flux沿路径在不同体素重复，不等于独立总能量。文件完整记录只包含请求区域及artifacts。

原生检查已覆盖矩形flux/irradiance/intensity及体积flux/absorbed_flux/absorbed_density与全量切片一致、独立点光线占用像素1W、保存重载及模型保持，并访问128^3体积中的单个角点像素。普通检查覆盖边界、单位/类型、快速索引、部分和、非有限值及大尺寸安全路径。

Rectangle、Polar、Color、Volume 和 Surface 探测器的数据读取及文件保存/加载见[非序列数据](nonsequential-validation.md)。
