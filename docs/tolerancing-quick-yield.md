# Quick Yield

`run_analysis` accepts `kind="quick_yield"`. The typed request selects a user-defined field and wavelength, configuration, Monte Carlo trial count, pupil sampling, tolerance statistic, analysis precision, compensation precision, and compensator strategy. The native Quick Yield analysis uses the system tolerance definition; its current supported setting enums and call entry are recorded in `verification/development/WP-01/probe030.json`.

```json
{
  "request": {
    "kind": "quick_yield",
    "field": 1,
    "wavelength": 1,
    "configuration": 0,
    "monte_carlo_samples": 1000,
    "pupil_sampling": 3,
    "statistic": "Normal",
    "precision": "Standard",
    "compensation": "Standard",
    "field_mode": "UserDefined",
    "compensator_strategy": "OptimizeAllDampedLeastSquares"
  }
}
```

The adapter writes and reads back each writable scalar and enum. It sets the QY user field through native `QYField.SetFieldUser` and verifies the selected index. The standard analysis task path owns execution, cancellation, native text/series extraction, and resource close. Native startup is available. Current acceptance gaps and numerical experiments are recorded below.

Related existing entry points are `run_pop` for Gaussian beam propagation and receiver coupling and `get_beam_file` for paged ZBF data inspection. Those implement overlapping capabilities while dedicated `FiberCouplingSettings` and GUI `BeamFileViewer` selection contracts remain separate items. Both Gaussian beam analyses completed acceptance in WP-01/acceptance362-gaussian.json.

`run_analysis` also accepts `kind="tolerance_yield"` and `kind="tolerance_histogram"`. Both requests select a zero-based tolerance operand and either use system tolerances or name a tolerance file exposed by the native settings object. Histogram additionally requires a finite increasing range and a bin count from 1 through 1000. The implementation records the selected source and reads back `Operand`, `MinValue`, `MaxValue`, and `NumBins`; results use the standard native text, series, and grid fields. Cooke-system distribution acceptance is recorded in TO-01/acceptance085.json and `tests/test_tolerance_special_analyses_live.py`.


Examples: [examples/quick-yield030.json](../examples/quick-yield030.json) and [examples/tolerance-statistics030.json](../examples/tolerance-statistics030.json).



2026-11-05续探查083：修复TolDataFile需文件名的本机行为，ZTD成功生成并被专题发现；修复QuickYield最小/默认1000与SetFieldUser成功返回null处理。QuickYield Cooke单参数执行、99点良率曲线、模型保持和关闭通过；独立数值、分页绘图及取消仍待完成。公差Yield文件与操作数采用后原生返回无效结果，Histogram尚未到达；继续分别探查。相关普通56通过；证据verification/development/TO-01/probe083.json。B002仍6/10，未执行全量或wheel。


2026-11-05编号与数值续验：ToleranceYield/Histogram 的公开 `operand` 是 GetOperands 列表的零起始编号，原生 Operand 为一基编号。结果任务的 `operand_selection` 同时记录 public_index、native_index 和 count。列表可包括准则、公差操作数及补偿器，以所选ZTD的实际列表为准。

Cooke十次MonteCarlo的准则列与TTHI列均已取得原生累计曲线和直方图。累计曲线内部采样点与原始试验值的经验累计百分比比较；直方图中心和计数按公开范围及bin数独立重算，固定容差分别为1e-8+1e-7相对、中心1e-10+1e-10相对。范围外汇总、失败样本及保存重载验收继续开放。

QuickYield零扰动参考仍超限：原生0.24512342752844274 waves，当前Centroid/GaussQuad3 RMS参考0.21532002492833044 waves，预设容差1e-5+1%保持。记录native084-index-fixed.xml与outputs/runs/quickyield084zero_bfc5a09198；继续定位参考定义与拟合条件。

