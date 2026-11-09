

0.1.7保持现有请求入口，补齐类型专属参数检查、POP最终启用条件及应用后回读。孔径拒绝跨类型尺寸和偏心参数；重采样从属参数要求resample_after_refraction=true，显式手动采样要求auto_resample=false。

## 数值范围

- 孔径：直接光线逐点核对圆形、矩形、蜘蛛、用户孔径及遮挡，覆盖偏心、缩放；点均避开边界。
- Composite：同轴零间隔EvenAspheric Add-on与镜面Base，非零二次项累加；比较sag与独立解析法线反射方向。sag容差1e-8镜头单位+1e-7×参考值，方向绝对差1e-7。原生顺序反射余弦与物理方向使用相反符号，结果保留原生约定。
- 镜面：负厚度反射系统，Flat/Curved基底和隐藏设置导出原生PNG；人工查看确认可见变化，绘图修改前后光线结果一致。
- POP：0.1mm高斯束腰、0.55µm波长、100mm传播。手动256×256/宽2mm、512×512/宽3mm与自动1024×1024均比较功率及二阶矩束宽，功率绝对差与束宽相对差均为5e-4。输出网格坐标采用实际传播结果，记录与输入宽度分别保留。
- 预检查：散射设置构造后触发后续无效面号，确认模型内容和修订号保持原状态；属性保存重载检查配置和solve。

自动重采样256×256实测束宽0.20291556989154308mm，解析参考0.20161760352659483mm，相对差约0.00644，超过0.0005。1024×1024实测0.2016672338260417mm，相对差约0.000246，满足同一容差。前次失败和高采样结果分别记录。

## 项目资源保持

项目模型的SaveAs会改变资源查找根目录。工作副本迁移前复制标准项目资源目录；检查点留在当前项目目录，避免使活动ABGF选择丢失。项目另存到新目录时先带入资源；目标已有同名资源目录则返回OUTPUT_EXISTS，保留现有内容。复制错误保留源、目标和原始原因。

本批原生样例验证ABGF文件在工作副本、检查点及保存重载中的持续采用。资源型模型交接须保留对应项目资源目录。

## 原生限制

- User：CreateScatteringTypeSettings抛出UILDEScatterData序列化异常。返回UNSUPPORTED_SETTING，details保留capability、stage及native_error；其他异常保持原始错误分类。
- ISScatterCatalog：本机有目录索引，但搜索未找到实际ISX数据文件，原生列表只有空选项。待提供有效ISX及匹配目录记录后验收。
- FloatingAperture至None：本机ChangeApertureTypeSettings可返回成功而类型仍为FloatingAperture，适配层返回SETTING_REJECTED，外层为PARTIAL_UPDATE，保留检查点。

FRU__delta_init诊断继续记录。散射验收包括设置、资源采用与几何追迹冒烟；散射角分布的统计物理验收另列专题。


ABGF格式和资源位置参考[2024 R2官方散射模型说明](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Available_Scatter_Models.html)。
