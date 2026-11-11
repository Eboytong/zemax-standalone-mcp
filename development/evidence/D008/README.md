# D008：玻璃贡献与替换试验

2026-11-11；主仓源码，Python3.14、OpticStudio24.2.0/build240529、PremiumEdition。已完成公开glass_trials请求、自动目录筛选、独立贡献参考、同预算原生优化、排名与候选保存。发行1.0.0保持原值，当前源码102工具、138分析入口。

## 已取得的原生结果

受控胶合双镜：前面R=50mm、N-BK7厚3mm；胶合面R=-40mm、N-F2厚2mm；后面R=-150mm、后空气90mm；光阑位于前面，孔径5mm；无穷远物方、视场0/2度、F/d/C波长0.4861327/0.5875618/0.6562725µm。前镜/后镜半口径5mm。

已读取Seidel原生文本、逐段三个波长的ILDE.GetIndex折射率、IMaterialsCatalog的Nd/Vd、波段、状态、替换排除标志、成本属性，以及PETC/PETZ/EFFL/AXCL/LACL/RSCE/RWCE/MTFT/MTFS的实际参数列。

正式GetIndex签名为`GetIndex(surface,count,double_array)`，成功返回请求数量。EFFL/PETC/PETZ的Wave在原生列3，列2未启用；AXCL使用两波长与Zone，LACL使用两波长及系统最大视场。角度、索引和单位已在原始数据中保留。

## 固定参考定义

- 采用正则近轴向量`(y,n*u)`，折射矩阵`[[1,0],[-(n_after-n_before)*c,1]]`，传播矩阵`[[1,t/n],[0,1]]`。当前合同从无穷远物方、空气起止、居中旋转对称系统开始。
- 轴向色差和横向色差采用C-F符号，与原生AXCL/LACL对齐。镜片材料贡献为参考d线处焦距/像高对该玻璃折射率的偏导，乘`n_C-n_F`；导数采用复步长1e-20。独立的F/C有限色差另外返回，包含色散非线性。
- Petzval曲率采用原生像面曲率符号`-Σ[(n_after-n_before)c/(n_before*n_after)]`。单玻璃段归属为`-(1-1/n)*(c_entry-c_exit)`；相邻玻璃在胶合面望远相消，求和与全系统曲率一致。
- 真正像质变化通过替换前后同条件原生评价和同预算优化对照计算；三阶原生Seidel表保留其原始定义和文本精度。

预先门槛：近轴代数及原生量对照`1e-10 + 1e-6×|参考值|`。结果：

| 量 | 矩阵值 | 原生值 | 绝对差 |
| --- | ---: | ---: | ---: |
| d线EFL/mm | 84.62539967013947 | 84.62539967013949 | 1.42e-14 |
| Petzval曲率/mm^-1 | -0.008315447060130411 | -0.008315447060130413 | 1.73e-18 |
| C-F轴向色差/mm | 0.3638087507358847 | 0.3638087507358616 | 2.31e-14 |
| C-F横向色差/mm | 0.0003424906085940371 | 0.0003424906085949253 | 8.88e-16 |

3项普通测试通过，覆盖薄透镜闭式参考、胶合材料的独立有限差分灵敏度、Petzval材料归属求和、退化与不一致材料段。

## 输入修正及生命周期

最初探针通过有类型请求传入无穷大厚度被finite_number拒绝；随后直接使用原生物面无穷远值建立自有控制模型。首次插入额外曲面时保留的原光阑落在后方零孔径面，Seidel返回“主光线不能被追踪”；调整为三界面并显式指定前面为光阑后，原生报告成功。曲率从Radius换算；ILDERow没有Curvature属性，探针已修正。

每次探针均在finally调用disconnect，最终记录ok=true。原始结果：`.local/evidence/development/D008/{probe_native.py,native-probe.json,reference-checks.json,operand-manual.txt}`。参考手册为本机2024R2英文版1066—1074页；GitHub参考G4的glass_explain.py和glass_trial.py固定commit50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3，读取其贡献/候选试验组织思路，算法独立编写。

命令：

```powershell
$env:PYTHONPATH="$PWD;$PWD\src"
.\.venv\Scripts\python.exe -B -X utf8 .local/evidence/development/D008/probe_native.py
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_glass_reference.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d008-reference-final
```

## 工作流及最终验收

新增glass_trials.py和glass_reference.py；请求由run_analysis注册，复用任务、rows分页和series绘图。原生目录扫描365材料，124种满足默认过滤；原材料N-BK7与最近四种BK7、N-BK7HT、N-BK7HTI、BK7HT分别在新副本中采用相同变量/目标/算法/循环数/优化预算执行。BK7HT的Nd/Vd不同，覆盖实际色散数据变化。

128项相关普通测试通过（0.98s），包括22项合同/滤选/矩阵测试和2项清理错误保留测试。最终原生用例各自独立启动并串行运行：

| 用例 | 结果 | 原始记录 |
| --- | --- | --- |
| 真实stdio五材料优化、有限色差参考、候选重载、无候选、分页、图像及取消 | 1 passed / 92.93s | .local/runs/runs/glass_trials_native_6b47e6df1c |
| 半径/厚度双变量、多目标、两目录同名材料、材料solve保护 | 1 passed / 22.05s | .local/runs/runs/glass_trials_protection_41954d381e |

原材料单变量merit从0.0011952351939494561降至7.353853608391757e-6；四种替换候选均成功。每组回读配置、MFE目标/权重、优化器与变量、采样及边界；比较RMS光斑、RMS波前、单频MTF及EFL。源曲面、系统设置和修订号保持原值。最佳候选保存重载后五项指标按1e-10+1e-7相对容差复算。取消取得cancelled终态，全部副本关闭，后续分析成功。

两目录同名用例由本机SCHOTT.AGF复制为自有D008_<uuid>.AGF，触发AMBIGUOUS_MATERIAL，副本关闭后删除自有文件。材料solve在读取折射率前拒绝，保留SOLVE_PROTECTED；半径使用CVGT/CVLT的反半径范围，厚度使用CTGT/CTLT，原生参数列均已确认。

原生发现修复：GetCatalogsInUse含空项；RelCost可为问号；重复AddCatalog会产生两个SCHOTT记录。实现过滤空项、保留未知成本原文并按成本条件筛选、仅添加尚未加载的目录。早期失败记录723a64046f/ecc30766e2/ee1fc3372a及d97ca9fc52分别保留测试请求包装、重复目录、测试保存工具名和solve检查顺序问题，最终记录采用修正后的入口。

最终会话disconnect成功，resources.all_copies_closed=true、cleanup_errors为空，自有资源已清除。图像已查看。状态done，累计8/16；下一项D009。

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_glass_trials.py tests/unit/test_glass_reference.py tests/unit/test_catalogs.py tests/unit/test_materials.py tests/unit/test_material_cell_identity.py tests/unit/test_merit_edit_safety.py tests/unit/test_standalone_optimization.py tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d008-affected
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_glass_trials_live.py --run-zemax -q -s -p no:cacheprovider --basetemp .local/tmp/pytest-d008-native
```

独立参考、目录、边界及生命周期的补充原始材料：.local/evidence/development/D008/{workflow-probe.json,duplicate-catalog-probe.json,bounds-manual.txt}。官方手册1078页定义单频MTF，1083页定义逐面厚度/曲率约束。请求示例examples/requests/glass-trials.json，使用文档docs/topics/modeling/glass-trials.md，schema已同步。集中检查按10项门槛执行。
