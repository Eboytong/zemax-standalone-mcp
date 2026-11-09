# MaterialModel环境刷新与独立空气参考

日期2026-11-09。D002/ED-02.MaterialModel.Material；源码0.1.62工作树，Python3.14，OpticStudio24.2.0 build240529 PremiumEdition。接续environment-model-controls-20261109.md，原Nd/Vd门槛保持。

## 计划、输入与正式接口

原C3温度10°C结果与20°C完全相同；本轮区分缓存未刷新和模型环境规则。独立新模型，N-BK7及MaterialModel(Nd1.6、Vd60、dPgF.001)，波长.5875618/.4861327/.6562725µm，环境修正开启。四种环境为10°C/1atm、30°C/1atm、20°C/0atm、20°C/.8atm。

每项记录设置后、正式IOpticalSystem.UpdateStatus()后及save_lens_as/open_lens重载后的全精度ILDE.GetIndex、solve和上下文。反射未创建应用，正式方法清单保存在.local/evidence/development/ED-02/environment-refresh-20261109/interfaces.json。

## 执行与结果

普通初轮38项通过，unit.xml。原生命令为`COMPLUS_LoadFromRemoteSources=1`后执行`.venv/Scripts/python.exe -B -X utf8 scripts/probes/D002-MODEL_GLASS/environment_refresh.py .local/evidence/development/ED-02/environment-refresh-20261109/native`。

两种材料共8个环境用例、24个波长值。全部UpdateStatus前后及重载前后最大变化均0，排除本轮条件下的缓存/重载差异。N-BK7随温度和压力改变；模型玻璃温度10/30°C与20°C保持相同折射率，压力变化有效。

诊断候选以实测20°C/1atm折射率为输入锚点，比较系统温度空气修正与固定20°C空气修正，不拟合模型色散。模型玻璃固定20°C候选的12个值最大差4.440892098500626e-16；系统温度候选在10/30°C最大差1.5615112543665433e-5。该对应定位原生行为，正式温度规则仍待厂商依据；不据此完成材料模型验收。

## 独立参考修正

本轮扩大环境范围时发现tests/support/athermal_reference.py::system_relative_index对空气折射率的参考波长使用有偏差：先前按换算波长计算参考空气，手册第119页明确空气公式λ为系统输入波长。修正后分别用系统输入波长计算系统/参考空气，再以二者比值缩放材料色散波长。

原初始12点参考记录catalog-reference.json保留，最大5.894268406692049e-9；未将该失败记为通过。正式手册转录修正后，`.venv/Scripts/python.exe -B -X utf8 scripts/probes/D002-MODEL_GLASS/environment_refresh.py --evaluate .local/evidence/development/ED-02/environment-refresh-20261109/native/probe.json`生成catalog-reference-corrected.json；N-BK7的12点全部通过1e-12，最大4.440892098500626e-16。

对已保存消热差r3再执行athermal_missing_data.py --evaluate：热功率21点结论保持，环境折射率21点最大差从2.1094237467877974e-13降至2.220446049250313e-16。旧参考保存在independent-reference-before-air-formula-correction.json。本次为参考定义修正，未改变原生计算、请求或原门槛。

最终相关普通84项通过，0.64秒，reference-final.xml；覆盖温压请求、区分候选、固定色散与空气归一化、显式热数据要求及材料回读。另有上轮218项对应其实际执行时源码，分别保留。

## 生命周期与剩余条件

probe.json中error为空，settings_restored=true、surfaces_restored=true、cleanup_failures=[]、disconnect.connected=false；所有8次保存重载完成，正式UpdateStatus返回及solve实际值均保存。未创建并行原生实例，FRU警告原样保留。

MaterialModel保持implemented。物理d/F/C谱线下的Nd/Vd仍沿原失败记录，dPgF独立参考和完整失败恢复待完成。取得模型完整色散/环境算法或厂商定义后继续；下一项为Gradium capping参数写入顺序控制，避免重复同条件材料矩阵。
