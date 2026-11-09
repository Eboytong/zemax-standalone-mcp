# B006 首次完成归属核对

2026-11-08，源码/发行基线0.1.61。本记录核对当日已执行的完成项及批次漏记；记录维护本身不另计功能。

此前B006记录6项；以下3项已有本轮原生完成证据，未出现在B003、B004或release061的B005完成名单，补记其首次完成归属，B006为9/10。

| 条目 | 原始结果与范围 | 结论 |
| --- | --- | --- |
| EXT-SPEOS.LensSystem | Cartesian及radial导出；本轮Cartesian输出54,523,861字节。原始结果`.local/runs/runs/speos_cartesian_a54755af39/c231fe8d02004fc1897025f13db39483/a9931b88320a4cd293e1cb344893b335.json`：copy_closed/tool_closed/source_metadata_preserved均true；calls记录任务成功及断连。 | 导出done；接收端导入保留独立未完成项。 |
| EXT-SPEOS.Whitebox | 原生OutputFilename=input.odx、ErrorCode=0及ODX/日志/ZDA。结果`.local/runs/runs/speos_whitebox_546c939a28/4d5ee7037bc149889a59941188f1e0f4/5faac7c07a3840ff8db40c4dce17992c.json`三项关闭/保持标志均true，calls正常断连。 | 导出done；接收端导入仍需环境。 |
| ED-01.Aperture.FloatingToNone | 本轮三次Floating→None，回读及其他属性保持。`.local/runs/runs/property_aperture_numeric_63cdfcea98/state/close_receipt.json`：native.closed=true、forced=false。 | done。 |

单项计划、请求、实际设置、命令、检查和环境分别见`development/evidence/EXT-SPEOS/lens-system-export-20261108.md`、`whitebox-export-20261108.md`及`development/evidence/ED-01/floating-aperture-clear-acceptance20261108.md`。此次直接复用条件适用的原始证据。

MF-01.TestPlateList继续implemented。progress435的899行/1799次尺寸对照、误差0、两项原生通过，支持原生活动目录及明确TPD文件路径；原记录仍列原生目录选择/采用回读缺口。不能凭后续维护说明关闭这一范围，故不计入本批完成数。436为能力补验，437仅手册材料。

下一动作：继续排序队列；第十项完成后执行全量普通、串行原生、构建、独立安装及真实stdio集中检查。未启动新原生实例，未构建0.1.62。
