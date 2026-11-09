# Universal Plot



本机正式接口为AS_Default，使用手册UN1/UN2配置键及SaveTo/ModifySettings/LoadFrom。原生194确认1D无数组、文本含变量身份和两列数值；2D有5×3非方形网格、轴范围和采样头信息。


```json
{"request":{"kind":"universal_plot_1d","surface":1,"start":2,"stop":6,"samples":5,"first_surface":1,"last_surface":1}}
```

配置键返回接受标志；执行后从原生文本核对Thickness、曲面编号、TTHI及首末曲面、采样数和实际横坐标。文本为六位科学计数，坐标回读容差5e-7×max(1,abs(value))，数值参考仍使用独立原容差1e-8+1e-7×参考值。结果提供series、rows、实际设置、文本和CFG文件，接入分页/PNG。





续验200：新增正式`CVVA`操作数，返回first_surface指定曲面的顶点曲率，单位为镜头长度单位的倒数；此操作数须省略last_surface。TTHI仍要求first_surface/last_surface。CVVA在半径扫描中应为1/r，在曲率扫描中应等于扫描值，原生199已确认这两种非恒定响应。原生文本只有六位科学计数精度，保留原始文本及此精度来源。

```json
{"request":{"kind":"universal_plot_1d","surface":1,"parameter":"Radius","start":2,"stop":4,"samples":3,"operand":"CVVA","first_surface":1}}
```




## Universal Plot 2D

`run_analysis.kind=universal_plot_2d`使用原生内部副本及正式UN2配置键。x/y各指定category、parameter、start、stop、samples；Surface轴必须提供surface，System轴的选择规则与1D相同。采样2–1001，网格预算65536点，两个轴须选择不同变量。操作数TTHI/CVVA与1D相同。

```json
{"request":{"kind":"universal_plot_2d","x":{"surface":1,"start":2,"stop":6,"samples":5},"y":{"surface":2,"start":3,"stop":5,"samples":3},"operand":"TTHI","first_surface":1,"last_surface":2}}
```

原生非方形5×3网格确认`values[y][x]`按X/Y升序，包含起止端点，步长=(stop-start)/(samples-1)。结果保留原生网格min_x/min_y/dx/dy，提供显式x/y坐标、单位、原生文本与CFG。原生文本数值表从高Y到低Y排列；原生结构化数组已为升序，沿用数组。分页和绘图共用这些坐标。

执行后核对原生文本的两轴参数/曲面、范围、采样及操作数身份，再与原生网格尺寸、坐标和步长比较。空网格、转置/尺寸冲突、设置拒绝与非有限值分别保留错误来源和原生文本路径。两轴都选同一变量时提前拒绝。




## 关闭故障定位及当前执行路径


当前2D在主分析所有者创建工具，使用手册3.6.1/3.6.2规定的Universal Plot内部模型副本隔离变量扫描；结果设置中记录isolation和native_display。保留异步任务，结果读取前调用正式WaitForCompletion；返回成功前确认关闭。结构化网格数据、坐标、单位和自定义PNG契约保持。当前内部原生显示选择GreyScale；Surface显示保留具体引擎阻塞及补丁后复测条件。完整条目仍implemented，其他类别/一般操作数及取消/恢复继续验收。


## 1D 系统变量

`category`默认Surface，沿用原有曲面请求；System类别必须省略surface。System的parameter支持Aperture、ApodizationFactor、Temperature、Pressure，单视场、单波长时原生参数编号分别为0、4、5、6；多视场/波长模型按下述展开规则动态解析。

```json
{"request":{"kind":"universal_plot_1d","category":"System","parameter":"Temperature","start":10,"stop":30,"samples":3,"operand":"TTHI","first_surface":1,"last_surface":1}}
```

温度使用摄氏度，压力使用大气压，切趾因子无量纲；孔径单位随当前ApertureType：EntrancePupilDiameter为镜头长度单位，ObjectConeAngle为度，F数/NA类型无量纲。FloatByStopSize无独立孔径数值而拒绝；Uniform模式的切趾因子不活动而拒绝。孔径须为正，压力和切趾因子非负，温度高于绝对零度；仍须start<stop。结果从原生文本核对系统变量身份、操作数和扫描坐标。条件与实际原生结果见EX-01/progress220.json。


续验223：System新增XField、YField、Wavelength，必须显式提供从1开始的`selection`；其他参数拒绝该字段。视场单位随当前FieldType：角度类型为degrees，高度类型为当前镜头长度单位；波长为micrometers。未知视场单位返回SETTING_UNCONFIRMED，索引越界在创建分析副本前拒绝，波长扫描值须为正。

```json
{"request":{"kind":"universal_plot_1d","category":"System","parameter":"Wavelength","selection":2,"start":0.45,"stop":0.65,"samples":3,"first_surface":1,"last_surface":1}}
```

原生System参数列表随视场数F和波长数W展开：Aperture=0、XField(i)=i、YField(i)=F+i、Wavelength(i)=2F+i、ApodizationFactor=2F+W+1、Temperature=2F+W+2、Pressure=2F+W+3。UN1_SURFACE不负责System索引选择。原生文本必须回读到正确的X/Y视场或波长编号；动态解析同时修复此前四项系统变量在多视场/多波长系统中的编号。



