# D015：加工成本约束下的公差预算

2026-11-11，已完成。入口`run_analysis:tolerance_budget`。源码1.0.0及当前工作区修改；Windows x64、Python3.14、OpticStudio24.2.0/build240529/Premium。

## 计划与实现范围

有类型输入指定TDE公差行、工艺最小/最大半宽、单位、逆幂成本参数、货币与计价基准、有限候选、性能阈值和目标良率。先原生灵敏度预筛选，再逐候选原生Monte Carlo，按双侧Wilson区间下限判可行并选最低成本；最佳候选使用不同SEED追加独立验证。保留原有补偿器及其他公差，采用统一分布，实际设置与种子回读。源模型、TDE和MFE成功/失败/取消后恢复；预算传至原生子任务。

成本为各项固定成本+变动成本×(参考半宽/候选半宽)^指数。报价与工艺边界由调用者输入，受控验收采用显式数学成本。原有“缺少实际报价”记录已转为具体请求字段，实际项目可直接替换参数运行。

## 受控输入与预定参考

Paraxial焦距50mm、瞳半径1mm、像距50mm、550nm；TTHI为像面前空气间隔。三种半宽0.01/0.05/0.2mm，成本100/20/5 CNY/件；均匀分布，筛选32样本、独立验证64样本，种子42/314159。RMS阈值0.001mm、目标良率80%、置信水平95%。独立解析关系RMS=abs(焦移)/(50×sqrt(2))；成本最低的解析可行候选为0.05mm。保存两个独立样本，以其实际厚度代入公式，并用四条半径sqrt(0.5)的原生光线复算面积平均RMS。数值容差绝对1e-10mm+相对1e-7。

## 命令、结果及生命周期

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_tolerance_budget_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d015-close --junitxml=.local/evidence/development/D015/close.xml
```

最终1 passed/18.19秒，8次数值对照最大差4.6783323743e-17。0.01/0.05mm候选均32/32合格，Wilson下限0.8928208017；0.2mm候选13/32合格，下限0.2551963484。推荐0.05mm、20 CNY/件；64/64独立样本合格，下限0.9433759402。

保存推荐模型并重载公差、两个独立样本解析/光线对照、分页/PNG并查看、实际取消、微小预算失败、非法编号、无可行候选、ParaxialFocus补偿、源模型/TDE/MFE恢复和正常disconnect均通过。补偿原生枚举ParaxialFocus回读为NONSEQNone；按本机枚举值的规范名称核对后通过，原始失败final.xml/txt保留。首次get_tolerances遗漏必填request的探针错误保留native.xml/txt；probe记录首轮成功。

原始输入、请求、结果、检查及图像位于`.local/runs/runs/tolerance_budget_16c17cb04f`，最终输出`.local/evidence/development/D015/close.xml`及close.txt。普通测试与尾批检查见[尾批记录](../tail-checks.md)。用户说明`docs/topics/analysis/tolerance-budget.md`；例子`examples/requests/tolerance-budget.json`。
