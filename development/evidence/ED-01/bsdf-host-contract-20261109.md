# D007 BSDF：正式目录与LDE/NCE选择器对照

日期2026-11-09；源码0.1.62，101工具/132分析；原生24.2.0 build240529 PremiumEdition。主仓.venv，COMPLUS_LoadFromRemoteSources=1，原生串行。

## 范围、假设和正式接口

ED-01.Scattering.BSDF声明范围为顺序曲面BSDF文件、参数、追迹和保存重载。本轮检查资源真实目录、Application.UpdateFileLists与System.UpdateFileLists后，LDE和NCE是否返回同一可用集合；再检查显式正式接口转换能否解除顺序设置对象的同名成员问题。

正式IZOSAPI_Application的ZemaxDataDir/ScatterDir/UpdateFileLists；LDE ISurfaceScatteringBSDF的FileName/GetAvailableFileNames；NCE IOSS_BSDF的ReflectFile/TransmitFile/GetAvailableFileNames。第二轮显式调用对应接口构造器包装原生对象。

原生实际ScatterDir为`C:/Users/tonge/Documents/Zemax/ScatterData`，已有17个.bsdf。输入BrownVinyl.bsdf，来自该目录的既有安装样例，记录文件首部；本轮没有改写这些资源。两个模式均使用自有新建工作模型；LDE面1及NCE RectangularVolume为MIRROR。

## 实际结果

| 条件 | LDE | NCE |
| --- | --- | --- |
| 应用及系统刷新后列表 | 仅“无” | “无”及17个真实.bsdf |
| basename设置并提交 | FileName为“无” | ReflectFile/TransmitFile均为BrownVinyl.bsdf |
| 显式正式接口，basename | 仍仅“无”、未采用 | 文件列表及采用均成立 |

第一轮另测NSC绝对路径：setter回读“无”，提交返回true，活动模型的_S_BSDF为null；读取随后抛AttributeError。保留此探针异常，未将返回true视为成功。第二轮以concrete/formal_interface两个路由重复basename对照，四案例均取得最终回读，排除本组输入下通过显式接口转换解除LDE缺口的假设。

NSC选择成功证明本机资源可由该正式选择器识别；顺序BSDF范围仍缺实际文件采用。本轮为选择器行为探查，无新增散射角分布或功率数值通过结论，原门槛保留。NCE结果没有替代顺序曲面验收。

## 命令、原始结果及关闭

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/ED-01/bsdf_host_contract.py .local/evidence/development/D007/bsdf-host-contract-20261109
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/ED-01/bsdf_host_contract.py .local/evidence/development/D007/bsdf-interface-contract-20261109
```

第一轮脚本测basename/绝对路径；当前脚本演进为第二轮的concrete/formal_interface两路，原始请求保留在各probe.json。探针记录完整列表、实际目录、源文件首部、设置回读和关闭回执。

相关属性、散射能力/结果及开发状态普通检查73 passed，1.22秒，XML为`.local/evidence/development/D007/bsdf-interface-contract-20261109/unit.xml`。

两进程退出码0，shutdown检查点成功、native.closed=true、forced=false、error=null；原生既有FRU警告出现。第一轮会话f2c6ceee4d714d6eb3a0d95acd7f85d3；第二轮编号见原始close_receipt。模型为自有新建副本，没有对用户既有模型进行保持比较；保存重载及散射追迹待LDE文件采用后执行。

状态继续blocked。解除条件：取得LDE正式BSDF选择器可枚举并采用真实文件的接口路径或厂商修复；再验scatter_fraction/angle、追迹、重载和关闭。下一项D008报告/制造正式设置；D007已有同条件结果继续沿用。完整验收4/10、剩余92组。
