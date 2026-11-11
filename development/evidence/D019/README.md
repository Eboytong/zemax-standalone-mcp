# D019 联合玻璃搜索验收

日期2026-11-11。源码基线a099540加本轮未提交修改；实际导入`C:/Users/tonge/Desktop/mcp/src/zemax_mcp`。产品版本保持1.1.0。

实现`get_glass_slots`、联合赋值、cartesian/one_at_time/beam、总评价次数和时间预算、逐候选实际预算、目录身份回读、独立副本和D018候选归属。正式接口使用LDE、MaterialCatalog、CopySystem、LocalOptimization及SaveAs/LoadFile/Close(False)。

普通检查：`pytest tests/unit/test_glass_trials.py tests/unit/test_joint_glass.py tests/unit/test_candidates.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d019-unit --junitxml=development/evidence/D019/ordinary.xml`，35通过。覆盖三槽组合、去重、预算、类型边界及现有候选机制。

原生检查：`pytest tests/native/test_joint_glass_live.py --run-zemax -q -s -p no:cacheprovider --basetemp .local/tmp/pytest-d019-native --junitxml=development/evidence/D019/native.xml`，1通过，320.70秒。OpticStudio24.2.0/build240529 Premium，Python3.14。真实stdio建受控双材料胶合系统，毫米，三波长0.4861327/0.5875618/0.6562725µm，两视场。材料来自本机SCHOTT目录。

槽0为N-BK7/N-BAK4/N-FK5，槽1为N-F2/N-SF5/N-SF6。每组合使用相同厚度变量65—110mm、相同spot目标及Fixed_1_Cycle。9组合全部成功，与9次独立原材料对照逐项比较5项性能，共45次比较，最大绝对差0；容差预先为`1e-8 + 1e-7×abs(reference)`。终选独立重载各项误差0。beam及3次评价上限通过；保存候选可由D018读取并评价。基线曲面保持，副本关闭计数一致，stdio正常断开。

原始请求、回执、逐候选结果和检查：`.local/runs/runs/d019_joint_glass_1bb45b8128/`。第一次原生检查后修正预算计时起点、实际采用预算和空beam阶段推进；这些修改已通过上述35项普通检查，空beam阶段已在后续原生执行中通过，统一发行回归再次串行覆盖。

沿用D008单组材料筛选、solve保护及失败证据。联合取消专用用例在活动glass_native_optimization期间取消，取得cancelled终态，副本创建/关闭数一致，基线曲面保持，正常断开；native-cancel.xml记录1通过、39.32秒，原始目录为.local/runs/runs/d019_joint_glass_cancel_c2d9da3fa8/。native-close.xml保留先前等待progress而错过取消时机的失败记录；后续用例改为等待活动原生子任务，测试条件与实际取消对应。D019功能验收完成。参考G4固定commit及许可见`development/github-references.md`，本实现复用本仓原生执行链。

发行回归首次执行遇到状态查询60秒超时（release130-native.xml）。定位到显式材料池仍执行全目录扫描；修正为仅读取原材料和请求池，自动扫描每16项交还任务控制，取消时关闭目录资源。ordinary-cooperative.xml记录50项相关检查通过，含显式池无多余扫描、扫描中途关闭资源。修复后原生复测见统一发行记录。
