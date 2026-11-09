# D007散射资源、图表和路径分类续验

执行日期：2026-11-09（本机）；原始事件为UTC 2026-11-08。源码0.1.62，主仓`C:/Users/tonge/Desktop/mcp`；原生24.2.0 build240529 PremiumEdition。进程设置`COMPLUS_LoadFromRemoteSources=1`。

## BSDF：正式资源选择

- 声明范围：真实BSDF文件选择、参数采用、追迹、保存重载与关闭。
- 输入：安装资源`ZemaxData/ScatterData/BrownVinyl.bsdf`，首部为Monochrome/BRDF；复制到自有工作项目的ScatterData，源文件保持。
- 正式接口：`ISurfaceScatteringBSDF.FileName`、`GetAvailableFileNames`及`ChangeScatteringTypeSettings`。
- 实验：透明面和MIRROR面分别尝试basename和自有绝对路径；第二轮先提交BSDF类型，再读取活动对象列表后写文件。
- 结果：两轮共八次尝试均未采用文件，列表及最终FileName均为“无”，类型修改返回true。第二轮提交前后列表一致。该实验排除了在所测输入下改变反射面条件或先提交类型即可采用文件的假设；根因仍未确认。
- 命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/ED-01/bsdf_selector_probe.py .local/evidence/development/D007/bsdf-reflection-20261109-r2`。
- 原始输出：`.local/evidence/development/D007/bsdf-reflection-20261109{,-r2}/probe.json`及各state目录。首轮探针错误查找last_shutdown.json，实际close_receipt.json保留；第二轮已修正读取路径。
- 第二轮会话`f72763c77ebf4f8bbf2dbd715a0e3e1f`，checkpoint成功、native.closed=true、forced=false、error=null。未将未采用资源用于数值验收。
- 本机CHM解包命令未产生帮助正文；未据此形成格式/目录定义结论。
- 状态blocked。解除条件：正式选择器返回真实文件并实际采用；随后验参数、追迹和持久化。

## IS目录

对安装ZemaxData和用户Documents/Zemax递归搜索ISX，均为0项。路径及结果见`.local/evidence/development/D007/isx-search-20261109.json`。搜索范围限上述两根目录。缺有来源且匹配原生目录的ISX，状态blocked；取得资源后执行精确名称采用、角度/采样回读、追迹和重载。

## 散射图表

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/NS-03/scatter_contracts.py .local/evidence/development/D007/scatter-contracts-20261109`。

输入为Cooke工作副本；两项均AS_Default，仅有基类属性。函数查看器八类集合均0、文本导出false。极坐标图一网格181×90，规范数组90×181，Dx=1.0112359550561798、Dy=1.988950276243094、原生MinX/MinY均0；所有值0.3183098861837907，文本导出false。当前数据尚无正式输入绑定及角度定义。

两个任务succeeded且close_attempted=true；模型设置与曲面前后相同。会话`011f4c0dcecd41c9890b5f3fc0223c2b`正常shutdown，关闭回执closed=true、forced=false、error=null。原始结果及每任务文件保存在该目录。两条保持blocked，解除条件为正式选择/有效出口及受控模型数值参考。

## PathAnalysis阈值

复用既有受控输入`.local/runs/runs/paths063_uncategorized_80ef223bc9/{calls.json,loss.zrd}`，重建模型并复制ZRD到自有工作目录。旧探针的失效fixture路径已调整为显式参数；输出目录和关闭回执同步更新。

命令：`.venv/Scripts/python.exe -B -X utf8 scripts/probes/NS-02/path_arrays_probe063.py .local/evidence/development/D007/path-arrays-20261109`。

| 相对阈值（实际回读一致） | 路径数 | 原生路径功率W | 未分类调用 |
| --- | ---: | ---: | --- |
| 0、0.5、0.9 | 1 | 0.9167180210351944 | There are no uncategorized paths |
| 0.95、1 | 0 | 无行 | 同上 |

路径顺序为`1.0, 2.1, 2.2, 3.0`；GetPathNumber(0/4294967295)均null。五次文本导出及工具关闭成功。设置和NSC对象保持，会话`7769b37cd866471ba54b38fa0da98b64`关闭、checkpoint成功，无强制收尾。

本轮阈值实验用于定位原生分类行为；独立ZRD功率参考沿用历史，未计为新数值通过。筛除路径未出现在原生uncategorized出口，需正式说明分类/筛除定义后审查参考。保留原容差及原始异常，状态implemented。

## 定向检查与结论

命令：`.venv/Scripts/python.exe -B -m pytest tests/unit/test_property_pages_adoption.py tests/unit/test_scatter_capabilities.py tests/unit/test_scatter_report.py tests/unit/test_path_analysis.py -q -p no:cacheprovider --basetemp=.local/tmp/d007-targeted-20261109 --junitxml=.local/evidence/development/D007/ordinary-20261109.xml`。

89项通过，1.24秒。原生重复出现FRU警告，未定位原因；实际关闭回执如上。公开请求契约未变，未新增schema字段。D007聚合散射继续等待BSDF及IS目录；本轮新增完整验收0，累计3/10、剩余93组保持。下一组D008先确认章节/曲面选择及默认报告当前生命周期。