2026-11-07 follow-up: 零扰动结果为0.24512342752844274 waves。18组RMS-vs-field特征对照显示，波长1下GaussQuad从3环增至10环后稳定在0.215335390657296 waves；Centroid与ChiefRay相同，采样环数与参考点未解释两者0.0297880368711467 waves的差值。波长2、3基准分别为0.182882174372852和0.27176021829815 waves。原`1e-5 + 1%`容差保持。结果见`outputs/runs/quickyield084zero_db3ca5c648/reference.json`和`outputs/runs/quickyield086_reference_5d4713d16b/characterization.json`。


2026-11-06：ToleranceYield与ToleranceHistogram完成原生存储值分布验收。新增distribution样本数、区间内计数及上下溢计数，计数总和与原生样本数核对；下溢4+区间内8+上溢4=16，失败样本5/8以9e9保留，累计曲线有效部分37.5%。固定容差保持，分页/PNG、保存重载、错误后复用、设置/曲面保持与关闭通过。普通66通过；原生最终3项及混合上下溢1项通过，早期四列数值对照见084。证据verification/development/TO-01/acceptance085.json。B002累计8/10，继续QuickYield定义差异及GeometricImage；未做全量或wheel。

`distribution` 返回 sample_count；Histogram另外返回underflow、overflow、in_range_count，曲线仅含区间内的柱。y_unit分别是percent和count。原生分布保留包括有限失败哨兵在内的存储值，failure_handling明确说明其口径。

2026-11-07 执行493/494：抛物面零像差、纯离焦与球面镜各用Standard/VeryHigh做六组零扰动比较，均满足`1e-5 waves + 1%`。离焦RMS=0.013110780303867043 waves，球面RMS=0.010584340635982752 waves。Cooke瞳采样3/5/10在Standard下均为0.24512342752844274，VeryHigh均为0.24567772661945006；同场同波长RMS=0.2153353906572962，差异仍超限。两项诊断测试通过表示完成受控实验与关闭检查，Cooke数值验收仍未通过。12次分析关闭、模型保持及断连通过。详见`verification/development/TO-01/progress494-controlled.json`。下一步分离Cooke瞳加权与拟合参考球，并补有限扰动与取消。

2026-11-07 执行502–507：新增最终组合检查，在QYField选择后重新核对配置、试验数、瞳采样、各枚举、用户视场模式和波长。结果保留原生曲线值及标签，明确横轴RMS波前单位waves、良率单位percent，并记录评价选择；非有限或越界的良率列返回INVALID_RESULT_DATA。

受控离焦模型TTHI±0.002mm、Uniform10000次的五个分位点，与独立厚度分位值处RMS比较通过；保存重载后再次运行，五个点仍通过原1e-5 waves+1%容差，共10次检查。100000次运行中取消、原生关闭、取消后复用、曲面/solve、系统设置、TDE/MCE/MFE保持和重载均通过。分页、PNG输出及查看通过。定向普通31通过，最终原生native507-uniform-reload.xml通过。

506曾按两次Monte Carlo结果逐点相等断言，观察到2.3792e-6 waves差异；此记录保留，507改为两次试验分别对照同一解析分布，采用原数值容差。Cooke零扰动差异仍开放。证据：TO-01/progress502-uniform.json、progress507-final-readback-uniform.json；501文本确认公开field1对应0度、wavelength1对应0.4800um，未据此改变编号。

2026-11-07 independent pupil check515 reuses50613 valid OPD rays from Cooke field1/wavelength1 in509. Uniform entrance-pupil population RMS after piston removal is0.2153820447waves, differing from GaussQuad10 ChiefRay RMS0.2153353907 by0.0000466540waves. Standard QuickYield remains0.2451234275, difference0.0297413828 from the independent ray RMS, outside the unchanged1e-5waves+1% gate. Including piston gives0.593386429 and does not explain QuickYield. No new native task was opened. The internal fitted-aberration/reference-sphere or weighting definition remains to be established; finite perturbation/lifecycle results507 remain accepted. Evidence: verification/development/TO-01/progress515-pupil-rms.json.


