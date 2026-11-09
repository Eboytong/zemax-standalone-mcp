# 相位传播分离与全瞳透射数值控制

2026-11-09，主仓源码0.1.62工作区，Python为主仓.venv，COMPLUS_LoadFromRemoteSources=1。原生OpticStudio24.2.0 build240529 PremiumEdition，执行串行。本记录接续[首轮控制](controls-20261109.md)。

## 相位传播实验

计划：在Cooke轴上平行入射条件，用正式逐面归一化追迹位置、GetGlobalMatrix和GetIndex构造独立几何光程，比较复场相位/传播相位/原生偏振相位的符号组合；沿用1e-6度即2.7777777777777776e-9 waves门槛。

入口：`scripts/probes/PO-01/phase_propagation_reference.py`。命令：`python -B -X utf8 scripts/probes/PO-01/phase_propagation_reference.py .local/evidence/development/PO-01/phase-path-20261109`。

401点×两方向，保留逐面矩阵、前一介质折射率、原生返回数量、逐点总光程和相位。模型设置与曲面逐项结果保持。shutdown回执native.closed=true、forced=false、native.error=null。

直接采用ray-minus-chief与两种传播符号的误差仍超限。对保存的原始点做反向native符号诊断，raw+propagation+native这一组合的弧矢/子午最大余数误差分别2.499509153593843e-7和2.5001445071084344e-7 waves，较直接复场对照缩小，仍超原门槛。四种组合存于sign-diagnostics.json；完整点值保留在probe.json。两方向X主光线为零振幅，标记indeterminate。

后续探针代码把反向native符号作为独立诊断字段保留，原门槛和原始比较不变。其几何算法由合成已知传播/偏振相位和跨周期样例测试，3项通过；联合既有控制测试51项通过。本次尚未定位剩余约2.5e-7 waves偏差，不能据此完成相位数值验收。

## 全瞳透射独立参考

计划：创建独立无镀膜平行平板，模型玻璃Nd=1.5、Vd=60、dPgF=0、波长.5876µm，检查正常入射两界面Fresnel透射；分别执行X/Y偏振和非偏振。原生全瞳32×32与自有32×32像素中心圆瞳采样分别计算；在该通量恒定模型中检查结果对应。

命令：`python -B -m pytest tests/native/test_transmission_pupil_reference_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/transmission-pupil-20261109 --junitxml=.local/evidence/development/PO-01/transmission-pupil-20261109.xml`。

1 passed in14.37s。原始调用和检查：`.local/runs/runs/transmission_pupil_reference_5f46d635dc/`。独立参考`(1-((1.5-1)/(1.5+1))**2)**2=0.9216`。10项数值检查均通过：原生0.921599997，批量均值0.9215999971122092，主光线最终值0.9216；所有检查最大绝对误差3.000000026176508e-9。

Fresnel比较预设atol=1e-6/rtol=1e-6，原生与批量比较atol=1e-8/rtol=1e-7。验证偏振报告Jones、非偏振模式、瞳网格、逐面主光线、批量行数/状态、系统设置和曲面恢复，执行后真实stdio断开。

此控制验证常量全瞳通量。仍需正式视场/波长/采样选择路径、非恒定瞳通量、渐晕/镀膜/吸收组合及完整声明生命周期；Transmission保持in_progress。新增完整验收0，累计3/10。
