# D008样板、等形面拟合及图纸出口续验

日期2026-11-09（本机），原始事件UTC 2026-11-08；源码0.1.62，OpticStudio24.2.0 build240529 PremiumEdition。主仓`C:/Users/tonge/Desktop/mcp`，项目venv，COMPLUS_LoadFromRemoteSources=1。请求及容差沿用当前模型。

## TestPlateList

正式定义复用2024R2手册8.2.3与5.4.5：TPD位于原生data/Testplate，报告尺寸为mm。原始摘录来源`.local/evidence/development/EXT-EXPORT/manual042.txt`。本轮未取得正式API目录选择成员或文档化CFG键。

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/MF-01/manufacturing_viewer_probe.py .local/evidence/development/MF-01/testplate-contracts-20261109 --topic TestPlateList`。

Cooke工作副本，设置AS_Default，仅基类属性；文本头实际Applied.TPD。八类结构集合0但文本导出成功。保存CFG；设置和曲面保持，工具关闭成功。会话959df85335eb42d98e7acaafd547a3ad关闭回执native.closed=true、forced=false、error=null，checkpoint成功。探针已改为记录实际shutdown回执及模型保持。

真实stdio命令：`.venv/Scripts/python.exe -B -m pytest tests/native/test_test_plates_live.py --run-zemax -q -p no:cacheprovider --basetemp=.local/tmp/testplate-native-20261109 --junitxml=.local/evidence/development/MF-01/testplate-native-20261109.xml`，2通过，26.53秒。

原始`.local/runs/runs/plates429_native_c7a1af7028`和`plates433_lifecycle_5902a89fbf`。1798次活动目录/独立TPD尺寸检查最大误差0，原绝对容差0.0000500001mm。覆盖目录身份、分页、指定其他目录的auto文件读取及native拒绝、三种可用性、缺失/损坏文件、取消、复用、保存重载、模型保持、任务终态和正常disconnect。自有TPD资源在finally删除。显式文件读取与活动目录工作流通过；完整原生目录切换仍缺，保持implemented。

## SagTable等形面控制

声明范围包括制造偏移、完整准则和反向摘要。本轮定位面型差异，未改变原容差或制造定义。

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/MF-01/sag_equivalent_models.py .local/evidence/development/MF-01/equivalent-models-20261109`。

独立参考：解析z=.0126r²、dz/dr=.0252r；带偏移RMS半径39.84003968804416mm来自progress589的256节点径向面积积分及独立优化。行容差1e-8+1e-6×参考值，半径绝对容差5e-6mm，实验前写入探针。

四个自有模型每个17个矢高/斜率点均通过，最大矢高误差1.3877787807814457e-17mm、最大斜率误差8.854028621385623e-15。全部使用R40、conic−1、附加r²系数.0001、半口径5mm；实际参数、请求和每次原生查询完整落盘。

| 模型 | Zernike项数/归一化半径mm | 带偏移RMS半径mm | 独立参考绝对差mm |
| --- | --- | ---: | ---: |
| EvenAspheric | 不适用 | 39.840039682665214 | 5.378943512823753e-9，通过 |
| ZernikeFringeSag | 1 / 5 | 39.84000130259916 | 3.838544499501495e-5，超限 |
| ZernikeFringeSag | 1 / 10 | 同上 | 同上 |
| ZernikeFringeSag | 4 / 5 | 同上 | 同上 |

每模型记录四种SSAG BFS flag的四点重建和DSAG的正式0/1/2半径及原始偏移；同模型DSAG/SSAG半径最大差7.105427357601002e-15mm。该实验排除了所测归一化半径和启用零系数项数对历史差异的影响；面型相关的原生拟合差异仍需解释。没有把DSAG原始偏移改作制造偏移，也未新增未经正式定义的DSAG反向参数。

四模型设置、曲面、评价函数保持，查询无临时工具。会话64b85ffce550458b977dac3f1d052a62实际shutdown关闭、checkpoint成功，无强制收尾及原生错误。保持implemented；后续为面型相关拟合定义/数值算法，以及物理偏移和反向制造摘要出口。

## 图纸与查看器

两个命令分别为：

```powershell
.venv/Scripts/python.exe -B -X utf8 scripts/probes/NS-04/text_contracts.py .local/evidence/development/NS-04/graphics-contracts-20261109 --graphics
.venv/Scripts/python.exe -B -X utf8 scripts/probes/NS-04/text_contracts.py .local/evidence/development/NS-04/nsc-viewer-contracts-20261109 --nsc
```

前三项使用官方Cooke工作副本；NSC两项使用官方Boolean Example 4- a lens mount模型，实际对象清单保存。ISOElementDrawing、ZemaxElementDrawing、PrescriptionGraphic、NSCObjectViewer、PartViewer均AS_Default；五项任务succeeded且close_attempted=true，八类结构集合均0、文本false、无原生消息。现有请求/正式选择及图形出口缺口继续按各条目记录。

两个会话d91017e5b5d64fed9db77b79f7af4298和6623f9a8f19d4173ba23de9e7ccdc383的系统设置与曲面/NSC对象保持，实际shutdown回执closed=true、forced=false、error=null。成功执行和关闭按实际记录；有效图纸及部件输出尚缺。

## 普通检查与后续

命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_test_plates.py tests/unit/test_sag_table.py tests/unit/test_sag_fit.py -q -p no:cacheprovider --basetemp=.local/tmp/manufacturing-unit-20261109 --junitxml=.local/evidence/development/MF-01/ordinary-20261109.xml`，71通过，0.57秒。

原生FRU警告继续保留，根因未确认。公开工具及请求schema未变，本轮新增诊断脚本和证据。D008完整验收未新增，累计3/10、剩余93组。下一组D009先审查现有格式/版本/配置层证据及当前正式导出工厂，随后检查STAR/HPC具体前置条件。
