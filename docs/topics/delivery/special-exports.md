# 特殊格式与正式导出

## 0.1.46 CAD 配置编码修复及原生复测

本机双配置探查确认：SetCurrentConfiguration 的 Configuration 回读为 0；SetSingleConfiguration(1/2) 回读为 1/2，模型当前配置保持 1。当前配置的最终状态检查改为核对原生编码 0；结果增加 configuration_selection，记录 current/single、解析后的配置编号及原生编码。公开请求和 schema 保持原有字段。

STEP/STL/SAT 扩展设置通过实际采用、文件生成、工具关闭及系统设置保持检查，独立安装 0.1.46 wheel 后再次通过。初次三项 SETTING_REJECTED 失败与修复后结果分别保留。文件几何的独立数值比较、NSC 专用选项及多配置输出规则继续待验收，EXT-EXPORT.CadSettings 保持 implemented。

证据：.local/evidence/development/EXT-EXPORT/cad-configuration046.json、cad-settings046.xml；安装包及逐调用记录见 .local/evidence/development/BASE-04/release046.json、reboot046.json。

## 曲面点云

`export_point_cloud` 调用本机LDE的 `CanExportPointCloud` / `RunTool_ExportPointCloudFile`，在独立系统副本中同步导出PCD并关闭副本。方法参数没有原生设置getter；输出头中的DATA与法线字段核对格式和法线选项，采样采用及物理坐标待原生受控模型对照。

```json
{"request":{"surface":1,"path":"C:\\ZemaxOutput\\surface.pcd","x_sampling":21,"y_sampling":15,"include_surface_normals":true,"format":"ASCII"}}
```

曲面编号从0开始，必须在当前顺序系统范围内，且CanExportPointCloud为true。采样每轴2至4096，单次乘积预算1048576点；该预算为服务资源限制。format为 `ASCII/Binary/CompressedBinary`，覆盖文件需overwrite=true。返回原生消息、PCD头、点数、字段、数据格式、镜头单位和完整文件路径；二进制及压缩负载按原生文件保留。坐标为所选曲面局部坐标，采用当前镜头单位；网格按Y行排列、X变化最快。采样点位于像元中心，孔径外的sag和法线保留原生NaN。输出WIDTH/HEIGHT、DATA和法线字段均核对请求。

该LDE方法同步返回IMessage，创建零个SystemTool，缺少原生取消接口。副本在成功和失败均关闭；失败关闭时保留原始错误并要求重连。空点云、无输出、原生消息错误和头格式错误分别返回。手册第48–49页标明需Premium或Enterprise，实际许可仍由CanExportPointCloud及执行结果确认。

## 黑盒、加密与旧线框

本机2024 R2公开接口908个类型已扫描，记录 `.local/evidence/development/EXT-EXPORT/public-types042.json`。`IOpticalSystemTools`提供CAD、布局和Speos导出，LDE提供点云；未发现ZBB创建、ZEC加密镀膜和旧DXF/IGES线框的命名导出工厂。IAPIUtilities只有格式转换，IFileManager处理项目文件依赖；ISurfaceBlackBoxLens用于选择已有ZBB。

本机手册第51–55页描述界面创建ZBB及ZEC；第49–51页描述旧线框出口。已将三项分别登记blocked。解除条件为取得本机版本可执行的正式创建接口或受支持自动化协议、参数和许可说明，然后补充有类型请求、原生文件与重载/追迹对照。界面功能存在的记录与MCP正式接口能力分别保留。

CAD的现有格式继续使用run_cad_export，Speos使用run_speos_export；项目归档沿用现有项目/归档工具。当前点云为implemented；设置实际采用、坐标/法线数值、保存重载和原生副本关闭待BASE-04启动恢复后运行 `tests/test_point_cloud.py -m zemax`。平面z与法线参考采用绝对容差1e-8、相对容差1e-7；其他面型及压缩负载数值解码仍为后续原生验收。

## 0.1.44 CAD 设置与结果

`run_cad_export` 新增13个可选设置。省略或传null沿用新建原生工具的对应值；既有字段继续按请求设置。类型、枚举及活动条件来自本机2024 R2公开IExportCAD与手册46–47页，记录见 `.local/evidence/development/EXT-EXPORT/cad-settings044.json`。

