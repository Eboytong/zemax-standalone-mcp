# D021 原生设计去敏感化证据

OpticStudio24.2.0/build240529 Premium Standalone，Python3.14，真实stdio原生验收通过。运行时`SEQOptimizationWizard2.IsHighManufacturingYieldAvailable=true`；实际启用`OptimizeForManufacturingYield=true`，RMS波前、Centroid、高斯求积3环，制造良率权重1。

受控系统为N-BK7球面单片，0.55µm、2mm入瞳，固定像面厚度均匀公差±0.2mm。变量为两曲率和像距，DLS 10周期；名义约束为RMS Spot≤0.01镜头单位，公差准则阈值0.002，Uniform分布。前后设计采用相同公差行、分布、seed 42和validation seed 314159。

原生灵敏度准则为RMSSpotRadius。估计变化RSS从0.002904037317990438降至0.001885838824374764，下降35.0615%。优化名义值1.083174161e-9，通过0.01约束。固定随机种子的64次筛选中，基线0/64、优化后64/64通过；独立256次验证中，基线0/256、优化后256/256通过。优化后验证均值8.971523678e-4，5/50/95百分位为9.122981082e-5、8.711501219e-4、1.708622656e-3。独立256次验证的95% Wilson区间：基线[0, 0.014783856425871423]，优化后[0.9852161435741286, 1]。64次筛选区间分别为[0, 0.05662405979280531]和[0.9433759402071946, 1]。

源系统、TDE和MFE恢复与初始读取一致；保存优化模型，重新载入后进行优化设计灵敏度和Monte Carlo。stdio正常断开。普通合同及灵敏度聚合测试20通过，见`ordinary.xml`；原生命令及结果见`native.xml`及`.local/runs/runs/d021_desensitization_f0eebb60e7/`。

失败、预算与取消原生用例通过：预算0.001秒返回BUDGET_EXCEEDED；变量起点在60—100范围外返回INVALID_ARGUMENT；活动原生子任务取消取得cancelled。每轮曲面、MFE、TDE、MCE均与基线一致，正常disconnect。native-lifecycle.xml记录1通过、20.91秒；原始目录.local/runs/runs/d021_failure_budget_cancel_03302f7e93/。D021完成制造良率向导这一正式路线的交付，实际许可标志及采用设置已保存。