2026-11-07 执行530/535：Cooke field1/wave1仅切换正式WavefrontMap.ReferenceToPrimary，保持256采样、UseExitPupil=false和RemoveTilt=false；两次50613点去活塞RMS均0.21538204468387392waves，与Standard QuickYield差0.029741382844568814，仍超原门槛。两分析关闭、系统/曲面保持且断连。本机手册索引1291/1292说明使用灵敏度拟合波前及modified Rimmer重建，重建细节为专有；这份材料没有提供足以独立预测当前差值的拟合项。继续保留implemented及507有限扰动证据。详见TO-01/progress530-reference-primary.json和CV-01/manual535-reference-assumptions.json。


2026-11-07 高阶精度诊断549/550：受控EvenAspheric镜面加入单项r6/r8/r10/r12，使四者边缘增加相同0.0003125mm sag。256个独立径向均面积中点OPD样本的去活塞RMS与GaussQuad10通过原1e-5waves+1%门槛。VeryHigh四项最大误差依次5.7230e-6、8.6698e-6、7.8664e-5、0.0003196035waves，均通过；Standard的r6差0.00313157通过，r8/r10/r12差0.00819337/0.01375458/0.01897441waves，均超原门槛。

这组控制实验显示阶次相关的拟合精度差异。Cooke在VeryHigh下仍保留既有约0.0303423waves差异，需要受控折射模型或正式拟合定义继续区分；整体状态implemented。549/550各1诊断测试通过表示独立参考与状态/关闭检查完成，其中Standard三项数值失败明确保留。八次QuickYield均关闭、两会话断连，曲面/solve/系统/MFE/MCE/TDE保持。详见TO-01/progress550-high-order.json。


2026-11-07 执行568–575：QuickYield受控参考与生命周期完成验收。Cooke原差异来自参考模型的solve求值条件：第6面半径采用MarginalRayAngle，源主波长为2。保留该solve、选择波长1/3运行QuickYield，与先将所选波长设为主波长后独立追迹的OPD RMS相符，最大差6.626551e-7 waves。独立参考模型的半径从−18.395332603变为蓝光−18.398367999、红光−18.378296012 mm；原生QuickYield运行前后的活动源模型及solve保持。

固定第6面半径后，活动源模型参考与QuickYield也通过原门槛，最大差6.904929e-7 waves。569原三波长与逐一单色化实验中，原主波长和三个单色情形均通过；该实验首先指向主波长相关solve。570动态控制通过，固定控制首次因缺少replace_solves而被保护拒绝，571显式替换后通过。全部原始差异与失败保留。

折射控制采用N-BK7平凸透镜、10mm入口瞳、6mm净半口径和0/3度、0/6度两组视场。64×64均面积瞳点独立OPD RMS去除活塞及最小二乘线性瞳倾斜后，与Standard/VeryHigh均通过1e-5 waves+1%参考值；八组最大差6.361863e-5 waves。原始仅去活塞RMS另列，离轴差值保留。572首轮6度的5mm孔径截断15/4096条光线，573扩大声明净孔径后全部光线有效，两项通过。这里记录受控数值等价关系，原生专有重建算法仍按手册定义。

574最终原生四项通过：修正参考条件的原始Cooke零扰动、Uniform有限扰动五分位及重载五分位、活动任务取消/关闭/复用，以及Cooke动态和固定solve控制。575定向普通80项通过。源模型系统/曲面/solve/MFE/MCE/TDE保持，stdio、分页、PNG与断连通过，Uniform PNG已查看。结果新增evaluation.source_wavelengths及带证据的reference_equivalence；空、非有限、负RMS及轴行数冲突明确拒绝，原生数值保持。

高阶r8/r10/r12在Standard精度下的旧超限继续作为原生拟合精度限制；VeryHigh的r6–r12参考沿用550的通过证据。本次以匹配原生求值条件的零扰动、单像差、有限扰动及生命周期证据完成共同功能，B006增至5/10，详见verification/development/TO-01/acceptance574-reference.json。原1e-5 waves+1%容差保持。