| 字段 | 值与条件 |
| --- | --- |
| ray_pattern | XYFan / XFan / YFan / Ring / List / Random / Grid / SolidRing；SolidRing要求顺序模式、至少8条光线；还需原生边缘光线可追迹且无焦散 |
| delete_vignetted | 是否删除渐晕光线 |
| ray_layer / lens_layer | 原生非负整数图层编号 |
| dummy_thickness | 有限非负数，当前镜头单位；要求export_dummy_surfaces与surfaces_as_solids均开启 |
| spline_segments | N_016 / N_032 / N_064 / N_128 / N_256 / N_512 |
| angular_tolerance | Low / Medium / High / Presentation；要求STL |
| scatter_nsc_rays / split_nsc_rays / use_polarization | NSC源光线的散射、分裂及偏振选项；实际物理效果待原生用例 |
| auto_name_faces | 原生自动命名面开关 |
| file_version | Current / V25–V30，原生ACISExportVersion；限ACIS格式。SAT/SAB读取实际文件头，显式版本未采用时返回SETTING_REJECTED |
| configuration | 正整数配置编号，缺省使用当前配置；通过SetSingleConfiguration选择导出配置，保持模型当前配置 |

VisualizationJSON请求拒绝这些CAD专用选项。STL不导出光线；图层与样条参数的文件效果取决于格式。多配置AllByFile/AllByLayer/AllAtOnce留待确认原生Configuration编码及输出文件规则后接入。

```json
{"request":{"path":"C:/ZemaxOutput/lens.stl","format":"STL","start":1,"end":2,"configuration":1,"export_dummy_surfaces":true,"dummy_thickness":0.1,"angular_tolerance":"High"}}
```

写入全部设置后核对最终标量与枚举值，拒绝静默忽略；结果保留`settings.requested`、`checked_fields`和原生标量设置。成功收集时先确认工具Close，再检查输出路径存在。设置失败与关闭失败同时发生时，保留原始错误及cleanup_error；原生计算失败、关闭失败及无结果文件分别归属CAD_EXPORT_FAILED、CLEANUP_FAILED、NO_RESULT_DATA。

45项定向测试通过。三项格式设置原生用例已准备，实际采用、几何文件内容、配置保持与原生关闭待BASE-04恢复启动后执行；历史CAD结果沿用原有证据范围。


## CAD 多配置调用与当前验收

`run_cad_export.configuration_mode`提供`current/single/all_by_file/all_by_layer/all_at_once`。省略时沿用既有行为：提供configuration则导出单配置，否则当前配置；显式single须提供configuration，其余模式与该编号互斥。配置编码最终回读为current=0、single=配置编号、AllByFile=n+1、AllByLayer=n+2、AllAtOnce=n+3，n为模型配置总数。导出保持模型活动配置及MCE内容。

```json
{"request":{"path":"C:/ZemaxOutput/design.step","format":"STEP","configuration_mode":"all_by_file","end":2}}
```

逐文件模式创建独立`design_configs_<id>`目录，返回目录path、全部paths及`configurations`编号/路径映射，逐项作为CAD artifact；原生基名增加`_config0001`等后缀。STEP采用原生`.stp`后缀、IGES采用`.igs`。原生写入完成并关闭后才读取文件集合，配置缺失返回NO_RESULT_DATA并保留输出位置。其他模式继续返回单文件path。

本机2/3配置探查及STEP/STL/IGES/SAT逐文件出口通过。双配置受控圆柱厚度2/4mm，当前、指定、两种集合及逐文件六次体积与πr²t比较通过，绝对容差1e-5mm³+1e-6×参考值，最大误差约3.77e-8mm³；保存重载、模型/配置/solve保持与关闭通过。初始OCP默认非自适应积分偏差0.0660764mm³，采用误差目标1e-10的自适应积分后通过，原容差保持。

层级仍待验收：原生IGES的LensLayer=10/RayLayer=20回读采用，但AllByLayer及AllAtOnce的目录层号未呈现预期10/11，观察到65535。STEP也未发现PRESENTATION_LAYER_ASSIGNMENT实体。EXT-EXPORT.CadMultipleConfigurations保留implemented；后续需确认原生导出器对分层的支持及可保持模型的正式修复路径。证据见`.local/evidence/development/EXT-EXPORT/progress175.json`；历史失败native169/170/174保留。相关普通56通过，native172的多配置数值和既有STEP/STL/SAT设置回归4通过。


