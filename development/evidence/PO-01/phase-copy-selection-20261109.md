# D001：相位专题副本输入选择与 solve 控制

2026-11-09；主仓 `C:/Users/tonge/Desktop/mcp`，源码0.1.62，Python3.14，OpticStudio24.2/build240529/Premium。完整计数仍为7/96。本记录先保留接口探查经过，末节记录已交付的公开请求与验收范围。

## 声明范围、计划与依据

`PO-01.PhaseAberration` 的剩余范围包括正式输入选择、有限共轭/变换/反射模型和完整生命周期。本轮先验证能否通过正式 `CopySystem`、视场表和 `MakePrimary` 获得指定输入的原生专题结果，避免重新实现其相位算法。

本机2024 R2手册p.903–904定义视场、波长、Jones输入及相对于主光线的相位。分析设置仍为AS_Default。使用副本中可回读的系统数据作为候选输入路径，实际采用由报告头确认；这一路径与直接专题设置的等价性须另行验证。

## 输入、调用和实际采用

输入为本机官方 `Samples/Sequential/Objectives/Cooke 40 degree field.zos` 的工作副本；源模型准备两个Y视场0/5度、权重1/.7，两个波长0.4861327/0.6562725 µm、权重.6/1，主波长为第二项；Jones幅度1/1，相位17/73度。

程序：`scripts/probes/PO-01/phase_copy_selection.py`。运行环境设置 `COMPLUS_LoadFromRemoteSources=1` 和指向主仓src的PYTHONPATH。正式接口：`CopySystem`、`ISDFields.GetField`、`ISDWavelengths.GetWavelength/MakePrimary`、`Analyses.New_Analysis_SettingsFirst(PhaseAberration)`、`ApplyAndWaitForCompletion`、`GetTextFile`、分析`Close()`及副本`Close(False)`。

第一轮请求包装错误在参数检查阶段失败，没有执行分析。第二轮发现：仅调换波长表顺序，专题仍采用主波长；同时修正探查程序对系统副本调用Close时遗漏False参数的问题。两轮原始异常及关闭回执保留。

第三轮四组视场/波长均在报告头确认，分别返回401行，四分析及四副本正常关闭，源设置、曲面和评价函数保持。这证明输入身份可以改变，尚未证明光学模型保持。

第四轮加入副本光学几何对照，发现主波长切换触发曲面6的MarginalRayAngle solve：半径由-18.377037272259606变为-18.398737323678674 mm，像面自动半口径也改变。该路径不能直接作为保留原模型的波长选择实现；记录明确失败并终止后续组合。

随后仅在副本把曲面6 RadiusCell和像面SemiDiameterCell固定为源模型数值，再改变输入。四组均确认输入身份，32个每组几何量按 `1e-12 + 1e-12×|source|` 对照通过；材料名称逐面一致。最初字符串严格相等误将原生数值写入的尾数变化判为几何变化，原始失败保留，最终使用预先写入程序的数值门槛复验。

## 命令、结果与资源生命周期

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
$env:PYTHONPATH='C:\Users\tonge\Desktop\mcp\src'
.venv/Scripts/python.exe -B -X utf8 scripts/probes/PO-01/phase_copy_selection.py .local/evidence/development/PO-01/phase-copy-selection-fixed-r2-20261109 --freeze
```

最终进程退出码0，`error=null`；四组`identity_matches/geometry_matches_source=true`，128项几何对照通过，最大绝对误差7.105427357601002e-15 mm；每组`tool_closed/copy_closed=true`，三类源模型状态保持。`state/close_receipt.json`中native.closed=true、error=null。原生FRU日志原样保留。探查为直接API执行，未创建MCP任务；不填写不存在的task_id或声称本轮已运行stdio/分页/取消。

台账更新并重新生成状态后，`tests/unit/test_development_status_report.py`定向检查20 passed（0.23秒），XML为`.local/evidence/development/PO-01/full-output-contract-20261109/status-unit.xml`。生成结果仍为94条源记录、91个编号、89组共同功能，完整7/10。没有触发集中全量回归或发行。

原始材料位于 `.local/evidence/development/PO-01/` 下的 `phase-copy-selection-20261109`、`phase-copy-selection-r2-20261109`、`phase-copy-selection-r3-20261109`、`phase-copy-selection-r4-20261109`、`phase-copy-selection-fixed-20261109`、`phase-copy-selection-fixed-r2-20261109`。每目录含probe.json，成功导出含原生UTF-16文本。

## 偏振光线完整出口的边界确认

程序集探查 `scripts/probes/PO-01/polarization_full_contract.py` 不创建应用，结果为 `.local/evidence/development/PO-01/full-output-contract-20261109/contracts.json`。记录完整参数名、方向和类型，而非只记录Double数量。

`IRayTraceNormPolData.ReadNextResultFull` 的输出为rayNumber、ErrorCode、XYZ、LMN、六个复电场实数及intensity；Direct版本增加vignetteCode。单光线Full接口对应相同物理输出。`GetGlobalMatrix`提供旋转及平移。所查接口没有逐界面的内部吸收、传播相位和入/出射偏振基底直接输出；这些接口组合尚不能覆盖完整专题。该结论限定于已检查的公开成员，不推断其他未验算法路径不存在。

## 探查阶段结论

相位专题的正式副本选择路径已有可执行依据，同时确认了主波长solve副作用及受控冻结办法。下一步先把副本冻结扩展到已声明的有效数值单元格、确认参数/配置/光线瞄准依赖和当前几何保持，再接入有类型请求、实际设置、失败关闭及取消；完成有限共轭/变换/镜面和原数值参考后判断整项完成。

偏振光线完整几何拼接路径暂不投入实现；已有29种CODA及默认原生专题继续保留。两项台账保持in_progress，不增加完整功能数。

## 公开请求交付与实际验收

已接入 `phase_aberration` 的 `method=auto/native/system_copy`、视场编号、波长编号与 Jones 输入。省略选择参数的默认调用沿用原生专题；显式选择通过自有 `CopySystem` 执行。副本冻结有效数值单元格中的依赖 solve，回读实际输入并核对源几何；分析对象和副本分别关闭，源模型保持。

几何核对采用 `1e-12 + 1e-12×|source|`；另用三条归一化真实光线比较状态、XYZ 和 LMN，门槛 `1e-9 + 1e-9×|source|`。Cooke 主波长由第二项改为第一项时，离轴见证光线最大差 `5.154093204594312e-5`，请求返回 `SETTING_REJECTED` 并关闭副本。非主波长选择的完整等价性仍待解决。

定向普通检查179项通过（2.176秒），证据 `.local/evidence/development/PO-01/phase-copy-unit-delivery-20261109.xml`。真实stdio用例1项通过（44.849秒），证据 `.local/evidence/development/PO-01/phase-copy-native-mapping-20261109.xml`；原始调用、检查和摘要位于 `.local/runs/runs/phase_copy_d1f76ad3ad/`。

本轮1604个相位值比较最大误差0，共1610项检查；6个任务正常关闭。已覆盖当前主波长、两个视场及非零X视场、Jones输入、start=7/count=11分页、PNG导出与查看、保存重载、非法编号、非主波长拒绝、失败后复用及源模型保持。请求取消后任务实际终态为 `succeeded`，实际 `cancelled` 终态仍待取得。会话正常断开。

下一步核对非主波长时正式瞳参数及光线瞄准依赖；在光学等价成立的模型中补有限共轭、变换、镜面和实际取消。当前条目保持 `in_progress`。
