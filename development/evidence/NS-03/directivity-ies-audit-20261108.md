# 方向性图独立 IES 参考审计

2026-11-08；源码0.1.61工作区；OpticStudio24.2.0 build240529 PremiumEdition、Python3.14。

计划：核对报告文件身份，以安装的sample.ies建立独立角度/光强/通量参考，加固坏行处理，并检查分页、模型保持和关闭。

输入为Colorimetry两色混光样例；报告文件名sample.ies，对照文件为`C:/Users/tonge/Documents/Zemax/Objects/Sources/IESNA/sample.ies`。LM-63-1995、TILT=NONE，19个垂直角0–180°、19个水平角0–360°；所有水平切片相同，光强18至0 cd。按绝对角度查表、除以18，逐点对照37个原生角度，预设绝对容差5.1e-5，全部通过。

报告峰值18 cd、通量112.81 lm。对原始采样做`2π∫I sinθ dθ`梯形积分得112.81009451201489 lm；按连续分段线性强度精确积分得113.09733552923255 lm。原生通量与离散梯形积分一致到报告小数精度；连续插值的定义需正式依据，未据此关闭完整条目。

实现：解析器拒绝损坏行、非有限/负强度、非有限/负峰值或通量，以及重复或逆序角度，保留原始文本。普通命令`.venv/Scripts/python.exe -B -m pytest tests/unit/test_yni_contributions.py tests/unit/test_contracts.py tests/unit/test_basic_analyses.py -q -p no:cacheprovider`：77通过。原生命令`.venv/Scripts/python.exe -B -m pytest tests/native/test_directivity_plot_live.py --run-zemax -q -s -p no:cacheprovider --junitxml=.local/evidence/development/NS-03/directivity-ies-reference-20261108.xml`：1通过，9.71秒。

原始数据`.local/runs/runs/directivity_plot_3b4cdaddec/ies-reference.json`及同目录calls.json记录实际请求、曲线、任务和断连。分页start3/count2通过；任务succeeded、close_attempted=true，系统设置保持，正常断连。启动FRU警告仍存在，沿用BASE-04生命周期问题。

结论：NS-03.DirectivityPlot保持implemented。正式IES文件/扫描角选择与采用回读仍缺；取得接口后以非旋转对称、多扫描角资源验证选择与归一化。此次不计新增完成数。