## 点云受控参考

倾斜和平移CoordinateBreak后的半径20球面、半口径5，7×5网格分别以ASCII/Binary/CompressedBinary、有/无法线导出；同时覆盖毫米和厘米单位。独立读取PCD标准负载及LZF压缩，逐点与球面sag、解析法线及像元中心比较；源模型在保存重载后建立基线，导出保持系统、曲面及solve，副本关闭。平面法线为(0,0,-1)，球面法线为(x/20,y/20,-sqrt(400-x²-y²)/20)，均为本轮受控正厚度模型的原生方向。

首次平面检查把孔径外NaN当作有限点而失败，原始native175记录保留；改为按独立孔径判定有效掩码，有限点仍沿用1e-8+1e-7×参考值容差。所有编码的7×5网格与法线开关采用均检查；最终结果见`.local/evidence/development/EXT-EXPORT/acceptance179.json`。同步方法沿用原生限制，无独立取消句柄；普通错误注入覆盖原生失败、无输出、维度/格式拒绝及关闭失败。


## CAD NSC 几何与 ACIS 版本续验

纯NSC使用光源的`NumberOfLayoutRays`控制导出光线数，`number_of_rays>0`提前返回INACTIVE_SETTING；SolidRing继续沿用顺序系统条件。八种散射/分裂/偏振布尔组合逐项写入回读，旋转30度并平移的RectangularVolume经STEP实体、STL三角形独立读取，与解析体积96mm³和全局边界比较通过。预设体积/坐标绝对差1e-5+1e-6×参考值；66次数值比较包含导出后实际NSC追迹的已知首交点。设置、对象、配置与solve在保存重载基线后保持，工具及应用关闭通过。

ACIS版本为独立待验收条件：SAT/SAB分别运行Current及V25至V30共14次，设置getter采用请求，文件实际声明均为版本代码500（ACIS5.0）。现在SAT/SAB在关闭原生写入器后读取实际头；Current/省略返回`file_metadata`，显式V25至V30与实际版本不符时返回SETTING_REJECTED，附请求、实际版本和保留文件路径。ASAT/ASAB仍由原生执行，实际版本解析继续待探查；其他格式拒绝file_version参数。

原生版本拒绝后可再次使用Current成功导出，源状态保持。原始native180的NSC非活动光线数拒绝、native181的测试读取器类型名错误及14次版本探查均保留。证据汇总`.local/evidence/development/EXT-EXPORT/progress186.json`。CadSettings保留implemented，完成受控几何与NSC选项部分；后续需原生可实际采用指定ACIS版本的正式路径。B003保持8/10，继续其他可执行条目。

2026-11-07 ASAT/ASAB复核521：自有双平面N-BK7模型中，FileType及Current版本设置回读采用，但两种格式均在原生Run抛出 `Unsupported export format`，任务为failed/TASK_START_FAILED且关闭确认、无cleanup警告。模型曲面与系统设置保持，会话正常断开。当前没有可供检查的ASAT/ASAB文件头，`cad_formats`原有native_rejected登记继续适用。解除条件为实际可写这两格式的正式导出器/版本/许可；届时再检查头部及几何。520探查未处理启动阶段拒绝而失败，521修正探查并继续第二格式，原记录保留。证据 `.local/evidence/development/EXT-EXPORT/progress521-advanced-acis.json`。SAT/SAB显式V25–V30实际500、IGES分层65535的既有缺口保持。


2026-11-07 CAD585：分离实体和曲面IGES写出路径，各自测试all_by_layer与all_at_once；LensLayer10与两配置回读采用，四份文件均只有层号65535。该单变量实验未解决分层遗漏，原175/178缺口继续保留。四任务关闭，曲面/solve、系统、MFE/MCE逐次与保存重载后保持，正常断连；1个诊断pytest通过生命周期检查，分层验收为false。证据EXT-EXPORT/progress585-solid-surface-layers.json。
