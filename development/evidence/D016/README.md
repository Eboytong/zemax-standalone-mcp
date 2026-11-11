# D016：双FSM离线闭环稳定仿真

2026-11-11，已完成。入口`run_analysis: fsm_control`；源码1.0.0及当前工作区修改，Windows x64/Python3.14/OpticStudio24.2.0 build240529 Premium。

## 实施与输入

在独立系统副本上使用两个CoordinateBreak/平面镜/反向CoordinateBreak三联面，四个镜面倾角自由度、两个固定物理观测平面。正式参数写入后回读；返回面的变换顺序为1，前面的顺序为0。原生差分追迹建立4×4控制响应与输入位置/斜率响应矩阵，检查秩和条件数，再执行显式周期、延迟、执行器时间常数、限幅和测量噪声的离散积分控制；每步重新原生追迹，保存线性化误差。物理时间取请求参数，API耗时独立记录。

受控模型两镜间50mm，观测面沿出射方向距第二镜50/100mm，输入面到观测面自由传播长度110/160mm。扰动[0.01,-0.005,0.0001,-0.00005]采用mm和方向斜率；20步、周期1ms、增益0.5、无延迟/噪声、倾角范围±0.1度。解析参考采用反射倍角、杠杆长度及自由传播；无噪声残差按初值×0.5^k衰减。

## 检查与结果

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_fsm_control_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d016-final --junitxml=.local/evidence/development/D016/final.xml
```

最终原生1 passed/28.34秒，相关普通105 passed/4.27秒。128次数值对照最大绝对差1.5031805408e-10；响应矩阵无穷范数条件数25。按1e-6mm位置门槛，稳定时间0.015s；最后两观测面的最大残差4.9591064e-8mm，最后出射斜率[1.90088187e-10,-9.60809625e-11]。逐步原生与线性预测最大差1.5031805424e-10mm。差分步长减半的16项对照、80项解析衰减对照和32项反射杠杆对照通过。

另覆盖1步延迟、1ms执行器时间常数、种子17的1e-8mm噪声、限幅导致的未收敛、观测面重合导致的秩不足、非法编号、实际取消、分页及PNG。源模型/修订保持，成功/失败/取消均关闭副本，最后正常disconnect。PNG已查看，四条残差曲线按预期衰减。

原始记录`.local/runs/runs/fsm_control_748203142c`包含calls/checks/result及fsm.png；测试输出`.local/evidence/development/D016/final.xml`和final.txt。首次探针将Integer类型的变换顺序按Double读取失败，已改用正式单元格类型读取；原始失败native.xml/txt和后续probe记录保留。

用户说明`docs/topics/analysis/fsm-control.md`，请求`examples/requests/fsm-control.json`。下一项：D015用户成本函数与原生公差候选工作流。
