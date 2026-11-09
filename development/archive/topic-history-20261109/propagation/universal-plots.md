# Universal Plot

2026-11-08计划范围：Universal Plot属于已完成的原生分析，沿用既有证据；EX-01工作包的用户代码宿主及回调后续开发已归档。当前计划见[原生功能收口](../../../development/current.md)。


本机正式接口为AS_Default，使用手册UN1/UN2配置键及SaveTo/ModifySettings/LoadFrom。原生194确认1D无数组、文本含变量身份和两列数值；2D有5×3非方形网格、轴范围和采样头信息。

当前1D/2D共用Surface/System/Configuration/NSC扫描轴：Surface支持Radius、Curvature、Thickness、Conic、TCE和SurfaceParameter；System支持孔径、切趾、温压、视场和波长；Configuration提供有类型的数值ConfigurationValue及THIC/CRVT别名；NSC支持纯模式及显式混合组的位置、倾斜和对象参数。保留TTHI/CVVA旧入口，并支持一般数值操作数和整体/指定行评价函数target。1D扫描在独立原生副本执行；2D采用GreyScale及原生内部副本。samples默认21，范围2–1001，start<stop。两项声明范围已完成，最终证据为.local/evidence/development/EX-01/acceptance261.json；下文保留各轮探查与修复记录。

```json
{"request":{"kind":"universal_plot_1d","surface":1,"start":2,"stop":6,"samples":5,"first_surface":1,"last_surface":1}}
```

配置键返回接受标志；执行后从原生文本核对Thickness、曲面编号、TTHI及首末曲面、采样数和实际横坐标。文本为六位科学计数，坐标回读容差5e-7×max(1,abs(value))，数值参考仍使用独立原容差1e-8+1e-7×参考值。结果提供series、rows、实际设置、文本和CFG文件，接入分页/PNG。

普通7项及真实stdio原生1项通过，五个TTHI参考点、分页/PNG及模型保持通过，证据.local/evidence/development/EX-01/progress195.json。条目implemented；其余变量、操作数/评价函数及生命周期验收继续开发，2D目前为原生接口探查阶段。发行wheel仍为0.1.58/96分析，工作源码新增此请求。


续验197：parameter支持`Radius/Curvature/Thickness`，分别经本机编号0/1/2确认。Radius和Thickness采用镜头长度单位，Curvature采用其倒数；结果保留原生变量身份。原生参数3在受控Standard面回退到Radius，尚未作为Conic公开。普通108通过（含镀膜适配相关回归），真实stdio原生3通过，均包含源状态保持、分页、PNG与关闭；证据.local/evidence/development/EX-01/progress197.json。其他类别及一般操作数继续开发，状态保持implemented。


续验200：新增正式`CVVA`操作数，返回first_surface指定曲面的顶点曲率，单位为镜头长度单位的倒数；此操作数须省略last_surface。TTHI仍要求first_surface/last_surface。CVVA在半径扫描中应为1/r，在曲率扫描中应等于扫描值，原生199已确认这两种非恒定响应。原生文本只有六位科学计数精度，保留原始文本及此精度来源。

```json
{"request":{"kind":"universal_plot_1d","surface":1,"parameter":"Radius","start":2,"stop":4,"samples":3,"operand":"CVVA","first_surface":1}}
```

正式枚举MeritOperandType含CVVA、不含CURV；未知操作数由请求模型拒绝。一般操作数、其他变量类别及2D仍为后续范围，完整条目保持implemented。最终本轮检查和关闭见.local/evidence/development/EX-01/progress200.json。

本轮最终相关普通110通过、原生5通过。CVVA半径与曲率各三个点保持原数值容差，原生文本精度作为结果来源保留。副本清理失败时保留最初分析创建错误，并进入重连状态。


## Universal Plot 2D

`run_analysis.kind=universal_plot_2d`使用原生内部副本及正式UN2配置键。x/y各指定category、parameter、start、stop、samples；Surface轴必须提供surface，System轴的选择规则与1D相同。采样2–1001，网格预算65536点，两个轴须选择不同变量。操作数TTHI/CVVA与1D相同。

```json
{"request":{"kind":"universal_plot_2d","x":{"surface":1,"start":2,"stop":6,"samples":5},"y":{"surface":2,"start":3,"stop":5,"samples":3},"operand":"TTHI","first_surface":1,"last_surface":2}}
```

