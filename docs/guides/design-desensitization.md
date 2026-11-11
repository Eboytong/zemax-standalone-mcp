# 固定公差的设计去敏感化

`run_analysis`的`design_desensitize`读取当前TDE，保持公差幅度，以原生制造良率向导构建目标，通过DLS改变设计变量，再对原始和优化设计运行相同条件的灵敏度及Monte Carlo。运行前保存工作模型、设置制造公差，并用`get_optimization_wizard_options`检查制造良率功能的实际可用性。

```json
{"request":{"kind":"design_desensitize","variables":[{"surface":1,"cell":"radius","minimum":45,"maximum":100},{"surface":2,"cell":"radius","minimum":-100,"maximum":-45},{"surface":2,"cell":"thickness","minimum":40,"maximum":90}],"merit":{"wizard":{"kind":"sequential","criterion":"Wavefront","type":"RMS","reference":"Centroid","use_gaussian_quadrature":true,"rings":3,"optimize_for_manufacturing_yield":true,"manufacturing_yield_weight":1},"constraints":[{"operand":"EFFL","target":75,"weight":10}]},"threshold":0.002,"maximum_nominal":0.01,"sampling":1,"screening_samples":64,"validation_samples":256,"seed":42,"validation_seed":314159,"budget_seconds":600}}
```

此例对应0.55µm、2mm入瞳、半径±50mm的N-BK7单片及面2厚度公差±0.2mm；将面号、变量边界和准则阈值按当前模型设置。半径边界保持同号；变量起点须位于边界内。TDE需要至少一条活动制造公差，分布由请求统一指定。`criterion`默认`RMSSpotRadius`，其数值单位为镜头单位，`criterion_unit`为输出单位标签。

默认筛选64次，独立验证256次，两个随机种子必须不同。`threshold`决定Monte Carlo通过率；`maximum_nominal`限制名义性能；`minimum_sensitivity_reduction`默认0.1，以各公差原生估计准则变化最大绝对值的RSS比较前后设计。

结果返回`wizard_settings`、实际MFE、固定TDE、灵敏度前后值、四组统计、分位数和95% Wilson区间。`summary.saved_model`为独立重载并复算的优化模型；`summary.nominal_passed`及`sensitivity_passed`按请求判断。`rows`分页保留筛选/验证统计及样本。源模型、MFE、TDE和配置在成功、失败及取消后恢复；读取任务终态和`restoration`确认完成。

受控单片案例的RSS下降35.0615%，独立验证通过率由0/256提高至256/256；这些结果对应上述模型和公差。实际设计返回自身的性能、良率和置信区间。
