# 已有扩展资源查询与历史宿主记录

当前后续开发范围见[原生计划](../../../development/current.md)。自定义宿主、回调、COM、任意宏执行及新增宏/DLL接入的计划已[归档](../../../development/archive/scope-native-only-20261108/README.md)。本页说明现有调用及历史执行结果。

## 已有资源查询

`get_system_resources`支持`kind=extension_files`，通过`extension_role`选择资源：

```json
{"request":{"kind":"extension_files","extension_role":"user_analysis","query":"Sample","start":0,"count":20}}
```

资源角色包括surface、source、object、surface_scatter、bulk_scatter、physical_optics、gradient_index、birefringence、diffractive、user_analysis、user_operand、extension、library和zpl。使用原生应用的ZemaxDataDir/ZPLDir，返回目录、存在状态、过滤后的文件名、总数及下一页。目录查询错误保留原因；缺目录返回空列表及`directory_exists=false`。

历史真实stdio验收覆盖14个角色、分页、模型状态保持及正常断开，独立安装包复测通过。查询创建零个原生分析/工具，修改零项模型状态。证据见`.local/evidence/development/EX-01/resource-followup045-tests.xml`及历史发行记录。

## 宿主与宏的历史状态

受控.NET回调曾编译成功，但原生LoadNETCallback返回null；宏进程曾返回退出码0，但没有可归属宏输出。相关条目保留其原始失败状态和输入，记录见[移出操作台账](../../../development/archive/scope-native-only-20261108/operations.csv)、[移出分析台账](../../../development/archive/scope-native-only-20261108/analyses.csv)及[原专题快照](../../../development/archive/scope-native-only-20261108/extensions-topic.md)。

已完成的Universal Plot和GridSag宏solve沿用历史实现及证据。当前原生功能的后续动作由[剩余排序](../../../development/remaining-ranked.md)和[当前交接](../../../development/handoff.md)维护。