原生非方形5×3网格确认`values[y][x]`按X/Y升序，包含起止端点，步长=(stop-start)/(samples-1)。结果保留原生网格min_x/min_y/dx/dy，提供显式x/y坐标、单位、原生文本与CFG。原生文本数值表从高Y到低Y排列；原生结构化数组已为升序，沿用数组。分页和绘图共用这些坐标。

执行后核对原生文本的两轴参数/曲面、范围、采样及操作数身份，再与原生网格尺寸、坐标和步长比较。空网格、转置/尺寸冲突、设置拒绝与非有限值分别保留错误来源和原生文本路径。两轴都选同一变量时提前拒绝。

本条目状态implemented，继续其他变量类别、一般操作数、失败/取消/恢复等完整验收。当前证据EX-01/progress206.json；B0038/10，源码98分析请求，发行wheel仍为96。

续验206–210：相关普通117通过；TTHI受控网格15点、分页/PNG及源状态检查曾通过。CVVA数值通过后关闭发生IPC错误，独立复现及半径20–40基线均未解决；TTHI的提前关闭亦复现。当前关闭失败明确使任务CLEANUP_FAILED并要求重连。完整原生生命周期仍待验收，保留implemented；下一步比较原生同步ApplyAndWaitForCompletion与任务异步Apply的完成握手，不能将原生202同步关闭通过扩展为异步链路已通过。原始失败和结论见EX-01/progress206.json。


## 关闭故障定位及当前执行路径

续验217：Windows事件1000/1026确认ZemaxCore.dll在Optical_System.Close / ZemaxAnalyses.CloseAnalysis中访问异常。直接同步/异步的CVVA Surface视图均复现；去掉外部CopySystem不足以消除该问题。改用正式UN2_SHOWAS=2（GreyScale）后，TTHI/CVVA原生用例及1D回归共3项通过、33次数值比较，保存重载基线、模型/solve保持、分页/PNG、资源关闭和disconnect通过；普通118通过。

当前2D在主分析所有者创建工具，使用手册3.6.1/3.6.2规定的Universal Plot内部模型副本隔离变量扫描；结果设置中记录isolation和native_display。保留异步任务，结果读取前调用正式WaitForCompletion；返回成功前确认关闭。结构化网格数据、坐标、单位和自定义PNG契约保持。当前内部原生显示选择GreyScale；Surface显示保留具体引擎阻塞及补丁后复测条件。完整条目仍implemented，其他类别/一般操作数及取消/恢复继续验收。证据EX-01/progress217.json，原始失败记录不改写。


## 1D 系统变量

`category`默认Surface，沿用原有曲面请求；System类别必须省略surface。System的parameter支持Aperture、ApodizationFactor、Temperature、Pressure，单视场、单波长时原生参数编号分别为0、4、5、6；多视场/波长模型按下述展开规则动态解析。

```json
{"request":{"kind":"universal_plot_1d","category":"System","parameter":"Temperature","start":10,"stop":30,"samples":3,"operand":"TTHI","first_surface":1,"last_surface":1}}
```

温度使用摄氏度，压力使用大气压，切趾因子无量纲；孔径单位随当前ApertureType：EntrancePupilDiameter为镜头长度单位，ObjectConeAngle为度，F数/NA类型无量纲。FloatByStopSize无独立孔径数值而拒绝；Uniform模式的切趾因子不活动而拒绝。孔径须为正，压力和切趾因子非负，温度高于绝对零度；仍须start<stop。结果从原生文本核对系统变量身份、操作数和扫描坐标。条件与实际原生结果见EX-01/progress220.json。完整条目继续implemented，配置/NSC类别和其他操作数等仍待开发。


续验223：System新增XField、YField、Wavelength，必须显式提供从1开始的`selection`；其他参数拒绝该字段。视场单位随当前FieldType：角度类型为degrees，高度类型为当前镜头长度单位；波长为micrometers。未知视场单位返回SETTING_UNCONFIRMED，索引越界在创建分析副本前拒绝，波长扫描值须为正。

