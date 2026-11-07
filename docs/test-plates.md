# 样板目录

新增 `run_analysis` 的 `test_plate_list`，复用任务查询、取消、结果文件及 `start/count` 行分页。资源发现使用 `get_system_resources` 的 `test_plate_files`，目录来自当前原生应用的 `ZemaxDataDir/Testplate`。

```json
{"request":{"kind":"test_plate_list","method":"native"}}
```

```json
{"request":{"kind":"test_plate_list","catalog_file":"Applied.tpd","method":"auto"}}
```

`method` 默认 auto。native 运行正式 TestPlateList，保留原生文本、消息、设置类型、报告头中的实际目录及关闭状态。省略 catalog_file 时读取原生活动目录；显式目录与报告不一致时，native 返回 SETTING_NOT_SUPPORTED，附请求、实际目录和原始文本路径。当前本机设置为 AS_Default，尚缺可确认采用的目录选择接口。

auto 对明确的目录不匹配使用官方 TPD 格式读取文件，记录 fallback_reason；原生计算、结果格式和关闭错误保留原始失败。file 直接读取指定资源，要求 catalog_file。文件名限定为资源目录中的 TPD 文件名，按本机文件名大小写规则解析；缺失文件列出可用资源。读取路径在结果中明示，文件路径与原生活动目录分别记录。

每行返回 plate_id、radius_mm、diameter_mm、concave、convex、availability_code 和 source_line。尺寸固定使用毫米；TPD 中代码 −1、0、1 分别表示凹面、两种、凸面。文件读取保留源数值精度；原生文本保留显示精度。文件路径输出 vendor_header。summary 返回样板数和凹/凸面可用数。该功能的交付输出为行和原生文本。

本机官方格式依据：OpticStudio 2024 R2 英文手册第1207–1208页，摘录见 `verification/development/MF-01/manual428-viewers.txt`。899行原生目录与独立TPD资源逐行比较通过，1798次尺寸检查的最大差为0，预设绝对容差0.0000500001mm。受控资源覆盖三种可用性、完整精度、缺失/格式错误、取消/复用和保存重载；原生指定其他目录的拒绝、分页和模型状态保持通过。

相关普通102项通过；最终真实stdio串行2项通过，两个会话均正常断连、关闭回执 native.closed=true / forced=false。早期公开请求包装错误记录于 native430-plates.xml，修正后的最终证据见 native435-plates-final.xml 与 progress435-plates.json。当前 MF-01.TestPlateList 保持 implemented，下一步为正式目录选择接口或有据可回读的CFG设置路径；该探查不增加B005完成数。
