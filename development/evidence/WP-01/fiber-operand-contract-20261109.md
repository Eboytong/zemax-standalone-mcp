# FICL正式参数、可选择调用及真实stdio验收

日期：2026-11-09。条目WP-01.FiberCouplingSettings，D001。源码0.1.62工作树，Python3.14，OpticStudio24.2.0/build240529/PremiumEdition。当前发行包沿用0.1.62，本次未构建安装包。

## 声明与接口

完整光纤专题含源/接收NA、椭圆分量、偏移、角度、对准及同条件复场参考。本次交付正式FICL可选择子范围，整项保持implemented。

依据为本机2024 R2手册印刷页1116—1117，原文索引`.local/evidence/development/EXT-EXPORT/manual042.txt`。实际签名为GetOperandValue(MeritOperandType,Int32,Int32,Double,Double,Double,Double,Double,Double)。临时FICL行八列依次为采样、波、视场、忽略源光纤、Sna、Rna、数据、偏振；前四和后两列Integer，NA两列Double。

原生探针`scripts/probes/PO-01/fiber_operand_contract.py`在Cooke工作副本上执行六条件×六数据模式，共36次直接查询与36次临时行计算。临时行finally移除，原评价函数、系统设置和曲面读取一致。实际请求和逐次回读位于`.local/evidence/development/WP-01/fiber-operand-contract-20261109/probe.json`。

## 实现

fiber_coupling_settings增加method=auto/native/operand。默认调用保留专题文本；显式参数auto采用FICL；native显式参数拒绝。参数为sampling32/64/128/256（按手册采样码1—4）、field/wavelength正整数、ignore_source、有限正source_na/receiver_na、integration=fast/huygens及use_polarization。此次原生验证采样64，其他采样仍需后续数值覆盖。

生产路径直接查询，不创建或修改评价函数行。返回功率、复振幅、原生调用参数、系统视场/波长身份、配置、来源及三行分页结果。三次查询之间设取消边界，沿用复合任务终态与错误保存。公开schema、能力说明及请求示例已同步。

真实stdio发现并修正两个接入问题：默认字段展开改变auto路由；默认专题被通用Field/SampleSize/UsePolarization写入流程误处理。原始失败XML保留，最终两用例通过。

## 结果、参考与容差

Cooke波长1=.48µm、波长2=.55µm。64×64、轴上、忽略源、接收NA=.1、无偏振：波长1快速0.07955359608159027，Huygens0.07685026102244516；波长2快速0.15061707631265225，Huygens0.14806083709504725。后者与专题文本0.148061差1.6290495275e-7，通过按六位小数舍入预设5e-7门槛。

波长1接收NA=.05的Huygens值0.044284255116349716；偏振开启为0.07283528788417001；视场2为0，作为本次原生返回值保留。源位于无穷远，启用源且sourceNA=.05未改变结果，此条件未证明有限共轭源NA采用。

全部直接/行结果逐项相等。功率与复振幅模方残差最大4.52e-17，属于一致性检查；独立解析/POP复场参考尚待完成。

## 命令、状态和关闭

进程环境COMPLUS_LoadFromRemoteSources=1。命令入口均使用项目`.venv/Scripts/python.exe -B -X utf8`：

- 探针：`scripts/probes/PO-01/fiber_operand_contract.py .local/evidence/development/WP-01/fiber-operand-contract-20261109`。
- 最终普通：pytest定向执行fiber_coupling_settings、fiber_operand、phase_aberration、polarization_ray_trace、polarization_transmission、transmission_pupil六文件，127通过，1.24秒；XML为`.local/evidence/development/WP-01/fiber-operand-unit-final-20261109.xml`。
- 串行原生：`-m pytest --run-zemax -q tests/native/test_polarization_topic_reference_live.py::test_fiber_operand_selection_paging_reload_and_cancel tests/native/test_polarization_topic_reference_live.py::test_fiber_topic_method_identity_and_reload`，2通过，22.80秒；XML为`.local/evidence/development/WP-01/fiber-operand-native-r3-20261109.xml`。
- schema：`scripts/development/export_tool_schemas.py`，正常退出。

真实stdio原始调用/结果分别在`.local/runs/runs/fiber_operand_3152b5ff32`及`fiber_topic_method_284f84c5c8`。覆盖默认专题、参数选择、功率/振幅、rows分页、保存重载、取消请求、后续复用及系统/曲面/评价函数保持。取消时允许已完成状态，精确取消边界另由普通测试验证。两会话disconnect成功，connected=false；关闭回执native.closed=true、forced=false、error=null。独立探针也正常关闭。原生FRU警告按原样保留。

## 结论与下一步

已取得并接入正式可选择的FICL路径。保持implemented，完整计数4/10、剩余92组。下一步：建立有限共轭源NA控制与解析高斯束/POP独立参考；为椭圆NA、去心、倾斜及对准寻找有正式依据的路径，逐项记录覆盖关系。取得完整范围及生命周期证据后再判定整项完成。

## 独立参考追加控制

2026-11-09新增理想Paraxial薄透镜控制：f=100 mm，圆形入口半径0.5 mm，轴上、空气、0.55 µm。解析参考对接收端及有限源端高斯角谱在瞳面作复振幅重叠面积分；积分结果与独立20,000区间径向中点求积普通测试最大差低于2e-9。FICL与解析参考使用绝对门槛5e-4，不含相对项。脚本及原始逐点记录在`scripts/probes/PO-01/fiber_gaussian_reference.py`及`.local/evidence/development/WP-01/fiber-gaussian-native-20261109/probe.json`。

27组真实stdio快速积分检查覆盖忽略源/有限共轭源、NA倍率0.5/1/2及64/128/256采样，最大绝对误差4.79537e-4，全部通过；模型设置和曲面保持，disconnect成功，native.closed=true、forced=false。终端记录为`.local/evidence/development/WP-01/fiber-gaussian-stdio-20261109.xml`，MCP调用及检查为`.local/runs/runs/fiber_operand_reference_46eed519dd`。独立公式及其20,000点校核共5项普通测试通过。

相同几何下Huygens 256/512/1024采样仍未达到该参考门槛：24项最大偏差约0.06229；继续至最高采样后相应有限共轭控制的偏差仍约0.02913。完整逐点结果位于`.local/evidence/development/WP-01/fiber-gaussian-native-20261109/probe.json`及`.local/evidence/development/WP-01/fiber-huygens-sampling-20261109/probe.json`，后者6查询均记录，设置、曲面、评价函数保持，任务正常关闭。解析参考为几何薄透镜标量近轴高斯模型，未建模Huygens的波动传播及原生积分权重；该差异目前归属为参考条件/积分定义未匹配，不能据此判定原生算法错误。下一步取得同定义Huygens出口场参考，或保留此项为待验证模式；不放宽5e-4门槛。

本次普通汇总127项、参考测试5项通过；两项既有真实stdio检查通过，独立参考真实stdio检查1项通过。完整整项仍未完成，椭圆NA、去心、倾斜/对准范围及Huygens同定义参考继续待验。