```json
{"request":{"kind":"universal_plot_1d","category":"System","parameter":"Wavelength","selection":2,"start":0.45,"stop":0.65,"samples":3,"first_surface":1,"last_surface":1}}
```

原生System参数列表随视场数F和波长数W展开：Aperture=0、XField(i)=i、YField(i)=F+i、Wavelength(i)=2F+i、ApodizationFactor=2F+W+1、Temperature=2F+W+2、Pressure=2F+W+3。UN1_SURFACE不负责System索引选择。原生文本必须回读到正确的X/Y视场或波长编号；动态解析同时修复此前四项系统变量在多视场/多波长系统中的编号。

两视场、两波长下七项系统扫描、源状态保持及关闭已通过；相关普通130通过、原生223两项通过（含1D CVVA回归）。物高/厘米单位续验及完整记录见EX-01/progress224.json。一般配置/NSC类别、其他操作数及完整生命周期仍待开发，状态保持implemented。

续验225/226：有限物距ObjectHeight在厘米单位下的索引2扫描通过，源设置/solve保持及正常disconnect通过；无限物距原始无效分析保留native224，现提前返回INVALID_MODEL。原生无效结果返回原始消息。最终相关普通131通过，native223两项和native225一项分别记录；完整范围继续implemented。

## 2D System 轴验收（228）

两轴复用1D的动态编号、单位与活动条件检查，支持Surface/System混合和双System组合。两个轴的变量身份包含类别、曲面或选择编号以及参数；同一曲面的Radius/Curvature视为同一属性。活动条件和索引在创建原生分析前检查。

```json
{"request":{"kind":"universal_plot_2d","x":{"surface":1,"parameter":"Radius","start":20,"stop":40,"samples":5},"y":{"category":"System","parameter":"Wavelength","selection":2,"start":0.45,"stop":0.65,"samples":3},"operand":"CVVA","first_surface":1}}
```

真实stdio串行4项通过，合计174次数值比较；新增System网格120次，固定容差为1e-8+1e-7×参考绝对值。七类System变量分别与半径混合扫描，另验有限物距ObjectHeight/厘米与波长的双System网格。原生文本逐轴确认选择身份、范围和采样；源系统/曲面/solve保持、保存重载基线、分页、PNG和关闭通过。相关普通138项通过。原生227的4项跳过保留历史来源；原生228实际运行4项、跳过0项。证据：.local/evidence/development/EX-01/progress228.json。Configuration/NSC、一般操作数/评价函数及完整取消恢复继续开发，两个条目保持implemented，B003为8/10。

## Configuration 轴（232）

1D/2D增加`category=Configuration`，必须提供`configuration`和`operand_row`（均从1开始），parameter为`THIC`或`CRVT`，省略surface/selection。原生MCE行必须与请求类型一致，目标单元格须活动、可写，solve为Fixed或Variable。THIC单位为当前镜头长度，CRVT为其倒数。其他MCE类型继续逐项探查。

```json
{"request":{"kind":"universal_plot_1d","category":"Configuration","configuration":2,"operand_row":2,"parameter":"THIC","start":2,"stop":4,"samples":3,"first_surface":1,"last_surface":1}}
```

模型须预先建立对应MCE行；编号是实际行号，包含默认MOFF行。正式CFG使用CATEGORY=2、PARAMETER=MCE行号、SURFACE=配置号。扫描选定配置的单元格，计算使用源模型当前配置：选择其他配置不会自动切换计算配置。任务settings.configuration记录当前配置，selected_configuration记录扫描配置。原生文本确认MCE行号/类型；配置选择依据正式CFG接受结果与当前/其他配置独立响应验收，原生轴标题未提供单独配置号getter。

2D两个Configuration轴可组合不同MCE行；与Surface轴组合时，若解析到当前配置的同一曲面属性则提前拒绝。原生验收232覆盖THIC与CRVT、当前/其他配置、双Configuration的5×3网格，24次数值比较最大绝对误差0，固定容差1e-8+1e-7×参考绝对值。保存重载基线、源系统/曲面/solve/MCE/当前配置保持、分页、PNG与关闭通过。相关普通152通过，原生231两项通过，元数据补充检查后的原生232一项通过。证据.local/evidence/development/EX-01/progress232.json；示例examples/requests/universal-configuration232.json。两个Universal条目仍implemented，下一步其他MCE/NSC、一般操作数/评价函数及生命周期。

