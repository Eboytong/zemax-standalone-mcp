# 扩展资源与宿主入口

## 0.1.46 原生复测

扩展资源发现已通过真实 stdio 验收全部 14 个角色，包括原生目录、分页、查询前后系统设置/曲面/修订号保持及正常 disconnect；独立安装包复测通过。EX-01.ResourceDiscovery 标为 done。

受控 ScalarCallback 编译后实际调用 LoadNETCallback，返回 null；应用正常关闭，没有返回回调实例，Execute 和回调 Dispose 未到达。EX-01.NETCallback 保持 blocked，下一步核对正式加载器的程序集/类型约定及宿主诊断，取得可加载受控输入后继续设置和数值验收。

原始失败 JUnit 为 .local/evidence/development/BASE-04/reboot-followup046.xml；完整执行记录及保留产物见 reboot046.json 和 reboot046-evidence/。下文“等待启动恢复”属于 0.1.45 历史状态。

`get_system_resources` 新增 `kind=extension_files`，需要指定 `extension_role`：

```json
{"request":{"kind":"extension_files","extension_role":"user_analysis","query":"Sample","start":0,"count":20}}
```

支持 surface、source、object、surface_scatter、bulk_scatter、physical_optics、gradient_index、birefringence、diffractive 九类 DLL，以及 user_analysis、user_operand、extension、library 和 zpl。查询使用当前原生应用的 ZemaxDataDir/ZPLDir，返回目录、存在状态、过滤后的文件名、总数和下一页。输入角色由枚举约束；目录查询错误保留原因。缺目录返回空列表及 `directory_exists=false`。

文件发现为后续原生消费者提供候选。DLL、用户分析及操作数的选择、参数和执行采用状态由对应原生设置或执行入口确认。查询自身创建零个原生分析/工具，修改零项模型状态。

本机官方 `SampleAnalysis1.cs` 使用 `ConnectToApplication()`，区分 UserAnalysis 与 UserAnalysisSettings 模式；`CSharpUserOperand_16_SumAbsoluteThickness.cs` 要求 Operand 模式。本服务当前创建 Standalone 实例。宿主运行条目需要接通正式的分析/操作数启动机制、状态和终止协议，再验收样例输出。

本机还提供 `LoadCCallback/LoadNETCallback`、`RegisterCOperandCallback/RegisterNETOperandCallback`、`ISettingsData` 和 `IZOSAPI_Callback.Execute()`。回调接口继承IDisposable，公开APINetCallback基类提供Dispose、Execute、Clone和Copy；本机反射已确认这些成员。取消接口仍未发现，宿主加载、设置传递及Dispose实际行为由独立最小用例确认。

ZPL solve 已沿 `update_surfaces` 的 `mode=zpl_macro`、`get_system_resources.kind=solve_macros` 实现选择与回读；独立任意宏运行仍需确认正式启动入口及生命周期。

各操作的状态、具体接口、样例路径和解除条件见 `.local/evidence/development/EX-01/probe036.json` 与 `development/ledgers/operations.csv`。资源发现已实现；宿主/回调条目保留 blocked。连接恢复后先运行 `tests/test_extension_resources_live.py`，核对实际根目录、分页和模型状态，再运行官方宿主最小用例。

## 0.1.45 .NET回调受控输入

已结合官方2024 R2 APINetCallback参考与本机ZOSAPI.dll/Interfaces.dll反射，确认公开抽象基类、无参构造、Execute覆写及继承的IDisposable。此前仅枚举接口声明方法，漏记了继承的释放协议；新记录见.local/evidence/development/EX-01/callback-contract045.json。

受控源码tests/fixtures/net_callback/ScalarCallback.cs已使用本机Framework64 csc编译成功。类名ZemaxMcp.Fixtures.ScalarCallback，读取double设置input，写入output=2*input及fixture标识，成功返回0；缺少输入返回10、非有限输入返回11。Settings属于原生应用创建的ISettingsData，没有继承IDisposable。

无宿主时，静态Transform(1.5)返回3；实例构造在APINetCallback..ctor抛NullReferenceException，没有返回回调实例，未执行Dispose。该结果与编译成功分别记录在callback-build045.json、callback-offline045.json。LoadNETCallback、实际设置读回、Execute及释放仍等待应用创建恢复。

准备的tests/test_net_callback_live.py会编译独立受控DLL，通过正式加载器读取实际Settings、比较output=3（绝对及相对容差各1e-12），并分别记录回调Dispose和应用关闭。该用例已收集，未执行。完成加载与生命周期探查后再接入有类型公开执行请求；EX-01.NETCallback保持blocked。

## 本轮继承接口与输入复核

通过 tests/support/inherited_contract_probe.py 读取安装目录的两份公开程序集，枚举 615 个接口及其继承方法、属性。169 个接口包含额外继承方法，完整记录见 .local/evidence/development/BASE-01/inherited-contracts045.json。IZOSAPI_Callback 的继承释放入口同样适用于 LoadCCallback 返回对象；C 回调的导出函数 ABI、受控输入和实际宿主执行仍缺证据。

应用接口没有继承的注销方法；MCE 继承 IEditor 的行操作及只读属性，未发现独立文件 Load/Save。反射确认 RunCommand(String)；正式应用参考本次读取返回 HTTP 403，未取得任意 ZPL 执行的正式命令和停止协议；继续沿用已有 ZPL solve 入口。

搜索本机安装及用户 ZemaxData 目录，已定位 BSDF 文件，未找到 ISX 文件。该搜索覆盖的具体目录、文件列表和逐项解除条件见 .local/evidence/development/EX-01/contract-followup045.json。BSDF 条目的已有阻塞是文件选择未采用，ISScatterCatalog 仍需 ISX 文件及匹配目录条目。

本轮 28 项启动/探测普通检查和 19 项资源发现普通检查通过；记录分别为 .local/evidence/development/BASE-01/contract-followup045-tests.xml、.local/evidence/development/EX-01/resource-followup045-tests.xml。本轮未创建原生应用，宿主执行与实际释放继续保留原状态。


2026-11-07 ZPL solve收口348：发现EX-01的GridSag9/10待办已由ED-02 acceptance047完成；本轮复测替换两组宏返回值、中文31字符宏名、保存重载、缺资源与超长请求、模型保持和正常关闭。原生1通过，相关普通162通过。正式Setter对照显示ASCII/中文名称31个UTF-16单元可用，32个即便返回Success仍回退Fixed；加入有类型长度前检并更新schema/能力。超长请求在MCP参数验证阶段拒绝，修订和检查点保持。证据EX-01/acceptance348.json。按历史重复范围收口，不增加B004完成数；仍8/10、剩余137组。机械口径/ChipZone宏限制和任意宏执行沿原条目保留。
