# 原生评价函数构建

`run_merit_program`支持在独立系统副本中预览、求值及应用评价函数。默认`apply=false`，返回逐操作数`rows`；`apply=true`保留恢复检查点并采用生成模型。

```json
{"request":{"apply":false,"targets":[{"kind":"opd","reference":"mean_remove_tilt","configuration":1,"wavelength":1,"hx":0,"hy":0.5,"rings":4,"arms":16,"target_waves":0,"scale_waves":0.1,"weight":1}],"constraints":[{"operand":"CTGT","surface":1,"target":2,"scale":1,"weight":10}]}}
```

`reference`取`chief_ray/mean/mean_remove_tilt`，对应连续原生OPDC/OPDM/OPDX组。OPD为waves，配置/波长编号从1起。归一化视场Hx/Hy各为−1至1；瞳节点覆盖完整2π方位。径向采用`u=r²`的Gauss-Legendre积分，`obscuration`为中心遮拦半径比例。返回完整节点及面积权重，组与组以原生分隔和CONF选择隔开。

每行权重为`面积权重×请求权重/scale_waves²`。`groups`返回波前残差RMS及归一化平方贡献；`native_merit`采用OpticStudio自身的总权重归一化。`constraints`返回实际值、超限量和尺度化贡献。厚度和EFL单位为镜头单位，CVGT/CVLT为镜头单位倒数。

常规RMS可通过`wizard`传入现有[原生优化向导](../topics/analysis/design-tools.md)设置；实际支持字段见`get_capabilities(topic="tool",tool_name="run_merit_program")`。有渐晕的自定义节点会保留原生失败结果；可用原生向导的删除渐晕选项配置常规目标。

向导的配置开关与编号按完整设置组合回读；指定单配置时同时传入对应编号。自定义OPD目标按每16个节点分步写入、回读，状态查询和取消可在批次之间执行。保存的`wizard_settings`、`groups.nodes`及逐行结果可用于复算。
