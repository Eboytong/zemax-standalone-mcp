# D006光谱、方向与其余专题原生合同

日期2026-11-09；主仓C:/Users/tonge/Desktop/mcp。源码0.1.62、101工具/132分析；原生24.2.0 build240529 PremiumEdition，项目.venv，进程COMPLUS_LoadFromRemoteSources=1。原生串行；完整验收仍3/10、剩余93组。

## 1. 单项计划及声明范围

按D006成员确认各专题正式输入、设置回读及有效输出。光谱以可变XYZ/文件和色度为完整范围；方向性以不同IES/扫描角及归一化为完整范围。其余八项分别确认通量曲线、两CIE图、极坐标轴、照明网格、光致发光有效模型、Radiant许可、道路设置及指标。

已确定失败条件复用历史；本轮原生通道恢复后取得当前构建的实际设置/结果/消息及关闭证据。原生succeeded只表示分析任务到终态，以下逐项按实际内容判断功能状态。

## 2. 正式接口探查及输入

复用scripts/probes/D005/runtime_contracts.py的有界任务机制，新增scripts/probes/NS-03/source_contracts.py。输入为官方Example 1 Two-color mixing gives white.zos工作副本；分析前后系统设置和NSC对象均保持。NSC结构使用get_nsc_objects；初轮误用get_surfaces的失败保留，未记作专题执行失败。

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/NS-03/source_contracts.py .local/evidence/development/NS-03/source-contracts-20261109-r2
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/NS-03/source_contracts.py .local/evidence/development/NS-03/remaining-contracts-20261109 --remaining
```

十个任务分别成功，均AS_Default；公开属性仅Analysis/TheDataID/IsValid/IsActiveWindow/Parent，无专题选择。两轮probe.json保存运行设置、成员、所有集合计数、原始值、消息、文本及任务上下文。两轮shutdown回执was_connected=true、native.closed=true、forced=false、error=null。会话分别0216987a6e6b4f1bbf81b88446d773f0和e1a2b41f22a04288ad173ebd46fe441f。每个任务到终态关闭后再执行下一个。

## 3. 光谱与方向性真实stdio

现有有类型默认请求source_spectrum_viewer/directivity_plot继续使用。新增NSC对象保持及PNG断言；方向性增加固定离散角积分参考，执行前门槛0.0051lm，依据报告小数显示精度。37点IES归一化沿用原5.1e-5门槛。

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -m pytest tests/native/test_source_spectrum_live.py tests/native/test_directivity_plot_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/source-contracts-20261109-r2 --junitxml=.local/evidence/development/NS-03/source-native-20261109-r2.xml
```

2 passed，35.06秒。初轮新增get_nsc_objects漏传stdio必填request，已改request={}；原失败XML保留。

光谱：20点0.44至0.64µm、最大权重1，输入/拟合XYZ均[1,1,1]、CRI70.1766、CCT5188K；样例和空NSC结果相同。默认报告解析、两行分页、PNG、对象/设置保持及正常断开通过。原始`.local/runs/runs/source_spectrum_3283c02702/`。这些默认常量属于输出采用检查；可变输入与独立色度参考未完成。

方向性：sample.ies、37点、峰值18cd。原生112.81lm，独立IES节点梯形积分112.81009451201489lm，差9.451201488275274e-5lm≤0.0051lm；每角归一化沿用原门槛，43项数值检查通过。解析、两行分页、PNG、对象/设置保持与断开通过。原始`.local/runs/runs/directivity_plot_af8d333068/`。连续三角分布积分113.09733552923255lm单列诊断，未将其与离散积分混用。

两项保持implemented，正式XYZ/文件/扫描角选择及实际采用仍缺。

## 4. 其余八项结果及解除条件

| 条目 | 当前结果 | 下一条件 |
| --- | --- | --- |
| FluxvsWavelength | 八类集合0；文本true但为空 | 取得正式输入合同和非空曲线/网格/文本 |
| SourceColorChart1931 | 八类集合0；文本false | 正式图表坐标/图像出口及输入 |
| SourceColorChart1976 | 八类集合0；文本false | 同上，分别验CIE1976 |
| SourcePolarViewer | 一个19×19网格，Dx10、Dy360/19、Min0，值0—18，文本false | 正式文件/扫描选择、轴和单位；非对称输入控制 |
| SourceIlluminationMap | 八类集合0；文本false，无消息 | 正式照明输入与有效网格/图像 |
| PhotoluminscenceViewer | 八类集合0；文本和消息提示输入无效数据/设置 | 正式有效模型条件和受控输入 |
| RadiantSourceModelViewerSettings | 八类集合0；消息仅旗舰版支持；文本false | 所需许可与匹配Radiant资源 |
| RoadwayLighting | 八类集合0；文本包含CIE140-2000/ME1/R1默认道路设置及八项零指标 | 道路专用模型、正式设置采用与独立照明指标参考 |

Photoluminscence/Radiant消息的ErrorCode均为Success，判定保留具体消息，未据此认定可用。道路报告相较旧记录新增明确文本出口，输入仍是颜色混光样例，尚未形成道路有效数值验收。

## 5. 非对称资源准备

新增examples/resources/light_sources/asymmetric-cosine.ies及asymmetric-cosine-reference.json。自有解析源I(theta,phi)=12×[1+0.25 sin(theta) cos(phi)]cd；19个垂直节点、5个水平节点含360°闭合点。theta90°时phi0/90/180°分别15/12/9cd，能区分水平选择。连续解析总通量48πlm，文件离散/插值通量在采用后独立验收。资源未替换任何本机sample.ies，原生输入采用尚待正式选择接口。

## 6. 普通检查与后续

相关普通检查：test_basic_analyses、test_light_source_report、test_bitmap_image、test_image_viewers、test_imaging、test_scene_images、test_contracts、test_development_status_report，187 passed，1.65秒。命令basetemp=.local/tmp/source-bitmap-final-20261109，其余参数-B -m pytest -q -p no:cacheprovider。

D006十项台账分别同步当前结果和解除条件；完成数保持不变。下一组D007优先BSDF正式资源选择、ISX及散射/路径功率；D006取得正式输入/出口后返回。全量回归与发行继续累计十项门槛。
