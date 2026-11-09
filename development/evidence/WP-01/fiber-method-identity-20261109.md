# 光纤专题计算方法归属修复与原生复验

日期：2026-11-09。条目WP-01.FiberCouplingSettings，D001。源码0.1.62工作树；OpticStudio 24.2.0 build240529 PremiumEdition；本机Python3.14。

## 声明范围与实现

修复原生光纤报告计算方法被硬编码标记为Huygens的问题。parse_fiber_coupling_text新增integration_method和integration_method_source，以首个非空标题识别huygens/ray_based；未声明时为null。正文提及Huygens不能确定计算方法。请求仍为kind-only，不新增未经确认的设置。

正式依据为本机2024 R2手册894—897页，摘录位于.local/evidence/development/WP-01/fiber-manual-20261109。已核对NA、去心、角度、波长、场、采样和积分方法定义。现有AS_Default未给出专用选择成员；已查MODIFYSETTINGS材料未取得专用设置键。

## 执行和结果

相关普通98项通过，XML：.local/evidence/development/WP-01/fiber-method-unit-20261109.xml。包含五个标题/来源归属测试。

原生命令：设置COMPLUS_LoadFromRemoteSources=1后，执行`.venv/Scripts/python.exe -m pytest --run-zemax -q tests/native/test_polarization_topic_reference_live.py::test_fiber_topic_method_identity_and_reload --junitxml=.local/evidence/development/WP-01/fiber-method-native-20261109.xml`。1项通过，11.97秒。

输入为本机Cooke样例工作副本，请求fiber_coupling_settings；实际标题为光纤耦合效率-惠更斯积分法，integration_method=huygens。源效率1.0，接收效率0.148061，总效率0.148061；接收NA X/Y为0.1，去心和角度为0。该次验证数值为原生报告值，未新增耦合效率独立参考结论。

原始请求、结果、分页、设置/曲面与保存重载记录位于.local/runs/runs/fiber_topic_method_653e3ada46。任务成功；保存重载及模型保持检查通过；disconnect响应ok=true、connected=false。

## 剩余动作

保持implemented；专用source/receiver选择、采用回读及同条件独立复场参考仍待完成。取得正式选择入口后将专用NA/偏移/倾角与既有POP接收场参考对应。完整验收计数保持4/10。