## 一般操作数与评价函数目标（236）

1D/2D共用可选`target`对象。沿用TTHI/CVVA旧入口时继续使用operand、first_surface和last_surface；使用target时省略这些旧字段。

- `{"mode":"operand","operand":"REAY","parameters":[1,1,0,0,0,0.5]}`：名称须为本机MeritOperandType枚举成员，parameters按原生PAR1至PAR8顺序，最多8项，省略的尾项写0。创建并及时关闭专用元数据副本，从该操作数的MFE活动单元格取得参数类型；整数参数拒绝小数，未活动参数拒绝非零值。正式CFG显式写全部八槽，结果文本核对操作数及活动参数的数量、顺序和值。
- `{"mode":"merit","line":0}`：整体原生评价函数。正行号返回该MFE行的原始操作数值，检查行号范围、原生行身份和操作数类型。正式CFG名称为区分大小写的`Merit`；不能将其改写为MERIT或MERI。

```json
{"request":{"kind":"universal_plot_1d","category":"System","parameter":"Aperture","start":4,"stop":8,"samples":3,"target":{"mode":"operand","operand":"REAY","parameters":[1,1,0,0,0,0.5]}}}
```

曲线/网格的标签使用实际目标名称。TTHI、REAX、REAY采用镜头长度单位，CVVA为其倒数。其他操作数及整体加权评价函数的物理单位未由本机元数据接口提供，返回null并保留unit_source；指定MFE行按该行操作数解析单位。操作数族的单位与独立参考继续扩充。目标类型、活动参数、参数头及写入值保存在任务settings.target。参数文本采用原生显示精度，回读容差5e-7；独立数值容差仍为1e-8+1e-7×参考绝对值。

原生235串行4项通过，包含一般REAY、整体及指定行Merit、Configuration和既有TTHI/CVVA网格回归。新增目标54次数值比较最大绝对误差0：平面光阑REAY=孔径/4，单行TTHI的line1=厚度之和，target1/weight1时line0=|厚度之和−1|。覆盖1D与5×3的2D、非恒定System响应、基线保存重载、源曲面/solve/系统/MFE设置保持、分页、PNG及关闭/断连。

原生可能在IsValid=true时导出“操作数不能计算”的报告；此时返回ANALYSIS_FAILED，保留原始报告和路径。未知名称、活动参数不符、整数类型错误、结果身份不符分别保留具体来源。元数据副本关闭失败要求重连，并保留先前探查错误。相关普通最终188通过；证据.local/evidence/development/EX-01/progress236.json，例子examples/requests/universal-targets236.json。其他MCE/NSC变量、更多操作数族与单位、完整取消/失败/恢复继续开发；两个完整条目保持implemented，B0038/10。

## 纯 NSC 轴与生命周期（242）

1D/2D增加`category=NSC`，必须指定从1开始的object，使用显式target，省略surface、selection、configuration和operand_row。当前原生验收覆盖纯NonSequential模型，2D两个轴均为NSC；混合顺序NSC组的显式选择与恢复继续探查。

parameter支持XPosition、YPosition、ZPosition、TiltX、TiltY、TiltZ；位置相对对象的RefObject，单位为当前镜头长度，倾斜单位为degrees。原生参数编号依次0–5，正式CFG的SURFACE字段在此类别表示对象号。执行前核对对象范围、单元格活动/可写及solve，拾取关系返回具体条件错误。

`parameter=ObjectParameter`时必须提供parameter_number（1–250），其他参数拒绝该字段；原生编号=parameter_number+5。读取对应ObjectColumn.ParN的活动状态、数据类型和solve。支持数值单元格；Integer类型要求起点、终点及每个等距采样点均为整数。Rectangle的参数1/2为半宽，轴及NPVA结果采用镜头长度单位；其他对象参数保留原生标题和数值，单位未确认时返回null及来源。最终结果标题核对对象、位置或参数号。

```json
{"request":{"kind":"universal_plot_1d","category":"NSC","object":1,"parameter":"XPosition","start":2,"stop":4,"samples":3,"target":{"mode":"operand","operand":"NPXV","parameters":[1,1,0]}}}
```

