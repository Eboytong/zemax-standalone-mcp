# Quick Yield


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

`run_analysis` also accepts `kind="tolerance_yield"` and `kind="tolerance_histogram"`. Both requests select a zero-based tolerance operand and either use system tolerances or name a tolerance file exposed by the native settings object. Histogram additionally requires a finite increasing range and a bin count from 1 through 1000. The implementation records the selected source and reads back `Operand`, `MinValue`, `MaxValue`, and `NumBins`; results use the standard native text, series, and grid fields. Cooke-system distribution acceptance is recorded in TO-01/acceptance085.json and `tests/native/test_tolerance_special_analyses_live.py`.


Examples: [examples/requests/quick-yield030.json](../../../examples/requests/quick-yield030.json) and [examples/requests/tolerance-statistics030.json](../../../examples/requests/tolerance-statistics030.json).






Cooke十次MonteCarlo的准则列与TTHI列均已取得原生累计曲线和直方图。累计曲线内部采样点与原始试验值的经验累计百分比比较；直方图中心和计数按公开范围及bin数独立重算，固定容差分别为1e-8+1e-7相对、中心1e-10+1e-10相对。范围外汇总、失败样本及保存重载验收继续开放。

QuickYield零扰动参考仍超限：原生0.24512342752844274 waves，当前Centroid/GaussQuad3 RMS参考0.21532002492833044 waves，预设容差1e-5+1%保持。




`distribution` 返回 sample_count；Histogram另外返回underflow、overflow、in_range_count，曲线仅含区间内的柱。y_unit分别是percent和count。原生分布保留包括有限失败哨兵在内的存储值，failure_handling明确说明其口径。




506曾按两次Monte Carlo结果逐点相等断言，观察到2.3792e-6 waves差异；此记录保留，507改为两次试验分别对照同一解析分布，采用原数值容差。Cooke零扰动差异仍开放。证据：TO-01/progress502-uniform.json、progress507-final-readback-uniform.json；501文本确认公开field1对应0度、wavelength1对应0.4800um，未据此改变编号。






这组控制实验显示阶次相关的拟合精度差异。Cooke在VeryHigh下仍保留既有约0.0303423waves差异，需要受控折射模型或正式拟合定义继续区分；整体状态implemented。549/550各1诊断测试通过表示独立参考与状态/关闭检查完成，其中Standard三项数值失败明确保留。八次QuickYield均关闭、两会话断连，曲面/solve/系统/MFE/MCE/TDE保持。详见TO-01/progress550-high-order.json。



固定第6面半径后，活动源模型参考与QuickYield也通过原门槛，最大差6.904929e-7 waves。569原三波长与逐一单色化实验中，原主波长和三个单色情形均通过；该实验首先指向主波长相关solve。570动态控制通过，固定控制首次因缺少replace_solves而被保护拒绝，571显式替换后通过。全部原始差异与失败保留。

折射控制采用N-BK7平凸透镜、10mm入口瞳、6mm净半口径和0/3度、0/6度两组视场。64×64均面积瞳点独立OPD RMS去除活塞及最小二乘线性瞳倾斜后，与Standard/VeryHigh均通过1e-5 waves+1%参考值；八组最大差6.361863e-5 waves。原始仅去活塞RMS另列，离轴差值保留。572首轮6度的5mm孔径截断15/4096条光线，573扩大声明净孔径后全部光线有效，两项通过。这里记录受控数值等价关系，原生专有重建算法仍按手册定义。
