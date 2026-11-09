# 透射扇图可选择输入验收

2026-11-08；源码0.1.61工作区执行，随后进入0.1.62发行候选；OpticStudio24.2.0 build240529 PremiumEdition、Python3.14。条目PO-01.TransmissionFan。

计划：保留原生默认报告，修复可变波长列；先用正式批量偏振追迹验证与专题对应关系，再补有类型选择、Jones输入、结果、分页、图像和生命周期。手册参考为已提取的`PO-01/manual-index-904.txt`：透射强度按视场/波长/瞳扇及Jones/非偏振输入定义。

实现：请求增加method=auto/native/ray_trace、field/wavelength（0全部、正数单项）、sampling（3..1001奇数、默认201）、可选polarization（jx/jy、x_phase/y_phase，度）。省略选择保留原生文本；显式选择走正式CreateNormPol/AddRay路径。非偏振取单位X/Y输入功率平均；Jones振幅归一化。系统设置回读确定实际视场/波长/配置，原生调用参数随结果保存。几何追迹单独判定错误/渐晕；无效点为null，保留逐光线状态及计数。没有将调用参数冒充专题设置getter。

结果含series、分页rows、实际设置、计算来源和追迹子任务ID。子追迹工具在finally关闭；失败使子任务失败并传播，父任务不拥有专题工具。默认专题保留原生关闭记录。成功、失败、取消、复用及保存重载沿现有机制。

定向普通命令`.venv/Scripts/python.exe -B -m pytest tests/unit/test_transmission_fan.py tests/unit/test_yni_contributions.py tests/unit/test_contracts.py tests/unit/test_basic_analyses.py tests/unit/test_evaluation.py tests/unit/test_field_analyses.py tests/unit/test_polarization.py -q -p no:cacheprovider`：180通过。新增请求边界、方法选择、归一化溢出、无效点/错误、取消和解析损坏数据检查。

最终原生命令`.venv/Scripts/python.exe -B -m pytest tests/native/test_transmission_fan_live.py --run-zemax -q -s -p no:cacheprovider --junitxml=.local/evidence/development/PO-01/transmission-fan-adoption-final-20261108.xml`：4通过，78.29秒。

| 条件与独立参考 | 固定容差 | 实际结果 |
| --- | --- | --- |
| SCHOTT.AGF N-BK7 Sellmeier + 无吸收双界面Fresnel；0/5°、0.55及0.65µm、单/双波长、两扇向，2412点 | 绝对5.1e-5，对应报告四位小数 | 最大差2.0655219793108692e-5，通过 |
| Cooke原生文本与正式批量偏振平均，18条全曲线3618点；另90点初始路径实验 | 绝对5.1e-5 | 共3708比较，最大差4.989979395852995e-5，通过 |
| 30°平板，0.65µm，X/Y、相位差90°等权Jones、振幅2归一化，40点 | 1e-8 + 1e-7×参考值 | 最大差3.1963320878958257e-13，通过 |
| 显式视场2/波长2/5点；截光、取消复用、重载、分页和PNG | 身份/终态/状态与请求一致 | 通过 |

原始目录：`.local/runs/runs/polarization_transmission_fan_ea9aada272`、`transmission_fan_fresnel_276ba2651a`、`transmission_fan_batch_equivalence_937c480913`、`transmission_fan_jones_3a839f3064`。calls.json/checks.json、原生文本和fresnel-reference.json记录请求、实际数据、逐点误差及终态；关闭回执native.closed=true、forced=false，均正常断连。

前期失败已保留：非法厚度输入、测试保存工具名错误、未识别截光占位符；复合父任务误查close_attempted；服务端默认值展开导致路径选择不确定；通用适配误写AS_Default的Field/SampleSize。已分别修正，并由最终整文件执行覆盖默认报告与显式路径。启动FRU警告仍沿BASE-04未解决问题记录。

结论：原生默认报告与经验证的正式追迹替代路径合计覆盖透射扇图选择和计算范围，条目done。原生专题自身的设置选择器仍无接口；forced native显式选择返回UNSUPPORTED_SETTING。PO-01其他专题分别保留未完成状态。本项计B006第10项，随后执行集中发行检查。
