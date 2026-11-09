# D005公共分析方法与设置文本探查

日期：2026-11-09。主仓C:/Users/tonge/Desktop/mcp；源码0.1.62，101工具/132分析。原生24.2.0、build240529、PremiumEdition；项目内.venv，进程COMPLUS_LoadFromRemoteSources=1。

## 声明范围与方法

检验正式IA_.ToFile和Application.CreateSettingsFromParent能否补齐六种图像专题的输入选择或有效输出。StandardSpot作为具有专用设置的对照。使用官方Cooke 40 degree field.zos工作副本，当前配置1、毫米单位。所有输出均为任务自有文件。

IA_.ToFile的正式签名为Filename、showSettings、verify；CreateSettingsFromParent接收IZAPI_BaseObject。第一轮分别以分析和设置为parent，并使用.txt/.png/.zda后缀，showSettings=false、verify=false；第二轮showSettings=true、verify=false。后缀对照检验输出内容类型；设置文本对照检验设置键是否实际可见。

## 命令与原始证据

脚本：scripts/probes/D005/analysis_common_outlets.py。执行前设置上述进程环境变量。

```powershell
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/D005/analysis_common_outlets.py .local/evidence/development/D005/common-outlets-20261109
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/D005/analysis_common_outlets.py .local/evidence/development/D005/common-settings-output-20261109 --include-settings
```

各目录probe.json保存请求、任务上下文、实际设置类型、文件输出及生命周期。执行发生于UTC 2026-11-08 21:46—21:48，对应本地2026-11-09。

## 实际结果

| 分析 | 专用设置 | 第一轮每文件字节 | 设置文本字节 | 两轮终态 |
| --- | --- | ---: | ---: | --- |
| StandardSpot | True | 697 | 1086 | succeeded/succeeded |
| LightSourceAnalysis | False | 320 | 370 | succeeded/succeeded |
| BitmapFileViewer | False | 275 | 331 | succeeded/succeeded |
| PartiallyCoherentImageAnalysis | False | 3259 | 3332 | succeeded/succeeded |
| ExtendedDiffractionImageAnalysis | False | 1049656 | 1049725 | succeeded/succeeded |
| GeometricBitmapImageAnalysis | False | 275 | 346 | succeeded/succeeded |
| BeamFileViewer | False | 17041 | 17095 | succeeded/succeeded |

第一轮全部21个文件均为结果文本，以Results for:开头。.png扩展名未产生图像，.zda扩展名未产生设置容器。七种分析共14个parent字典均available=true、count=0、keys=[]。

第二轮StandardSpot导出Field、Wavelength、Pattern、ReferTo、Configuration等专用设置；其余六种AS_Default仅含分析名称及结果文本，未取得输入文件或完整设置选择键。Beam仍报告未定义文件，默认非空结果未证明实际输入身份；EXD既有网格和PCI既有结果的来源判断继续沿用原记录。

## 生命周期与模型状态

- common-outlets-20261109：会话aff1ca6b1af34125b7e43769a329daf5、模型修订1；七任务均succeeded并close_attempted=true。系统设置、曲面、评价函数和配置前后均保持；cleanup_failures=[]；disconnect.connected=false、requires_reconnect=false。
- common-settings-output-20261109：会话ef19344bf6fd4fbeb924e80c88bd2979、模型修订1；七任务均succeeded并close_attempted=true。系统设置、曲面、评价函数和配置前后均保持；cleanup_failures=[]；disconnect.connected=false、requires_reconnect=false。

任务关闭由既有任务管理器负责；原始记录没有逐任务独立Close返回值。未进行新数值验收，本项判据为设置键、输出内容类型和任务生命周期。既有数值门槛保持原记录。

## 结论与下一步

两种公共方法的本轮调用没有补齐六专题输入选择。完整功能状态保留原台账，集中检查仍4/10、剩余92组。文件选择的解除条件为：取得正式专用设置、已确认CFG或等价正式接口，并用两个不同受控输入验证报告身份及输出变化。继续D006正式光谱输入探查，复用既有默认合同。
