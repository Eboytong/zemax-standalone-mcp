# D006光谱输入绑定与NCE模式合同修复

日期2026-11-09；源码0.1.62、101工具/132分析；原生24.2.0 build240529 PremiumEdition。执行环境为主仓.venv，进程COMPLUS_LoadFromRemoteSources=1，所有原生执行串行。

## 声明范围与计划

确认正式NCE SourceColorSettings是否绑定独立SourceSpectrumViewer输入。以两个黑体温度及两组XYZ改变所有四个SourceEllipse；核对实际参数、Fit及查看器谱线。若回读具体类暴露跨模式别名，按公开ISCS接口收敛回读和请求，补参数拒绝、保存重载和stdio回归。

专题完整范围仍为正式颜色模式、数值/文件输入选择、实际采用、独立光谱和色度参考，以及结果/生命周期。此次修复交付NCE模式合同，专题选择仍待正式路径。

## 正式依据、输入与请求

- 本机用户手册1410—1411页：Source Spectrum Plot具有独立Source Color、模型输入、Spectrum、波长范围和Spectrum File设置。1408—1409页分别定义方向性文件/扫描及极坐标Normalize和范围。摘录保存在`.local/evidence/development/NS-03/source-input-routes-20261109/manual-*.txt`。
- 官方样例`ZemaxData/ZOS-API Sample Code/C#/CSharpStandalone_25_source_spectrum_diffraction_grating.cs`：SourceColor/_S_BlackBodySpectrum设置及DetectorViewer读取；没有SourceSpectrumViewer输入选择示例。
- 本机公开接口快照`BASE-01/probe/api-interfaces.json`：十种ISCS模式的可读/可写字段及ISCS_SpectrumFile.GetAvailableSpectrumFiles。SystemWavelengths没有可写设置；SpectrumFile只有SpectrumFile可写，采样字段为只读。
- 官方`Example 1  Two-color mixing gives white.zos`工作副本，四个SourceEllipse和一个DetectorColor。原始文件保持；实验仅改自有工作模型。
- 黑体两组TemperatureK=3000/6000、SpectrumCount=20、WavelengthFrom=.4、WavelengthTo=.7；XYZ两组分别[1.5,.5,.1]及[.2,.1,1.5]，其余值沿各次重新打开的基线。

请求示例见`examples/requests/nsc-source-spectra.json`。波长单位µm、温度K，模式及设置名沿用正式API名称。run_analysis请求保持source_spectrum_viewer默认合同。

## 实际结果与修复

NCE黑体Fit由[1,.9253,.3648]变为[.9300,.9581,1]；两组XYZ拟合分别为[1,.3571,.0591]及[.7047,.2731,1]。四次独立查看器均20行、输入/拟合XYZ=[1,1,1]、CRI70.1766、CCT5188K，逐行数据完全相同。NCE设置实际采用，仍未绑定独立查看器。

修复前具体实现类将同一底层值同时显示为TemperatureK、X、R、u等字段。新增source_spectrum.py，依据十种正式ISCS合同实现有类型的mode/settings联合请求；保留请求的既有外层结构。回读仅含当前模式正式字段及Fit，SpectrumFile额外包含原生只读采样。跨模式、只读字段、未知模式及无效数值在修改前拒绝。省略设置保留当前值。更新后的schema由真实stdio导出。

本轮数值判据为输入实际采用、对应Fit变化及查看器逐行比较；未新增光谱算法数值通过结论。原专题参考及容差继续沿用。

## 命令与检查

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/NS-03/source_spectrum_binding.py .local/evidence/development/NS-03/source-spectrum-binding-20261109-r4
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_source_spectrum_settings.py tests/unit/test_nsc_final_state.py tests/unit/test_remaining_adapters.py tests/unit/test_mixed_objects.py tests/unit/test_contracts.py tests/unit/test_development_status_report.py -q -p no:cacheprovider --basetemp=.local/tmp/source-spectrum-settings-20261109 --junitxml=.local/evidence/development/NS-03/source-input-routes-20261109/unit.xml
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_nsc_live.py tests/native/test_spectral_phosphor_live.py::test_uniform_source_spectrum_native tests/native/test_source_spectrum_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/source-spectrum-settings-native-20261109 --junitxml=.local/evidence/development/NS-03/source-input-routes-20261109/native.xml
.\.venv\Scripts\python.exe -B -X utf8 scripts/development/export_tool_schemas.py
```

- 首轮普通128 passed，1.66秒：模式合同、别名/只读/数值拒绝、部分设置、原生读失败来源、修改前拒绝及受影响消费者。
- 最终扩大受影响普通范围167 passed，2.35秒，覆盖NSC provenance、光谱解析、发行参数及状态统计；原始unit-final.xml。
- 串行真实stdio 3 passed，36.71秒：NSC建模/追迹/ZRD/探测器、均匀三谱线及光谱查看器。沿用原追迹门槛；具体误差见各checks.json。
- 原始stdio目录：`.local/runs/runs/nsc_b3de5cb393/`、`uniform_spectrum_2d832b67e0/`、`source_spectrum_c52d75a034/`。
- 四组直接原生对照均succeeded并close_attempted=true；拒绝后的模型保持、分析前后保持、保存重载及重开基线均通过。
- 首轮探针误用NSC不支持的get_configurations，第二轮run_analysis缺少request包装，均已修正并保留失败probe.json。第三轮取得原别名问题，第四轮完成修复后回归；这些探针错误未归入原生专题接口失败。
- 原生退出仍输出既有FRU__delta_init警告；各成功进程退出码0，关闭回执native.closed=true、forced=false、error=null。

## 生命周期与结论

- blackbody_3000：模型修订3，任务1ffb5de87fe945d990a438a62b6a630b；7行分页取齐20行；拒绝保持True，分析保持True，重载保持True。
- blackbody_6000：模型修订6，任务aaecb7e7fe334f8d83018fd88d3aa172；7行分页取齐20行；拒绝保持True，分析保持True，重载保持True。
- xyz_red：模型修订9，任务239335dae7b24c86b5ec550bdb29a088；7行分页取齐20行；拒绝保持True，分析保持True，重载保持True。
- xyz_blue：模型修订12，任务f88c7065e7154de593a5666626d17f4d；7行分页取齐20行；拒绝保持True，分析保持True，重载保持True。

会话1436fc0a9d154f66b0ab590ce961309b；重开原始工作副本后系统设置、对象、评价函数及配置均恢复；shutdown检查点成功、应用关闭成功，无强制终止。

SourceSpectrumViewer保持implemented；取得独立专题的正式模式/数值/文件选择和实际回读后，才能完成光谱/色度数值验收。下一项按D006顺序寻找其他依赖满足的正式输入/结果；已有相同条件空接口记录沿用。完整验收仍4/10，剩余92组。