## 2D System 轴验收（228）

两轴复用1D的动态编号、单位与活动条件检查，支持Surface/System混合和双System组合。两个轴的变量身份包含类别、曲面或选择编号以及参数；同一曲面的Radius/Curvature视为同一属性。活动条件和索引在创建原生分析前检查。

```json
{"request":{"kind":"universal_plot_2d","x":{"surface":1,"parameter":"Radius","start":20,"stop":40,"samples":5},"y":{"category":"System","parameter":"Wavelength","selection":2,"start":0.45,"stop":0.65,"samples":3},"operand":"CVVA","first_surface":1}}
```


## Configuration 轴（232）

1D/2D增加`category=Configuration`，必须提供`configuration`和`operand_row`（均从1开始），parameter为`THIC`或`CRVT`，省略surface/selection。原生MCE行必须与请求类型一致，目标单元格须活动、可写，solve为Fixed或Variable。THIC单位为当前镜头长度，CRVT为其倒数。其他MCE类型继续逐项探查。

```json
{"request":{"kind":"universal_plot_1d","category":"Configuration","configuration":2,"operand_row":2,"parameter":"THIC","start":2,"stop":4,"samples":3,"first_surface":1,"last_surface":1}}
```

模型须预先建立对应MCE行；编号是实际行号，包含默认MOFF行。正式CFG使用CATEGORY=2、PARAMETER=MCE行号、SURFACE=配置号。扫描选定配置的单元格，计算使用源模型当前配置：选择其他配置不会自动切换计算配置。任务settings.configuration记录当前配置，selected_configuration记录扫描配置。原生文本确认MCE行号/类型；配置选择依据正式CFG接受结果与当前/其他配置独立响应验收，原生轴标题未提供单独配置号getter。


## 一般操作数与评价函数目标（236）

1D/2D共用可选`target`对象。沿用TTHI/CVVA旧入口时继续使用operand、first_surface和last_surface；使用target时省略这些旧字段。

- `{"mode":"operand","operand":"REAY","parameters":[1,1,0,0,0,0.5]}`：名称须为本机MeritOperandType枚举成员，parameters按原生PAR1至PAR8顺序，最多8项，省略的尾项写0。创建并及时关闭专用元数据副本，从该操作数的MFE活动单元格取得参数类型；整数参数拒绝小数，未活动参数拒绝非零值。正式CFG显式写全部八槽，结果文本核对操作数及活动参数的数量、顺序和值。
- `{"mode":"merit","line":0}`：整体原生评价函数。正行号返回该MFE行的原始操作数值，检查行号范围、原生行身份和操作数类型。正式CFG名称为区分大小写的`Merit`；不能将其改写为MERIT或MERI。

```json
{"request":{"kind":"universal_plot_1d","category":"System","parameter":"Aperture","start":4,"stop":8,"samples":3,"target":{"mode":"operand","operand":"REAY","parameters":[1,1,0,0,0,0.5]}}}
```

曲线/网格的标签使用实际目标名称。TTHI、REAX、REAY采用镜头长度单位，CVVA为其倒数。其他操作数及整体加权评价函数的物理单位未由本机元数据接口提供，返回null并保留unit_source；指定MFE行按该行操作数解析单位。操作数族的单位与独立参考继续扩充。目标类型、活动参数、参数头及写入值保存在任务settings.target。参数文本采用原生显示精度，回读容差5e-7；独立数值容差仍为1e-8+1e-7×参考绝对值。



## 纯 NSC 轴与生命周期（242）

1D/2D增加`category=NSC`，必须指定从1开始的object，使用显式target，省略surface、selection、configuration和operand_row。

parameter支持XPosition、YPosition、ZPosition、TiltX、TiltY、TiltZ；位置相对对象的RefObject，单位为当前镜头长度，倾斜单位为degrees。原生参数编号依次0–5，正式CFG的SURFACE字段在此类别表示对象号。执行前核对对象范围、单元格活动/可写及solve，拾取关系返回具体条件错误。

`parameter=ObjectParameter`时必须提供parameter_number（1–250），其他参数拒绝该字段；原生编号=parameter_number+5。读取对应ObjectColumn.ParN的活动状态、数据类型和solve。支持数值单元格；Integer类型要求起点、终点及每个等距采样点均为整数。Rectangle的参数1/2为半宽，轴及NPVA结果采用镜头长度单位；其他对象参数保留原生标题和数值，单位未确认时返回null及来源。最终结果标题核对对象、位置或参数号。

```json
{"request":{"kind":"universal_plot_1d","category":"NSC","object":1,"parameter":"XPosition","start":2,"stop":4,"samples":3,"target":{"mode":"operand","operand":"NPXV","parameters":[1,1,0]}}}
```


原生239取消验收使用Cooke、RSRE128：1D1001点和2D255×255点均实际进入取消终态，关闭确认无警告；源曲面、solve、系统设置和模型修订保持。每次取消后在同会话运行CVVA，6次数值比较最大绝对误差3.333333331578814e-9，容差1e-8+1e-7×参考绝对值。原生实例正常disconnect。


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



续验250：元数据副本中的NPVA单位读取改动补跑纯NSC回归，原生一项通过，54次数值检查误差0、源对象保持及关闭/断连通过。

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
