# D008 样板目录原生配置入口

2026-11-09，主仓 `C:/Users/tonge/Desktop/mcp`，源码0.1.62；Python3.14、OpticStudio2024 R2/24.2/build240529/Premium。声明范围为原生样板目录选择、报告身份、尺寸、分页及资源关闭。本轮为部分实现，完整验收维持7/96。

## 计划及正式接口

先在原生样板列表中选择第二个目录并保存原生配置，再使用正式 `IAS_.LoadFrom` 在独立 Standalone 中加载。原生报告第一行确认实际 TPD 身份；各行尺寸以安装目录内官方 TPD 资源为参考，沿用绝对容差0.0000500001毫米。任意合法目录选择、第二目录及完整生命周期通过后再判定整项完成。

## 实现及检查

`TestPlateList.native_settings_file` 为 CFG 绝对路径，适用于 `auto/native`；执行前检查文件存在，分析对象先 `GetSettings/LoadFrom` 再 `Apply/GetTextFile`。结果 `native_configuration` 保存路径、加载返回值和报告头实际目录。显式配置与请求目录不一致时保留原生文本并返回 `SETTING_NOT_SUPPORTED`；分析对象通过既有 finally 路径关闭。

普通用例覆盖路径类型、方法冲突、加载接受/拒绝、目录不一致和关闭；本轮连同契约和状态统计定向检查80项通过（0.84秒）。命令：

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_test_plates.py tests/unit/test_contracts.py tests/unit/test_development_status_report.py -q -p no:cacheprovider --junitxml=.local/evidence/development/MF-01/native-cfg-unit-20261109.xml
```

schema已通过 `scripts/development/export_tool_schemas.py` 更新；能力说明和样板目录专题已同步。新增 `tests/native/test_test_plates_live.py::test_test_plates_formal_cfg_save_and_stdio_reload`，以正式 SaveTo 生成任务自有输入，关闭首个实例，再通过真实stdio重放并比较原生参考和独立TPD尺寸；该新增原生用例本轮尚未运行。

## GUI重试与当前状态

用户手动点击“保存”后，文件写至默认 `C:\Users\tonge\Documents\Zemax\Configs\TPL.CFG`，已复制为 `.local/evidence/development/MF-01/Atoptical.CFG`。实际独立原生重放报告仍为 `Applied.tpd`；配置加载成功但 Atoptical 身份核对返回 `SETTING_NOT_SUPPORTED`。报告保留在 `.local/runs/runs/plates_selected_cfg_c385ed344f/`。因此手动保存没有捕获 Atoptical 选择，不能作为第二目录证据。

另一项独立原生检查由原生 `SaveTo` 生成活动配置，随后关闭原会话并经真实stdio新会话 `LoadFrom`。OpticStudio 24.2 Premium 中用例通过，耗时15.25秒；1798个目录尺寸检查全部通过，最大误差0；报告实际身份Applied.tpd，分页、分析关闭、模型状态保持、保存重载、任务及正常断连检查通过。JUnit：`.local/evidence/development/MF-01/formal-cfg-replay-native-20261109.xml`；原始输入、调用和误差检查在 `.local/runs/runs/plates_cfg_replay_e28ecbc12c/`。

用户操作后启动的本轮空白GUI实例已按不保存Lens改动关闭；native close receipt显示 `closed=true`、`forced=false`。本次也出现FRU重复初始化日志，已独立真实stdio用例后续通过，显示该日志未阻止该重放。普通检查80项通过。CFG正式加载/活动目录Applied重放通过；原生任意目录选择仍未实现/验收，条目保持 `implemented`。下一步转D008 SurfaceData原生面号设置入口，另将TestPlate第二目录选择留待新设置采用证据后处理。