纯NSC受控Rectangle原生242通过：六种位置/倾斜、两个半宽参数、位置和参数的5×3网格，共10个成功关闭任务，54次数值比较最大绝对误差0；保存重载基线、源对象/solve/系统设置保持、分页和PNG通过。示例examples/requests/universal-nsc242.json。原生241两项通过，另覆盖Configuration回归。

原生239取消验收使用Cooke、RSRE128：1D1001点和2D255×255点均实际进入取消终态，关闭确认无警告；源曲面、solve、系统设置和模型修订保持。每次取消后在同会话运行CVVA，6次数值比较最大绝对误差3.333333331578814e-9，容差1e-8+1e-7×参考绝对值。原生实例正常disconnect。

1D与2D均在收集器返回成功前确认资源关闭；失败返回CLEANUP_FAILED并要求重连。普通故障注入覆盖两个适配器的设置拒绝、启动失败、原生计算报告、结果身份解析失败、取消、关闭失败及计算失败后的再次调用。最终相关普通235项通过，证据.local/evidence/development/EX-01/progress242.json。按本机手册扩充RSCE/RSCH/RSRE/RSRH镜头长度单位和RWCE/RWCH/RWRE/RWRH的waves单位。混合NSC组、其他MCE/曲面参数、更多目标族及原生失败恢复继续开发；两个完整Universal条目保持implemented，B0038/10。

## 混合 NSC 组与扩展曲面轴（249）

混合顺序模型的NSC轴必须指定`nsc_surface`，表示LDE中的NonSequential组件曲面号；纯NSC省略该字段。NSC组按LDE顺序展开为CATEGORY=3+组的零基序号，SURFACE仍为该组内的对象号。两组模型中曲面2/4分别对应类别3/4。NCE.ActiveSurface只影响编辑器元数据读取，不能替代此扫描选择。读取活动/可写及solve信息时临时选择组并立即恢复，原生分析运行期间保持源编辑器选择。恢复失败返回RESTORE_FAILED，保留原始操作错误并要求重连。

1D支持任意已存在NSC组；2D支持不同组组合，以及顺序模型中的NSC与Surface轴组合。两轴身份包含NSC组号，允许不同组中同号对象/同名参数独立扫描。组身份通过正式CFG类别、模型组列表及受控独立数值响应确认；原生轴标题保留对象/位置或参数号，未单列NSC组号。

Surface新增`parameter=Conic`，原生索引4，单位dimensionless；`parameter=SurfaceParameter`必须指定parameter_number1–254，原生索引=n+6。检查原生单元格活动、可写、solve和数值类型，Integer参数要求全部采样点为整数。原生标题确认圆锥系数或准确参数号。CoordinateBreak的参数1/2采用镜头长度单位，3/4/5为degrees，6为dimensionless；其他曲面参数单位未确认时返回null及原生参数标题。COVA返回圆锥系数，PMVA返回指定曲面参数，已确认类型按同一单位定义输出。ObjectParameter仍接受1–250。

```json
{"request":{"kind":"universal_plot_1d","surface":1,"parameter":"Conic","start":0.001,"stop":0.003,"samples":3,"target":{"mode":"operand","operand":"COVA","parameters":[1]}}}
```

```json
{"request":{"kind":"universal_plot_1d","category":"NSC","nsc_surface":4,"object":1,"parameter":"XPosition","start":2,"stop":4,"samples":3,"target":{"mode":"operand","operand":"NPXV","parameters":[4,1,0]}}}
```

本机探查显示索引3回退Radius，索引6报告Parameter0；两者均未作为上述新字段开放。COVA是已安装枚举中的圆锥系数值操作数；CCVA不在枚举中，原始CFG不能计算报告保留。CoordinateBreak的Conic不活动，即使原生接受标题，COVA仍为0；适配器按活动条件提前拒绝。

原生248两项及扩展249一项通过。最终两个执行记录包含13个成功关闭任务、87次数值比较，最大绝对误差0：COVA/PMVA等于请求属性值，NPXV/NPVA等于组内位置/矩形半宽，两个等权零目标NPXV行的Merit为sqrt((x²+y²)/2)。覆盖两个NSC组、对象参数、跨组5×3网格、NSC/Surface组合、保存重载、源曲面/solve/对象/活动组/修订保持、分页、PNG和断连。

