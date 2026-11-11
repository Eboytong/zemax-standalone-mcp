# D001—D010 集中检查

2026-11-11。源码fc814ef及工作区修改；主仓Windows x64/Python3.14，OpticStudio24.2.0/build240529/PremiumEdition。当前102工具/140分析请求。原生执行全程串行。

| 检查 | 结果 |
| --- | --- |
| 全量普通 | 3662 passed，30.74s |
| 十专题原生 | 14 passed，440.96s |
| 隔离构建与独立目录安装 | 成功，.local/builds/d001-d010 |
| 安装包真实stdio schema | 102工具、140分析请求，正常关闭 |
| 安装包真实stdio原生 | 鬼像主/副路径、候选、分页、PNG、重载、取消及断开，1 passed，26.65s |

构建为当前源码的本地检查包，沿用pyproject现有1.0.0版本号，保存在.local/builds；已发行releases中的1.0.0产物保持。目标发行仍为1.1.0。

首次普通回归3660通过、2失败：一处工具数预期仍为101，一处stdio子进程导入旧安装包。分别更新为102和显式主仓src后，全量3662通过。首次非隔离构建缺少setuptools.build_meta，改用pyproject声明的隔离构建成功；构建依赖安装在临时隔离环境。

## 原生用例

- `test_gradient2_gradient3_profiles_and_convergence`：通过，9.49s。
- `test_direct_coating_rta_stdio_fresnel_films_and_model_preservation`：通过，10.41s。
- `test_detector_viewer_current_and_zrd_stdio`：通过，16.41s。
- `test_manufacturing_geometry_stdio`：通过，16.71s。
- `test_pop_fiber_alignment_stdio`：通过，63.83s。
- `test_alignment_failure_reuse_and_budget`：通过，11.59s。
- `test_fixed_stack_native_optimizer_stdio`：通过，21.62s。
- `test_nsc_efficiency_scan_optimize_stdio`：通过，107.15s。
- `test_nsc_efficiency_random_rectangle_repeats`：通过，16.39s。
- `test_nsc_efficiency_budget_and_final_readback`：通过，16.63s。
- `test_glass_trials_native_stdio`：通过，85.10s。
- `test_glass_trials_radius_and_protection`：通过，19.04s。
- `test_scanner_4f_spacing_fold_aperture_stdio`：通过，20.44s。
- `test_ghost_plate_fresnel_candidates_and_lifecycle_stdio`：通过，24.72s。

## 原始记录与下一步

.local/evidence/development/D010中的concentrated-unit-final.txt/xml、concentrated-native.txt/xml、concentrated-build-isolated.txt、concentrated-install.txt、installed-schema/summary.json、installed-native.txt/xml及concentrated-summary.json。每个原生场景的calls/checks及模型保存在.local/runs/runs各自目录，入口由上述pytest日志和XML关联。

本轮覆盖D001—D010，完成数10/16，下一轮计数从0开始。继续D011共焦响应与有限针孔积分。D013保持已有正式接口阻塞。
