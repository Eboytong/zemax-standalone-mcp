# D005 POP光纤对准、寻优与容差

日期2026-11-11。主仓C:/Users/tonge/Desktop/mcp，源码fc814ef及当前工作区修改，主仓.venv/Python3.14。OpticStudio24.2.0/build240529、PremiumEdition。发行基线1.0.0；源码102工具、135种分析请求。新增run_analysis:fiber_alignment。

## 声明范围、请求与原生设置

AstigmaticGaussian原生复场接收器，X/Y偏心参数4/5、Z联动束腰位置2/3、倾角TiltAboutX/Y；束腰半径参数0/1。支持1/2维扫描、五轴有界坐标模式搜索、固定其余分量的1/3dB损耗交点、范围状态、粗细采样变化、最佳候选ZOS及完整run_pop请求。复用原生POP耦合积分；每次候选记录实际设置、子任务、配置、修订、功率和关闭结果。数据支持rows分页、均匀网格区域分页和PNG导出。非均匀扫描坐标显式记录。

原生接收场在固定POP输出平面评价，Z改变接收模式束腰位置；光学模型为只读，接收参数属于各自关闭的原生分析对象。成功/失败/取消保持曲面和solve。最佳ZOS与请求保存后恢复工作文件名。

## 受控模型与数值参考

平面零程系统，N=1，波长0.55µm，圆高斯束腰w=0.1mm，功率1W。窗口1×1mm，128²，再以256²复算最佳点。五轴对照：横移±0.1mm、离焦±60mm、倾角±0.1度及中点。独立参考分别为exp[−d²/w²]、1/[1+(z/2zR)²]、exp[−(πw sinθ/λ)²]，zR=πw²/λ；效率绝对容差5e−4，最大误差1.1206042904166047e−6。

有符号位置对照：输入AstigmaticGaussian束腰位置X/Y=+5mm、偏心(0.023,−0.017)mm，接收同位置时效率0.9999999999999853。输入为束腰偏心(0.023,−0.017)mm的另一模型：扫描5×5细网格后，边界±0.1mm的X/Y模式搜索，得到(0.023046875,−0.017187500000000005)mm、效率0.999996264655409。搜索步长终止条件满足，总评价129次。

容差切片步长0.01→0.005mm，1dB宽0.09592980188137891mm（解析0.09597051824376163），3dB宽0.166197015188215mm（解析0.16622581362691102）。相对解析误差约0.0424%/0.0173%，预设门槛0.5%；粗细宽度变化0.3180%/0.07365%。最佳模型及配套请求重载效率完全相同；128²→256²效率差2.4758e−14。

## 检查、错误与生命周期

主用例真实stdio1 passed，112.16秒；失败/预算用例真实stdio1 passed，16.37秒。主用例34数值断言通过。普通定向71 passed，0.77秒，覆盖边界、模式参数、角度、姿态映射、括区、缓存、有界寻优、二维方向、错误和取消。

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_fiber_alignment.py tests/unit/test_pop_input_cleanup.py tests/unit/test_pop_dll.py tests/unit/test_fiber_coupling_settings.py tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d005-final
.\.venv\Scripts\python.exe -B -m pytest tests/native/test_fiber_alignment_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d005-native
```

主记录 `.local/runs/runs/fiber_alignment_native_8ce83817cc/{calls.json,checks.json}`；失败/预算记录 `.local/runs/runs/fiber_alignment_failure_budget_7d207626ba/calls.json`。非法视场保留INDEX_OUT_OF_RANGE，模型保持且后续调用成功；评价上限2次保留候选并报告evaluation_or_time_budget。实际取消进入cancelled，所有原生POP子任务关闭；前后曲面/solve一致，guarded及常规disconnect成功。alignment.png已导出并查看。

设置探查和七点复算还保存在 `.local/evidence/development/D005/` 及 `.local/runs/runs/fiber_alignment_probe_065758fda9/`。初次直接运行探查脚本读取了已安装包，输出在.venv/Lib/.local；随后显式设置主仓src/root的PYTHONPATH复算，以上原生pytest通过conftest和stdio显式导入主仓源码。首次探查收尾参数错误已修正；原始记录保留。

## GitHub参考与结论

参考G5固定commit6a197e467c7fceeb51ab651b3dbea21d9781d94e的confocal_tools.py中的流程组织；本项目使用原生POP复场及原生接收积分，独立编写扫描、搜索和损耗交点，未复制代码。请求示例、schema、能力说明和使用指南已同步。D005声明范围完成，下一项D006固定膜系多条件优化。

## 早期接口探查记录

# D005 POP光纤对准与容差：接口探查

2026-11-10，OpticStudio24.2.0/build240529，主仓.venv/Python3.14，主仓源码。正式PhysicalOpticsPropagation设置对象具备FiberType、FiberPosition、TiltAboutX/Y、ComputeFiberCouplingIntegral、GetFiberParameterName/Value及SetFiberParameterValue。

AstigmaticGaussian六参数按原生回读：0束腰X、1束腰Y、2束腰位置X、3束腰位置Y、4偏心X、5偏心Y。GaussianWaist八参数：束腰X/Y、偏心X/Y、孔径X/Y、阶数X/Y。因此轴向扫描采用AstigmaticGaussian两个束腰位置联动，横移采用4/5，倾角采用原生TiltAboutX/Y。后续先用解析高斯复场验证符号、模式半径及重叠，再接入一/二维扫描、有界局部寻优、1/3dB交点和最佳模型/请求独立保存。

原始探查：.local/evidence/development/D005/probe_settings.py及settings-probe.json。分析工具finally Close，最终disconnect成功；首次探查的收尾脚本参数漏传已修正，保留原终端错误。原生退出输出FRU__delta_init警告，正式调用及断开返回成功。

状态in_progress；下一步定义有类型扫描/寻优请求、设置映射和数值参考，复用run_pop及其复场耦合结果。
