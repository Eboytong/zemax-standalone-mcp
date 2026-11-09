# 0.1.62 发行完成

2026-11-08：B006 10/10，集中检查通过，默认安装已切换0.1.62。全量普通2590通过/819跳过；集中原生23个不同用例最终通过；独立安装schema101工具/118分析及原生2项通过。断开回执native.closed=true、forced=false。结构化记录见[release062.json](release062.json)。B007为0/10，目标0.1.63。FRU警告保留。

## 历史执行记录

# 0.1.62 集中发行检查进度

2026-11-08；B006首次完成10/10，未发行。条目清单在`development/tracking/batches.json`，透射扇图最终4项原生通过见PO-01独立验收。

全量普通命令：`.venv/Scripts/python.exe -B -m pytest tests -q -p no:cacheprovider --junitxml=.local/evidence/development/BASE-04/batch-B006-ordinary-final-20261108.xml`：2590通过、819跳过，29.89秒。首次14失败、2576通过、819跳过的XML保留。修复涉及测试/参考迁移路径、测试夹具位置、101工具预期、solve支持文档定位，以及保存故障注入使用真实不可写目标；定向124项通过后全量重测通过。

wheel构建：`pip wheel . --no-deps --no-build-isolation --wheel-dir releases/0.1.62`成功；独立`pip install --no-deps --target .local/builds/wheel-install062 releases/0.1.62/zemax_standalone_mcp-0.1.62-py3-none-any.whl`成功。候选包尚未成为默认安装版本。

独立安装stdio schema：`scripts/release/installed_schema_smoke.py .local/builds/wheel-install062 .local/evidence/development/BASE-04/installed-schema062 0.1.62`成功，101工具、118分析、正常关闭，未启动原生应用。

集中原生组串行执行，XML为`.local/evidence/development/BASE-04/batch-B006-native-20261108.xml`。首两个POP/制造工作流在connect返回INVALID_LICENSE，失败应用已关闭；其后NSC MTF、QuickYield及YNI已取得成功输出。前两项需在此组终态后单独重测，禁止与当前原生组并行启动。

扩展FFT相干诊断的128/dft_knots窗口最大差1。原始数据`.local/runs/runs/fft_spread513_fft_stretched_dft_knots_128_8e9249cd9f/comparisons.json`保留。独立离散瞳步长10/63 mm给出的无混叠范围为±173.25µm（焦移后±173.28465µm），请求绘图范围约±352µm，离散变换在外侧产生周期重复；原生外侧为0。范围内误差分别0.0004842707765871368/0.0003281285123865052，低于既有0.005。参考检查现按采样间距计算有效域，原生域外以绝对1e-12检查零延伸；全窗口差及掩码均保存。此调整未改产品输出或数值容差，待单独重测。

仍待：当前原生组终态、失败项/参考修正重测、安装包原生stdio执行/分页/图像/关闭，以及发行记录和下一批交接。启动FRU警告未解决。所有成功数量以最终XML为准。