修复绘图对null单位的处理：保留结果中的null，轴标签显示单位参见结果，色标使用值名称。原始native247导出失败及日志保留；修复后EvenAspheric/CoordinateBreak和混合模型PNG通过，并查看EvenAspheric图的坐标、色标与标签。相关普通247通过（含绘图、共用生命周期和任务产物回归）。证据.local/evidence/development/EX-01/progress249.json，例子examples/requests/universal-extended249.json。其他数值MCE轴、更多操作数族/单位及原生计算失败恢复继续开发，完整Universal两项保持implemented；B0038/10。

续验250：元数据副本中的NPVA单位读取改动补跑纯NSC回归，原生一项通过，54次数值检查误差0、源对象保持及关闭/断连通过。最终请求schema与证据EX-01/progress249.json同步更新。

## 数值 MCE、设置保护与最终验收（261）

Configuration新增`parameter=ConfigurationValue`，必须指定`mce_operand`为预期的本机四字符MCE类型，并提供从1开始的configuration和operand_row。执行前核对实际类型、单元格活动/可写、数值数据类型及solve。String等非数值单元格返回具体条件错误；Integer要求每个采样点为整数。TEMP须高于绝对零度，PRES非负，WAVE为正。已确认单位包括长度、曲率、圆锥常数、温压、波长、视场、CoordinateBreak参数及TCE；其余单位未由接口提供时返回null及来源。

原生行的参数列表逐项回读并与结果标题比较。WAVE、XFIE、YFIE的API Param1从0开始，标题编号从1开始；`native_operand_parameters`保留原始值，`operand_parameters`保存标题值。变量物理身份据此统一，拒绝同一配置中System轴与MCE轴等实际相同的双轴组合。视场高度单位与有限物距条件沿用System轴规则。

```json
{"request":{"kind":"universal_plot_1d","category":"Configuration","parameter":"ConfigurationValue","mce_operand":"PRAM","configuration":2,"operand_row":6,"start":0.1,"stop":0.3,"samples":3,"target":{"mode":"operand","operand":"PMVA","parameters":[1,1]}}}
```

TCE扫描使用原生索引5，TCVA读取其值，单位ppm/Celsius；例如TCE=100表示每摄氏度相对长度变化100×10^-6。MCE TCEX采用同一单位。探查确认原生REAY波长99可在标题保留99的同时使用有效波长，因此一般操作数的活动波长、视场及曲面编号在执行前检查。原生定义允许的0号特殊值仍按具体操作数定义解释，完整模型波长/视场设置保存在结果上下文。

多配置`update_merit_function(mode=replace)`须以显式CONF行开头。CONF省略target/weight，仅指定parameters第2列的配置号。stdio保留原请求中省略字段的信息；完成后重新检查最终行类型、参数、目标和权重。原始隐式CONF插入导致TTHI/PMVA被改写的失败、MCE波长零基编号失败和修复分别保留native253/native255及后续证据。Merit目标记录`merit_configurations`及`configuration_scope`，使用评价函数中的配置指令解释结果。

```json
{"mode":"replace","operands":[{"type":"CONF","parameters":{"2":2}},{"type":"TTHI","parameters":{"2":1,"3":1},"target":0,"weight":1},{"type":"PMVA","parameters":{"2":1,"3":1},"target":0,"weight":1}]}
```

最终普通334项通过，Universal原生17项通过、无跳过；471次数值比较均满足原定容差。75个原生任务包含71成功、2实际取消、2按设置回读失败，均确认关闭；失败/取消后同会话复用通过。覆盖全部公开轴类别、TCE、九类数值MCE代表、双波长/双视场、一般数值目标、整体/行Merit、非方形网格、保存重载、源模型/solve/配置/活动组/修订保持、分页及PNG。计算报告、启动、设置、解析和关闭错误另有故障注入检查；历史原生异常保留具体归属。

两个Universal条目标为done；原生Surface显示关闭异常、未提供物理单位的字段、非数值/资源型单元格，以及BLNK占位参数无法确认的报告，保留明确条件和失败输出。例子examples/requests/universal-numeric-mce261.json，完整验收.local/evidence/development/EX-01/acceptance261.json。B003达到10/10，0.1.59集中发行检查正在执行。
