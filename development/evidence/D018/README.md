# D018 候选模型、恢复与冻结条件比较

2026-11-11；主仓src源码基于a099540，发行基线1.1.0；Windows x64、Python3.14、OpticStudio2024R2/API24.2.0/build240529 Premium Standalone。

完成`manage_candidates`和`run_candidate_evaluation`。受保护基线、分支、具名检查点、恢复、持久索引和冻结条件比较公开可调用。候选和父候选关联进入现有任务context；已有优化预算、取消和历史机制沿用。模型快照记录曲面、solve、系统设置与全部配置；报价等外部指标带单位和来源，单列比较。

原生模型为635nm附近单色的受控双面球面透镜（本用例采用0.55µm，口径5mm，半径±50mm，N-BK7，厚3mm，后空气48mm）。同基线分出A/B/C：第一面半径45mm、材料N-F2、后空气49mm。按同一Centroid光斑及密度6评价。四候选全部成功，比较允许设计差异，光斑指标保留原生µm单位；每项原始数值见调用记录。

原生命令：`.venv/Scripts/python.exe -B -m pytest tests/native/test_candidates_live.py --run-zemax -q -s -p no:cacheprovider --basetemp .local/tmp/pytest-d018-native-final --junitxml=development/evidence/D018/native.xml`，1通过，19.71s。真实stdio覆盖基线/分支/选择/修改/检查点/评价/比较/分页/报告/恢复；将波长改为0.6µm的候选返回`EVALUATION_CONDITIONS_CHANGED`并恢复；取消取得cancelled终态并恢复。最终曲面与基线逐字段相同，正常disconnect。

原始证据：`.local/runs/runs/d018_candidates_f1584530ad/calls.json`、`checks.json`、`state/close_receipt.json`及设计索引。前次成功路径证据为`d018_candidates_ef71552b9b`；后次新增失败/取消验收使用上述final记录。

普通检查：候选、检索、建模能力、历史、项目资源与评价消费者共91通过，见[ordinary.xml](ordinary.xml)。覆盖重启后的索引读取、条件/单位不同、外部指标、非法编号、资源目录复制、SaveAs失败及Close失败时保留原始错误并进入重连。

结论：D018完成。最终统一发行时复验独立安装调用；使用指南为docs/guides/candidates.md。下一项D019。
