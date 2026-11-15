# OpticStudio 2026 R1 全功能试验

更新：2026-11-15T22:00:20.340385+08:00

原生测试：收集 904 项，已完成 904 项；通过 845、失败 48、跳过/预期限制 11。
已结束模块：289/289。当前状态：全部计划试验已结束。
工具调用覆盖：107/107；run_analysis 请求覆盖：146/146。
普通测试：{'total': 3777, 'passed': 3764, 'failed': 0, 'skipped': 13}。

结论：设置v261安装目录后，MCP可连接本机2026 R1并完成大部分建模、追迹、分析、优化和文件操作。当前结果包含下列未通过项目，需按具体功能采用测试结论。
环境：Python 3.14.10 x64，MCP 1.4.0，OpticStudio API 26.1.0 / build 260127，EnterpriseEdition。
使用仓库原生测试及补充覆盖用例，逐个独立进程串行执行；测试环境转发 v261 安装目录。测试夹具调整涉及安装路径、搬迁路径、目录计数和等待上限。首轮按模块限制1800秒，补跑按用例限制3600秒。产品源码保持原样。
覆盖表区分接口调用结果与后台任务终态；错误路径、预期限制和缺少外部输入均保留原始记录。
原先失败后复测通过：30项。已记录的工具中，至少一次返回成功的有106/107项；后台任务完成情况见分析覆盖表。
HPC读取在本机返回HPC_SETTINGS_UNAVAILABLE，相关5项测试按原生接口条件跳过；另有4项缺少历史数值输入或原生CFG预设，以及2项仓库预期失败。
STAR分析包含Cooke基准镜头的原始测试，以及用原生API预先导入FEA数据的补充镜头。补充镜头用于单独测试MCP拟合、读取、卸载和分析；MCP导入路径检查的原始失败记录保留。
STAR补测：变形及直接折射率的拟合、常量采样与卸载通过；温度数据卸载通过，恒温21°C输入的拟合采样返回0°C；刚体开关/参考点、组件配置和从FEA去除组件刚体通过，添加坐标断点返回SETTING_REJECTED。6类STAR分析在已导入并拟合FEA的镜头上均返回NO_RESULT_DATA，原生IsSTARModuleEnabled为true。
公开汇总见docs/compatibility/2026r1/；完整原始记录保留在测试机.local/full-2026r1/，其中保存collected-tests.json、test-results.jsonl、native-calls.jsonl、module-results.jsonl、各次pytest日志/XML、summary.json与feature-coverage.csv；光学输入和输出保存在.local/runs/。首轮、补跑和中断记录均保留。

## 已定位的产品代码问题

- `backend.py:1516`：评价函数目标/权重使用浮点严格相等比较。请求49.99999950000002、原生回读49.9999995，约2e-14差异触发SETTING_REJECTED。
- `star.py:235`：STAR导入要求回读文件名等于输入文本路径。本机导入后回读为Documents/Zemax/OBJECTS/STOP Files/*.zst，触发SETTING_REJECTED。
- `analyses.py:912`起的通用结果收集：受控抛物面镜FFT离焦MTF输出“计算终止; 无效的结果!”且无曲线/网格，任务仍标记succeeded。
原始调用、原生文本和首次失败记录均保留；本次功能试验中的产品源码保持原样。

## 当前未通过原因

| 类别 | 用例数 |
| --- | ---: |
| 原生离焦 MTF 无效结果仍标为成功 | 1 |
| IGES 多配置图层限制 | 1 |
| NSC 分组转换原生错误 | 3 |
| 材料 Abbe 数值参考超差 | 1 |
| 相干 FFT 线扩散数值参考超差 | 6 |
| PSF 傅里叶与原生 MTF 数值超差 | 4 |
| 散射路径 CDF 超差（观察到边界几何差异） | 1 |
| 评价函数浮点严格相等导致回读误拒绝 | 1 |
| 导入模型原生追迹出现错误光线 | 3 |
| 受控 .NET 回调装载返回空值 | 1 |
| CriticalRayData 原生结果不可用 | 1 |
| 路径阈值过滤后未提供未分类通量 | 1 |
| ABgFile 散射资源接口不可用 | 1 |
| QuickYield 瞳采样数值参考超差 | 2 |
| RMS 视场图数值参考超差 | 1 |
| 独立宏运行后未生成预期输出 | 1 |
| STAR 未返回有效数据 | 7 |
| STAR 导入回读为 ZST 容器路径 | 3 |
| 曲面 MTF 圆瞳参考超差 | 5 |
| 测试资源搬迁路径或历史输入缺失 | 1 |
| 曲面 MTF 与 PSF 傅里叶参考超差 | 1 |
| STAR 温度拟合采样为0（输入恒温21度） | 1 |
| STAR 组件刚体添加坐标断点未通过回读 | 1 |

## 工具覆盖

| 工具 | 已记录调用 | 返回成功 | 返回错误 |
| --- | ---: | ---: | ---: |
| cancel_task | 82 | 82 | 0 |
| clear_detectors | 7 | 7 | 0 |
| compare_results | 3 | 3 | 0 |
| connect | 887 | 887 | 0 |
| copy_editor_rows | 3 | 3 | 0 |
| copy_nsc_objects | 3 | 3 | 0 |
| copy_surfaces | 9 | 9 | 0 |
| copy_system | 1 | 1 | 0 |
| create_archive | 2 | 2 | 0 |
| delete_nsc_objects | 4 | 4 | 0 |
| delete_surfaces | 2 | 2 | 0 |
| disconnect | 867 | 867 | 0 |
| evaluate_merit_function | 167 | 167 | 0 |
| export_analysis_image | 302 | 298 | 4 |
| export_evaluation_report | 24 | 24 | 0 |
| export_point_cloud | 15 | 15 | 0 |
| generate_tolerances | 1 | 1 | 0 |
| get_beam_file | 426 | 426 | 0 |
| get_capabilities | 39 | 39 | 0 |
| get_coating_layers | 26 | 26 | 0 |
| get_coating_rta | 17 | 16 | 1 |
| get_configurations | 132 | 132 | 0 |
| get_constraint_coverage | 1 | 1 | 0 |
| get_design_tool_options | 6 | 6 | 0 |
| get_detector_data | 741 | 740 | 1 |
| get_editor_metadata | 3 | 3 | 0 |
| get_external_dependencies | 1 | 1 | 0 |
| get_glass_slots | 2 | 2 | 0 |
| get_historical_result | 2 | 2 | 0 |
| get_hpc_settings | 6 | 0 | 6 |
| get_lens_catalogs | 1 | 1 | 0 |
| get_material_properties | 20 | 20 | 0 |
| get_merit_function | 302 | 302 | 0 |
| get_nsc_object_geometry | 16 | 16 | 0 |
| get_nsc_objects | 200 | 198 | 2 |
| get_optimization_wizard_options | 4 | 4 | 0 |
| get_project_settings | 6 | 6 | 0 |
| get_request_status | 2 | 2 | 0 |
| get_star_data | 6 | 6 | 0 |
| get_status | 61 | 61 | 0 |
| get_surface_geometry | 371 | 371 | 0 |
| get_surfaces | 3531 | 3531 | 0 |
| get_system_resources | 79 | 75 | 4 |
| get_system_settings | 932 | 932 | 0 |
| get_system_summary | 43 | 43 | 0 |
| get_task_result | 4635 | 4635 | 0 |
| get_task_status | 10974 | 10974 | 0 |
| get_tolerances | 35 | 35 | 0 |
| get_variables | 8 | 8 | 0 |
| insert_editor_rows | 3 | 3 | 0 |
| insert_nsc_objects | 139 | 139 | 0 |
| insert_surfaces | 557 | 557 | 0 |
| list_task_history | 2 | 2 | 0 |
| load_archive | 2 | 2 | 0 |
| load_detector_data | 12 | 8 | 4 |
| load_merit_function | 1 | 1 | 0 |
| load_tolerance_file | 1 | 1 | 0 |
| manage_candidates | 18 | 18 | 0 |
| new_system | 670 | 669 | 1 |
| open_lens | 2711 | 2706 | 5 |
| read_zrd | 378 | 378 | 0 |
| run_analysis | 2119 | 2064 | 55 |
| run_batch_evaluation | 1 | 1 | 0 |
| run_batch_ray_trace | 648 | 648 | 0 |
| run_cad_export | 53 | 45 | 8 |
| run_candidate_evaluation | 4 | 4 | 0 |
| run_catalog_evaluation | 1 | 1 | 0 |
| run_catalog_lens | 2 | 2 | 0 |
| run_configuration_evaluation | 2 | 2 | 0 |
| run_design_tool | 8 | 8 | 0 |
| run_fft_mtf | 34 | 33 | 1 |
| run_global_optimization | 1 | 1 | 0 |
| run_hammer_optimization | 2 | 2 | 0 |
| run_layout_export | 9 | 9 | 0 |
| run_lens_catalog_search | 1 | 1 | 0 |
| run_local_optimization | 5 | 5 | 0 |
| run_merit_program | 6 | 6 | 0 |
| run_multistart_optimization | 5 | 5 | 0 |
| run_nsc_conversion | 15 | 7 | 8 |
| run_nsc_ray_trace | 557 | 556 | 1 |
| run_optimization_wizard | 5 | 5 | 0 |
| run_parameter_scan | 6 | 6 | 0 |
| run_pop | 208 | 208 | 0 |
| run_pop_convergence | 2 | 2 | 0 |
| run_quick_focus | 2 | 2 | 0 |
| run_speos_export | 3 | 3 | 0 |
| run_spot_analysis | 16 | 16 | 0 |
| run_standalone_macro | 1 | 1 | 0 |
| run_star_operation | 24 | 24 | 0 |
| run_tolerance_analysis | 83 | 83 | 0 |
| run_zrd_replay | 108 | 108 | 0 |
| save_detector_data | 4 | 4 | 0 |
| save_lens_as | 1468 | 1468 | 0 |
| save_merit_function | 1 | 1 | 0 |
| save_tolerance_file | 1 | 1 | 0 |
| search_capabilities | 4 | 4 | 0 |
| set_configuration | 64 | 64 | 0 |
| set_variables | 54 | 37 | 17 |
| summarize_tolerance_results | 15 | 15 | 0 |
| update_coating_layers | 9 | 9 | 0 |
| update_configurations | 45 | 45 | 0 |
| update_merit_function | 19 | 17 | 2 |
| update_nsc_objects | 648 | 646 | 2 |
| update_project_settings | 3 | 3 | 0 |
| update_surfaces | 2775 | 2608 | 167 |
| update_system_settings | 980 | 971 | 9 |
| update_tolerances | 109 | 109 | 0 |

## 分析请求覆盖

| 请求 | 调用 | 已受理 | 任务终态 |
| --- | ---: | ---: | --- |
| absorption_vs_angle | 10 | 10 | {'succeeded': 10} |
| absorption_vs_wavelength | 6 | 6 | {'succeeded': 6} |
| athermal_glass_map | 2 | 2 | {'succeeded': 2} |
| biocular_dipvergence_convergence | 10 | 9 | {'succeeded': 7, 'cancelled': 1, 'failed': 1} |
| biocular_field_of_view | 11 | 10 | {'succeeded': 8, 'cancelled': 1, 'failed': 1} |
| cardinal_points | 2 | 2 | {'succeeded': 2} |
| coating_listing | 1 | 1 | {'succeeded': 1} |
| coating_optimization | 6 | 5 | {'succeeded': 4, 'cancelled': 1} |
| configuration_matrix_spot | 1 | 1 | {'failed': 1} |
| confocal_response | 7 | 7 | {'failed': 3, 'cancelled': 1, 'succeeded': 3} |
| contrast_loss | 12 | 11 | {'succeeded': 10, 'cancelled': 1} |
| critical_ray_trace | 5 | 5 | {'succeeded': 3, 'cancelled': 1, 'failed': 1} |
| design_desensitize | 4 | 4 | {'failed': 2, 'cancelled': 1, 'succeeded': 1} |
| detector_viewer | 9 | 7 | {'succeeded': 6, 'cancelled': 1} |
| diattenuation_vs_angle | 7 | 7 | {'succeeded': 7} |
| diattenuation_vs_wavelength | 6 | 6 | {'succeeded': 6} |
| diff_efficiency_2d | 7 | 7 | {'cancelled': 2, 'succeeded': 5} |
| diff_efficiency_angular | 12 | 12 | {'failed': 2, 'succeeded': 10} |
| diff_efficiency_chromatic | 5 | 5 | {'succeeded': 5} |
| diffraction_encircled_energy | 35 | 35 | {'succeeded': 35} |
| directivity_plot | 2 | 2 | {'succeeded': 2} |
| dispersion_diagram | 14 | 12 | {'succeeded': 11, 'cancelled': 1} |
| dispersion_vs_wavelength | 9 | 9 | {'succeeded': 8, 'cancelled': 1} |
| extended_diffraction_image | 1 | 1 | {'succeeded': 1} |
| extended_source_encircled_energy | 25 | 23 | {'succeeded': 22, 'cancelled': 1} |
| fft_line_edge_spread | 50 | 49 | {'succeeded': 48, 'cancelled': 1} |
| fft_mtf_map | 4 | 4 | {'succeeded': 4} |
| fft_mtf_vs_field | 2 | 2 | {'succeeded': 2} |
| fft_psf | 54 | 54 | {'succeeded': 54} |
| fft_psf_cross | 1 | 1 | {'succeeded': 1} |
| fft_surface_mtf | 37 | 37 | {'succeeded': 37} |
| fft_through_focus_mtf | 2 | 2 | {'succeeded': 2} |
| fiber_alignment | 10 | 10 | {'succeeded': 8, 'cancelled': 1, 'failed': 1} |
| fiber_coupling_settings | 36 | 36 | {'succeeded': 35, 'cancelled': 1} |
| field_curvature_distortion | 1 | 1 | {'succeeded': 1} |
| file_comparator | 6 | 5 | {'succeeded': 5} |
| focal_shift | 1 | 1 | {'succeeded': 1} |
| footprint | 6 | 6 | {'succeeded': 6} |
| foucault | 17 | 14 | {'succeeded': 13, 'cancelled': 1} |
| fsm_control | 7 | 7 | {'failed': 2, 'succeeded': 4, 'cancelled': 1} |
| full_field_aberration | 20 | 19 | {'succeeded': 18, 'cancelled': 1} |
| full_field_spot | 3 | 3 | {'failed': 3} |
| geometric_bitmap_image | 9 | 7 | {'succeeded': 5, 'cancelled': 1, 'failed': 1} |
| geometric_encircled_energy | 2 | 2 | {'succeeded': 2} |
| geometric_image | 11 | 10 | {'succeeded': 9, 'cancelled': 1} |
| geometric_line_edge_spread | 14 | 13 | {'cancelled': 1, 'succeeded': 12} |
| geometric_mtf | 5 | 5 | {'succeeded': 5} |
| geometric_mtf_map | 5 | 5 | {'succeeded': 5} |
| geometric_mtf_vs_field | 2 | 2 | {'succeeded': 2} |
| geometric_through_focus_mtf | 1 | 1 | {'succeeded': 1} |
| ghost_diagnostics | 8 | 8 | {'succeeded': 6, 'cancelled': 1, 'failed': 1} |
| glass_map | 7 | 7 | {'succeeded': 7} |
| glass_trials | 27 | 27 | {'succeeded': 21, 'failed': 4, 'cancelled': 2} |
| grid_distortion | 2 | 2 | {'succeeded': 2} |
| grin_profile | 24 | 24 | {'succeeded': 24} |
| huygens_mtf | 54 | 54 | {'succeeded': 50, 'running': 4} |
| huygens_mtf_vs_field | 2 | 2 | {'succeeded': 2} |
| huygens_psf | 51 | 51 | {'succeeded': 51} |
| huygens_psf_cross | 1 | 1 | {'succeeded': 1} |
| huygens_surface_mtf | 27 | 26 | {'succeeded': 25, 'cancelled': 1} |
| huygens_through_focus_mtf | 1 | 1 | {'succeeded': 1} |
| ima_bim_viewer | 14 | 13 | {'succeeded': 12, 'cancelled': 1} |
| image_simulation | 24 | 23 | {'succeeded': 22, 'cancelled': 1} |
| incident_angle_vs_image_height | 23 | 21 | {'cancelled': 2, 'succeeded': 16, 'failed': 3} |
| interferogram | 24 | 22 | {'succeeded': 21, 'cancelled': 1} |
| internal_transmission_vs_wavelength | 2 | 2 | {'succeeded': 2} |
| lateral_color | 1 | 1 | {'succeeded': 1} |
| longitudinal_aberration | 1 | 1 | {'succeeded': 1} |
| manufacturing_geometry | 5 | 5 | {'succeeded': 4, 'cancelled': 1} |
| matrix_spot | 1 | 1 | {'failed': 1} |
| nsc_efficiency | 14 | 14 | {'succeeded': 11, 'failed': 2, 'cancelled': 1} |
| nsc_geometric_mtf | 35 | 35 | {'succeeded': 31, 'cancelled': 4} |
| nsc_single_ray_trace | 6 | 6 | {'succeeded': 5, 'cancelled': 1} |
| nsc_surface_sag | 15 | 15 | {'succeeded': 11, 'failed': 3, 'cancelled': 1} |
| opd_fan | 1 | 1 | {'succeeded': 1} |
| paraxial_gaussian_beam | 11 | 10 | {'succeeded': 9, 'cancelled': 1} |
| partially_coherent_image | 1 | 1 | {'succeeded': 1} |
| path_analysis | 9 | 9 | {'succeeded': 8, 'cancelled': 1} |
| phase_aberration | 10 | 8 | {'cancelled': 1, 'succeeded': 7} |
| phase_vs_angle | 9 | 8 | {'succeeded': 8} |
| phase_vs_wavelength | 9 | 9 | {'succeeded': 7, 'cancelled': 2} |
| polarization_pupil_map | 6 | 6 | {'succeeded': 6} |
| polarization_ray_trace | 25 | 24 | {'succeeded': 23, 'cancelled': 1} |
| polarization_transmission | 39 | 38 | {'succeeded': 37, 'cancelled': 1} |
| polarization_transmission_fan | 16 | 16 | {'succeeded': 15, 'cancelled': 1} |
| power_field_map | 94 | 94 | {'succeeded': 94} |
| power_pupil_map | 98 | 98 | {'succeeded': 97, 'cancelled': 1} |
| prescription_data | 4 | 4 | {'succeeded': 3, 'failed': 1} |
| pupil_aberration_fan | 7 | 7 | {'succeeded': 6, 'cancelled': 1} |
| quick_yield | 44 | 44 | {'succeeded': 43, 'cancelled': 1} |
| ray_database_viewer | 11 | 11 | {'succeeded': 10, 'cancelled': 1} |
| ray_fan | 5 | 5 | {'succeeded': 5} |
| reflection_vs_angle | 30 | 28 | {'succeeded': 28} |
| reflection_vs_wavelength | 14 | 14 | {'succeeded': 14} |
| relative_illumination | 3 | 3 | {'succeeded': 3} |
| retardance_vs_angle | 7 | 7 | {'succeeded': 7} |
| retardance_vs_wavelength | 6 | 6 | {'succeeded': 6} |
| rms_field_map | 6 | 4 | {'succeeded': 3, 'cancelled': 1} |
| rms_vs_field | 56 | 56 | {'succeeded': 56} |
| rms_vs_focus | 8 | 8 | {'succeeded': 8} |
| rms_vs_wavelength | 11 | 10 | {'succeeded': 9, 'cancelled': 1} |
| sag_table | 43 | 42 | {'succeeded': 38, 'cancelled': 3, 'failed': 1} |
| scan_pupil | 9 | 9 | {'succeeded': 7, 'cancelled': 1, 'failed': 1} |
| seidel_coefficients | 7 | 7 | {'succeeded': 7} |
| seidel_diagram | 11 | 10 | {'succeeded': 8, 'cancelled': 1, 'failed': 1} |
| sequential_energy_budget | 8 | 8 | {'cancelled': 1, 'succeeded': 7} |
| single_ray_trace | 4 | 4 | {'succeeded': 4} |
| skew_gaussian_beam | 12 | 11 | {'succeeded': 10, 'cancelled': 1} |
| source_spectrum_viewer | 3 | 3 | {'succeeded': 3} |
| star_2d_def_plot | 1 | 1 | {'failed': 1} |
| star_align_check | 1 | 1 | {'failed': 1} |
| star_index_vs_temp | 1 | 1 | {'failed': 1} |
| star_inspect_fea | 2 | 2 | {'failed': 2} |
| star_perf_change | 1 | 1 | {'failed': 1} |
| star_sys_viewer | 1 | 1 | {'failed': 1} |
| surface_curvature | 1 | 1 | {'succeeded': 1} |
| surface_curvature_cross | 1 | 1 | {'succeeded': 1} |
| surface_data | 1 | 1 | {'succeeded': 1} |
| surface_phase | 4 | 4 | {'succeeded': 4} |
| surface_phase_cross | 3 | 3 | {'succeeded': 3} |
| surface_phase_slope | 15 | 14 | {'succeeded': 13, 'cancelled': 1} |
| surface_phase_slope_cross | 15 | 14 | {'succeeded': 13, 'cancelled': 1} |
| surface_sag | 2 | 2 | {'succeeded': 2} |
| surface_sag_cross | 1 | 1 | {'succeeded': 1} |
| surface_slope | 17 | 16 | {'succeeded': 15, 'cancelled': 1} |
| surface_slope_cross | 23 | 22 | {'succeeded': 21, 'cancelled': 1} |
| system_check | 3 | 3 | {'succeeded': 3} |
| system_data | 2 | 2 | {'succeeded': 2} |
| test_plate_list | 13 | 12 | {'succeeded': 9, 'failed': 2, 'cancelled': 1} |
| thermal_compensation | 5 | 5 | {'failed': 2, 'succeeded': 2, 'cancelled': 1} |
| through_focus_spot | 5 | 5 | {'succeeded': 4, 'cancelled': 1} |
| tolerance_budget | 6 | 6 | {'succeeded': 3, 'failed': 2, 'cancelled': 1} |
| tolerance_histogram | 9 | 7 | {'succeeded': 7} |
| tolerance_yield | 7 | 5 | {'succeeded': 5} |
| transmission_vs_angle | 11 | 11 | {'succeeded': 11} |
| transmission_vs_wavelength | 6 | 6 | {'succeeded': 6} |
| universal_plot_1d | 56 | 53 | {'succeeded': 51, 'cancelled': 1, 'failed': 1} |
| universal_plot_2d | 25 | 24 | {'succeeded': 22, 'cancelled': 1, 'failed': 1} |
| vignetting | 2 | 2 | {'succeeded': 2} |
| wavefront | 291 | 291 | {'succeeded': 291} |
| yni_contributions | 7 | 7 | {'succeeded': 7} |
| yybar_diagram | 12 | 11 | {'succeeded': 10, 'cancelled': 1} |
| zernike_annular | 6 | 6 | {'succeeded': 6} |
| zernike_coefficients_vs_field | 18 | 18 | {'succeeded': 17, 'cancelled': 1} |
| zernike_fringe | 14 | 14 | {'succeeded': 14} |
| zernike_standard | 10 | 10 | {'succeeded': 10} |

## 原生失败与限制

### tests/native/test_analytic_analyses_live.py::test_parabolic_mirror_independent_references

结果：failed。

```text
tests\native\test_analytic_analyses_live.py:65: in test_parabolic_mirror_independent_references
    s=result["series"][0];target=0 if"through_focus"in kind else 50
      ^^^^^^^^^^^^^^^^
E   KeyError: 'series'
```

### tests/native/test_cad_layer_modes_live.py::test_cad_iges_solid_surface_layer_diagnostic

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_cad_layer_modes_live.py", line 46, in test_cad_iges_solid_surface_layer_diagnostic
  |     asyncio.run(execute('cad585_solid_surface_layers',guarded))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_cad_layer_modes_live.py", line 42, in guarded
      |     try:await work(e)
      |         ^^^^^^^^^^^^^
      |   File "<REPO>\tests\native\test_cad_layer_modes_live.py", line 26, in work
      |     result=await e.finish(await e.call('run_cad_export',dict(request=q)))
      |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': 'ce46c524f4354bdf9ea1dd7d62dae7c5', 'request_id': '4a35cff5f510472ebf6bc7e03a3e325b', 'kind': 'cad_export', 'state': 'failed', 'created_at': '2026-11-15T04:59:59.343269+00:00', 'finished_at': '2026-11-15T04:59:59.536882+00:00', 'progress': 0, 'native_progress': 0, 'status': 'None', 'can_cancel': False, 'cancel_requested': False, 'settings': {'FileType': 'IGES', 'Tolerance': 'N_TenEMinus4', 'IsAsynchronous': True, 'IsValid': True, 'CanCancel': False, 'IsFiniteDuration': True, 'FirstSurface': 1, 'LastSurface': 2, 'CanChangeSurface': True, 'FirstObject': -1, 'LastObject': -1, 'SequentialSettingsEnabled': True, 'RayPattern': 'XYFan', 'NumberOfRays': 0, 'Wavelength': 0, 'Field': 0, 'DeleteVignetted': True, 'RayLayer': 20, 'LensLayer': 10, 'DummyThickness': 1.0, 'SplineSegments': 'N_032', 'AngularTolerance': 'Low', 'Configuration': 4, 'NumConfig': 2, 'ExportDummySurfaces': False, 'SurfacesAsSolids': True, 'ScatterNSCRays': False, 'SplitNSCRays': False, 'UsePolarization': False, 'ExportRayFootprint': False, 'RayFootprintLayer': 0, 'ExportChiefRay': False, 'RayFilter': '', 'OutputFileName': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\True_all_by_layer.igs', 'AutoNameFaces': False, 'FileVersion': 'Current', 'IsCancelling': False, 'Progress': 0, 'Status': None, 'IsRunning': False, 'Succeeded': False, 'ErrorMessage': None, 'checked_fields': ['SurfacesAsSolids', 'ExportDummySurfaces', 'NumberOfRays', 'Field', 'Wavelength', 'Configuration', 'OutputFileName', 'FirstSurface', 'LastSurface', 'RayLayer', 'LensLayer', 'FileType', 'Tolerance'], 'requested': {'path': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\True_all_by_layer.igs', 'overwrite': False, 'format': 'IGES', 'start': 1, 'end': 2, 'surfaces_as_solids': True, 'export_dummy_surfaces': False, 'number_of_rays': 0, 'field': 0, 'wavelength': 0, 'tolerance': 'N_TenEMinus4', 'ray_pattern': None, 'delete_vignetted': None, 'ray_layer': 20, 'lens_layer': 10, 'dummy_thickness': None, 'spline_segments': None, 'angular_tolerance': None, 'scatter_nsc_rays': None, 'split_nsc_rays': None, 'use_polarization': None, 'auto_name_faces': None, 'file_version': None, 'configuration': None, 'configuration_mode': 'all_by_layer'}, 'configuration_selection': {'mode': 'all_by_layer', 'resolved_configuration': [1, 2], 'native_encoding': 4}}, 'context': {'session_id': '39672988488c4775910349847f2bac67', 'model_revision': 9, 'source_file': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\before.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\39672988488c4775910349847f2bac67\\working_06be9ea7.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\39672988488c4775910349847f2bac67\\checkpoint_r8_before_open_d0c79ecf.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 9, 'session_id': '39672988488c4775910349847f2bac67'}}, 'error': {'code': 'SETTING_REJECTED', 'message': 'IGES实际层号未采用请求。', 'details': {'setting': 'lens_layer', 'requested': [10, 11], 'actual': {'source': 'native IGES directory entry field5, columns33–40 of first DE record', 'directory_entries': 67, 'levels': [0, 65535], 'indirect_level_pointers': [], 'requested_levels': [10, 11], 'scope': 'explicit sequential lens layers with no exported rays'}, 'path': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\True_all_by_layer.igs'}}, 'close_attempted': True, 'result_path': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\39672988488c4775910349847f2bac67\\ce46c524f4354bdf9ea1dd7d62dae7c5.json', 'elapsed_seconds': 0.172}, 'checkpoint': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\39672988488c4775910349847f2bac67\\checkpoint_r8_before_open_d0c79ecf.zos', 'result_schema_version': 1, 'context': {'session_id': '39672988488c4775910349847f2bac67', 'model_revision': 9, 'source_file': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\before.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\39672988488c4775910349847f2bac67\\working_06be9ea7.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\cad585_solid_surface_layers_ebce10f38f\\39672988488c4775910349847f2bac67\\checkpoint_r8_before_open_d0c79ecf.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 9, 'session_id': '39672988488c4775910349847f2bac67'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_coating_nsc_probe_live.py::test_mixed_plate_coating_face_discovery

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_coating_nsc_probe_live.py", line 22, in test_mixed_plate_coating_face_discovery
  |     asyncio.run(execute('coating_nsc060_probe',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_coating_nsc_probe_live.py", line 21, in work
      |     await mixed_plate(e)
      |   File "<REPO>\tests\native\test_coating_nsc_probe_live.py", line 12, in mixed_plate
      |     converted=await e.finish(await e.call('run_nsc_conversion',dict(request=dict(first_surface=1,last_surface=4))))
      |                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 19, in call
      |     if okay:assert r and r["ok"],r
      |                    ^^^^^^^^^^^^^
      | AssertionError: {'ok': False, 'data': None, 'error': {'code': 'TASK_START_FAILED', 'message': 'An unknown error occurred', 'details': {'task_id': 'bfd3ac975a18407a986053407e4eaf11', 'command': 'run_nsc_conversion', 'partial_changes_possible': True}}, 'warnings': [], 'context': {'session_id': '7722716b0f1d4a46a485d519e46ffb70', 'model_revision': 8, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\coating_nsc060_probe_0130ad5723\\7722716b0f1d4a46a485d519e46ffb70\\working_331cc2fa.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\coating_nsc060_probe_0130ad5723\\7722716b0f1d4a46a485d519e46ffb70\\checkpoint_r7_convert_to_nsc_e53aeb17.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 8, 'session_id': '7722716b0f1d4a46a485d519e46ffb70'}, 'request_id': '87cc73946ce4448684858d5b0f7a181c'}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_conversion_live.py::test_nsc_group_conversion_reference_rays

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_conversion_live.py", line 35, in test_nsc_group_conversion_reference_rays
  |     asyncio.run(execute('conversion026_group',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_conversion_live.py", line 22, in work
      |     result=await e.finish(await e.call('run_nsc_conversion',dict(request=dict(first_surface=1,last_surface=last))))
      |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 19, in call
      |     if okay:assert r and r["ok"],r
      |                    ^^^^^^^^^^^^^
      | AssertionError: {'ok': False, 'data': None, 'error': {'code': 'TASK_START_FAILED', 'message': 'An unknown error occurred', 'details': {'task_id': '167ed49101254a58a69c2542a3883e60', 'command': 'run_nsc_conversion', 'partial_changes_possible': True}}, 'warnings': [], 'context': {'session_id': '357d90baf41c45d38745c5e11c8dfc63', 'model_revision': 4, 'source_file': '<USER_HOME>\\Documents\\Zemax\\Samples\\Sequential\\Objectives\\Cooke 40 degree field.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\conversion026_group_4cca0769f9\\357d90baf41c45d38745c5e11c8dfc63\\working_ad89cddd.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\conversion026_group_4cca0769f9\\357d90baf41c45d38745c5e11c8dfc63\\checkpoint_r3_convert_to_nsc_7db381b1.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 4, 'session_id': '357d90baf41c45d38745c5e11c8dfc63'}, 'request_id': '17b801a66fb74bf596c1250cee2940ec'}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_extended_solves_live.py::test_material_solves_numeric_stdio[model]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_extended_solves_live.py", line 77, in test_material_solves_numeric_stdio
  |     asyncio.run(execute("material_"+mode+"_numeric048",work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_extended_solves_live.py", line 57, in work
      |     e.check("model rounded Abbe from Snell",(nd-1)/(nf-nc),60,atol=1e-5)
      |     ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 35, in check
      |     assert passed,self.checks[-1]
      |            ^^^^^^
      | AssertionError: {'label': 'model rounded Abbe from Snell', 'actual': 59.99988524798844, 'expected': 60, 'atol': 1e-05, 'rtol': 1e-07, 'passed': False}
      +------------------------------------
```

### tests/native/test_fft_spread_coherent_live.py::test_fft_coherent_line_pupil_slice[interior-psf_auto-128]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 73, in test_fft_coherent_line_pupil_slice
  |     asyncio.run(execute(f'fft_spread513_{pupil_nodes}_{plot_sampling}_{pupil_size}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 72, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.005815089292018738, 'atol': 0.005, 'expected': 0, 'label': '-100 unaliased coherent pupil slice', ...}, {'actual': 0.005908416623084278, 'atol': 0.005, 'expected': 0, 'label': '-100.02 unaliased coherent pupil slice', ...}]
      | assert not [{'label': '-100 unaliased coherent pupil slice', 'actual': 0.005815089292018738, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': '-100.02 unaliased coherent pupil slice', 'actual': 0.005908416623084278, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_fft_spread_coherent_live.py::test_fft_coherent_line_pupil_slice[interior-dft_knots-64]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 73, in test_fft_coherent_line_pupil_slice
  |     asyncio.run(execute(f'fft_spread513_{pupil_nodes}_{plot_sampling}_{pupil_size}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 72, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.006259929127548747, 'atol': 0.005, 'expected': 0, 'label': '-100 unaliased coherent pupil slice', ...}, {'actual': 0.006093067889693715, 'atol': 0.005, 'expected': 0, 'label': '-100.02 unaliased coherent pupil slice', ...}]
      | assert not [{'label': '-100 unaliased coherent pupil slice', 'actual': 0.006259929127548747, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': '-100.02 unaliased coherent pupil slice', 'actual': 0.006093067889693715, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_fft_spread_coherent_live.py::test_fft_coherent_line_pupil_slice[interior-dft_knots-128]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 73, in test_fft_coherent_line_pupil_slice
  |     asyncio.run(execute(f'fft_spread513_{pupil_nodes}_{plot_sampling}_{pupil_size}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 72, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.005797966244510344, 'atol': 0.005, 'expected': 0, 'label': '-100 unaliased coherent pupil slice', ...}, {'actual': 0.005891249369564755, 'atol': 0.005, 'expected': 0, 'label': '-100.02 unaliased coherent pupil slice', ...}]
      | assert not [{'label': '-100 unaliased coherent pupil slice', 'actual': 0.005797966244510344, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': '-100.02 unaliased coherent pupil slice', 'actual': 0.005891249369564755, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_fft_spread_coherent_live.py::test_fft_coherent_line_pupil_slice[guard-psf_auto-128]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 73, in test_fft_coherent_line_pupil_slice
  |     asyncio.run(execute(f'fft_spread513_{pupil_nodes}_{plot_sampling}_{pupil_size}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 72, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.005915890743713292, 'atol': 0.005, 'expected': 0, 'label': '-100 unaliased coherent pupil slice', ...}, {'actual': 0.006008147348337822, 'atol': 0.005, 'expected': 0, 'label': '-100.02 unaliased coherent pupil slice', ...}]
      | assert not [{'label': '-100 unaliased coherent pupil slice', 'actual': 0.005915890743713292, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': '-100.02 unaliased coherent pupil slice', 'actual': 0.006008147348337822, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_fft_spread_coherent_live.py::test_fft_coherent_line_pupil_slice[guard-dft_knots-64]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 73, in test_fft_coherent_line_pupil_slice
  |     asyncio.run(execute(f'fft_spread513_{pupil_nodes}_{plot_sampling}_{pupil_size}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 72, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.005842474922190477, 'atol': 0.005, 'expected': 0, 'label': '-100 unaliased coherent pupil slice', ...}, {'actual': 0.005680027882594418, 'atol': 0.005, 'expected': 0, 'label': '-100.02 unaliased coherent pupil slice', ...}]
      | assert not [{'label': '-100 unaliased coherent pupil slice', 'actual': 0.005842474922190477, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': '-100.02 unaliased coherent pupil slice', 'actual': 0.005680027882594418, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_fft_spread_coherent_live.py::test_fft_coherent_line_pupil_slice[guard-dft_knots-128]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 73, in test_fft_coherent_line_pupil_slice
  |     asyncio.run(execute(f'fft_spread513_{pupil_nodes}_{plot_sampling}_{pupil_size}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_fft_spread_coherent_live.py", line 72, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.005899562541935577, 'atol': 0.005, 'expected': 0, 'label': '-100 unaliased coherent pupil slice', ...}, {'actual': 0.0059917599105314134, 'atol': 0.005, 'expected': 0, 'label': '-100.02 unaliased coherent pupil slice', ...}]
      | assert not [{'label': '-100 unaliased coherent pupil slice', 'actual': 0.005899562541935577, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': '-100.02 unaliased coherent pupil slice', 'actual': 0.0059917599105314134, 'expected': 0, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_finite_imaging_live.py::test_cooke_finite_psf_mtf_energy_native[1-3]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_finite_imaging_live.py", line 66, in test_cooke_finite_psf_mtf_energy_native
  |     asyncio.run(execute(f'finite_imaging_F{field}_W{wavelength}',work,role='fixture'))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_finite_imaging_live.py", line 65, in work
      |     assert records and all(r['passed']for r in records),[r for r in records if not r['passed']]
      | AssertionError: [{'actual': 0.12146849985032175, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.18350852502938744, ...}, {'actual': 0.16518328323723144, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.19976915775923285, ...}, {'actual': 0.12371097690061782, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.18373013748353628, ...}, {'actual': 0.16634099196083063, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.20005398547371578, ...}]
      | assert ([{'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.786852658951591, 'expected': 0.7817087955365245, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.13135694743820786, 'expected': 0.14236607221586572, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.1728889878235273, 'expected': 0.1709604280374819, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.8601937692663733, 'expected': 0.8570181182418163, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.426905371132565, 'expected': 0.42780871659948666, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.09960002367718385, 'expected': 0.10045760610434513, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.7865938043561438, 'expected': 0.7814230078134531, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.13325496122746527, 'expected': 0.14384526838426326, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.17215586623624368, 'expected': 0.17025551119028282, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.859346217885121, 'expected': 0.8561185775420225, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.4261458828978736, 'expected': 0.42699478505282296, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.09997806108866272, 'expected': 0.10078174317530571, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.7805869887271202, 'expected': 0.7979154872853058, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.12146849985032175, 'expected': 0.18350852502938744, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.16518328323723144, 'expected': 0.19976915775923285, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.8550843979969552, 'expected': 0.8531316978729782, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.42372731886736875, 'expected': 0.4278651179458041, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.10144170714965701, 'expected': 0.10178821587594322, 'atol': 0.02, 'passed': True}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 256, 'radius_um': 10, 'actual': 0.27248228167579996, 'expected': 0.2752600505616004, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 256, 'radius_um': 20, 'actual': 0.9487613726132083, 'expected': 0.9432942432808051, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.7814240933030553, 'expected': 0.8004385294862149, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.12371097690061782, 'expected': 0.18373013748353628, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.16634099196083063, 'expected': 0.20005398547371578, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.8555362924831657, 'expected': 0.8560851990902838, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.4249200352428627, 'expected': 0.42913427118203024, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.10144269296983324, 'expected': 0.10247479097961115, 'atol': 0.02, 'passed': True}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 512, 'radius_um': 10, 'actual': 0.2726709026822528, 'expected': 0.275481093386689, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 512, 'radius_um': 20, 'actual': 0.9451414075319438, 'expected': 0.9465817832330874, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}] and False)
      |  +  where False = all(<generator object test_cooke_finite_psf_mtf_energy_native.<locals>.work.<locals>.<genexpr> at 0x000002320D63A5A0>)
      +------------------------------------
```

### tests/native/test_finite_imaging_live.py::test_cooke_finite_psf_mtf_energy_native[2-3]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_finite_imaging_live.py", line 66, in test_cooke_finite_psf_mtf_energy_native
  |     asyncio.run(execute(f'finite_imaging_F{field}_W{wavelength}',work,role='fixture'))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_finite_imaging_live.py", line 65, in work
      |     assert records and all(r['passed']for r in records),[r for r in records if not r['passed']]
      | AssertionError: [{'actual': 0.4753918085547151, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.5178077108506904, ...}, {'actual': 0.10828310784054303, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.08690583025374356, ...}, {'actual': 0.4767694548527017, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.5190492509539719, ...}, {'actual': 0.10698716511049558, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.08665229121126367, ...}]
      | assert ([{'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8757762753154156, 'expected': 0.8730618975286756, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.48371592109668693, 'expected': 0.48313751241656544, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.11669218724216787, 'expected': 0.11739549573822275, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.8586605448523462, 'expected': 0.8556421323475016, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.4390342804766921, 'expected': 0.43994225954599225, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.11673201825061469, 'expected': 0.11741358117394403, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8747884409336577, 'expected': 0.8720414746225702, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.4839905739439979, 'expected': 0.4834227425771728, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.11473229330074794, 'expected': 0.1155524635692626, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.85778796209861, 'expected': 0.8547200798424487, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.43802119418533814, 'expected': 0.4388815443136999, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.11693553843472398, 'expected': 0.11756938686362382, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8681804093639578, 'expected': 0.8777256197765004, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.4753918085547151, 'expected': 0.5178077108506904, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.10828310784054303, 'expected': 0.08690583025374356, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.853101595240125, 'expected': 0.8516770974978868, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.4355274606887206, 'expected': 0.44015822427956414, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.11835341289738159, 'expected': 0.11899057871915182, 'atol': 0.02, 'passed': True}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 256, 'radius_um': 10, 'actual': 0.561079860430046, 'expected': 0.5549091549558561, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 256, 'radius_um': 20, 'actual': 0.9463633133504089, 'expected': 0.9425406145605593, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8684896485444776, 'expected': 0.8810756870522788, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.4767694548527017, 'expected': 0.5190492509539719, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.10698716511049558, 'expected': 0.08665229121126367, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.8535295329744136, 'expected': 0.8547182150447116, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.4365918698108281, 'expected': 0.4410443868212321, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.11843743080622536, 'expected': 0.11973104751968797, 'atol': 0.02, 'passed': True}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 512, 'radius_um': 10, 'actual': 0.5576968809368378, 'expected': 0.5560583558684399, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 512, 'radius_um': 20, 'actual': 0.9436338518972174, 'expected': 0.9460007021371879, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}] and False)
      |  +  where False = all(<generator object test_cooke_finite_psf_mtf_energy_native.<locals>.work.<locals>.<genexpr> at 0x0000019DBB403920>)
      +------------------------------------
```

### tests/native/test_finite_imaging_live.py::test_cooke_finite_psf_mtf_energy_native[3-3]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_finite_imaging_live.py", line 66, in test_cooke_finite_psf_mtf_energy_native
  |     asyncio.run(execute(f'finite_imaging_F{field}_W{wavelength}',work,role='fixture'))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_finite_imaging_live.py", line 65, in work
      |     assert records and all(r['passed']for r in records),[r for r in records if not r['passed']]
      | AssertionError: [{'actual': 0.4129495137795554, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.4350432821171999, ...}, {'actual': 0.41294965912512926, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.43543858162452814, ...}]
      | assert ([{'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8742253987149192, 'expected': 0.8737137972088839, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.6583360248161143, 'expected': 0.6584025606284359, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.42427990453956566, 'expected': 0.4240828734453444, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.9070136611711742, 'expected': 0.9051768615827994, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.6348746716538628, 'expected': 0.634601362204142, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.26554156394864686, 'expected': 0.2656527695844183, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8714668179920001, 'expected': 0.870921867528248, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.6544091305234068, 'expected': 0.6544661966974534, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.4210871488645468, 'expected': 0.4208889520062587, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.9062271163694154, 'expected': 0.9043476662594165, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.6338656341690142, 'expected': 0.6335547049534958, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.2646778228699992, 'expected': 0.26475689555376, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8650095807380267, 'expected': 0.8756194615311086, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.6470547591646875, 'expected': 0.6661917211668699, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.4129495137795554, 'expected': 0.4350432821171999, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.9008072744809148, 'expected': 0.9000923170506003, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.6284761128496102, 'expected': 0.6308605732166768, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.259639690132959, 'expected': 0.2619560880881896, 'atol': 0.02, 'passed': True}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 256, 'radius_um': 10, 'actual': 0.7364779380972653, 'expected': 0.729534730204989, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 256, 'radius_um': 20, 'actual': 0.930106662539908, 'expected': 0.9241641039966927, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8649006450268113, 'expected': 0.8779117558366073, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.6468186060353015, 'expected': 0.6666869307583966, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.41294965912512926, 'expected': 0.43543858162452814, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.9010526775678466, 'expected': 0.9040595522914849, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.6291717073903375, 'expected': 0.6331628911141105, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.2602691381865775, 'expected': 0.2627715113641093, 'atol': 0.02, 'passed': True}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 512, 'radius_um': 10, 'actual': 0.7313714647293023, 'expected': 0.7314216082858586, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 512, 'radius_um': 20, 'actual': 0.9258858141497313, 'expected': 0.9274534685352027, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}] and False)
      |  +  where False = all(<generator object test_cooke_finite_psf_mtf_energy_native.<locals>.work.<locals>.<genexpr> at 0x000001C2028039F0>)
      +------------------------------------
```

### tests/native/test_finite_scatter_live.py::test_finite_angle_sphere_transport_native[10]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_finite_scatter_live.py", line 87, in test_finite_angle_sphere_transport_native
  |     asyncio.run(execute('finite_scatter_'+str(angle),work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_finite_scatter_live.py", line 86, in work
      |     assert all(r['passed']for r in records),[r for r in records if not r['passed']]
      | AssertionError: [{'actual': 0.5365, 'atol': 0.026266263428294592, 'expected': 0.22448, 'label': 'path CDF 3mm', ...}]
      | assert False
      |  +  where False = all(<generator object test_finite_angle_sphere_transport_native.<locals>.work.<locals>.<genexpr> at 0x0000016CFB447920>)
      +------------------------------------
```

### tests/native/test_live.py::test_real_tools_over_stdio

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_live.py", line 162, in test_real_tools_over_stdio
  |     asyncio.run(scenario())
  |     ~~~~~~~~~~~^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\native\test_live.py", line 25, in scenario
  |     async with Client(params, read_timeout_seconds=90) as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\native\test_live.py", line 99, in scenario
      |     await call("update_merit_function", {"mode": "rms_spot_wizard", "operands": [
      |         {"type": "EFFL", "target": original["first_order"]["effective_focal_length"], "parameters": {"3": 2}}
      |     ]})
      |   File "<REPO>\tests\native\test_live.py", line 34, in call
      |     assert response["ok"], response
      | AssertionError: {'artifacts': [], 'context': {'checkpoint': '<REPO>\\.local\\runs\\runs\\live_e7343dedbe\\33d00ddd9c8d48e4941b170408166ea8\\checkpoint_r6_merit_044ee6ad.zos', 'configuration': 1, 'geometry': {'model_revision': 7, 'session_id': '33d00ddd9c8d48e4941b170408166ea8', 'state': 'pending'}, 'lens_units': 'Millimeters', ...}, 'data': None, 'error': {'code': 'SETTING_REJECTED', 'details': {'actual': 49.9999995, 'added_operands': [133], 'checkpoint': '<REPO>\\.local\\runs\\runs\\live_e7343dedbe\\33d00ddd9c8d48e4941b170408166ea8\\checkpoint_r6_merit_044ee6ad.zos', 'command': 'update_merit_function', ...}, 'message': '评价函数最终目标或权重未采用。'}, ...}
      | assert False
      +------------------------------------
```

### tests/native/test_model_cad_live.py::test_installed_mesh_geometry_native[oval.stl]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_model_cad_live.py", line 58, in test_installed_mesh_geometry_native
  |     asyncio.run(execute('adaptation_cad_'+name.replace('.','_'),work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_model_cad_live.py", line 47, in work
      |     _,segments=await trace(e,f'mesh_{transformed}_{reload}',use_polarization=True)
      |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\nsc.py", line 19, in trace
      |     r=await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(save_zrd=str(zrd),random_seed=42,**options))))
      |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': 'f442dbd323d64a0bbd9e21a0c1d36add', 'request_id': '10d8953854e14bb297c806f382c91f21', 'kind': 'nsc_ray_trace', 'state': 'failed', 'created_at': '2026-11-15T08:06:49.549695+00:00', 'finished_at': '2026-11-15T08:06:50.007635+00:00', 'progress': 0, 'native_progress': 0, 'status': 'None', 'can_cancel': True, 'cancel_requested': False, 'settings': {'IsAsynchronous': True, 'IsFiniteDuration': True, 'IsValid': True, 'CanCancel': True, 'RayMultiplier': 1.0, 'AutoUpdate': False, 'NumberOfCores': 1, 'UsePolarization': True, 'IgnoreErrors': False, 'SplitNSCRays': False, 'ScatterNSCRays': False, 'SaveRays': True, 'SaveRaysFile': 'mcp_c70472ac84fa4c52b257460c63743ec9.zrd', 'SavePaths': False, 'SavePathsFile': 'working_26daf210.PAF', 'ZRDFormat': 'CompressedFullData', 'Filter': '', 'DeadRayErrors': 0.0, 'DeadRayThreshold': 0.0, 'IsHPCEnabled': False, 'HPCEstimatedTimeS': 0.0, 'HPCRemainingTimeS': 0.0, 'HPCTimeToStartS': 0.0, 'HPCQueuePosition': 0, 'HPCState': 'NotRunning', 'HPCHasTimeEstimate': False, 'HasHPCUnsupportedDetectors': False, 'IsCancelling': False, 'Progress': 0, 'Status': None, 'IsRunning': False, 'Succeeded': False, 'ErrorMessage': None, 'detector_policy': 'clear', 'random_seed': 42, 'optical_model_snapshot': {'state': 'captured', 'object_count': 2, 'path': '<REPO>\\.local\\runs\\runs\\adaptation_cad_oval_stl_8bfed7e0e5\\8f1c1aa351a44452ae6ed2b737afc8e3\\nsc_model_snapshot_1a6a8a91da03401693993cd5f13d9010.json'}, 'trace_options': {'use_polarization': True, 'split_rays': False, 'scatter_rays': False, 'ignore_errors': False, 'number_of_cores': 1, 'random_seed': 42, 'filter': ''}}, 'context': {'session_id': '8f1c1aa351a44452ae6ed2b737afc8e3', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\adaptation_cad_oval_stl_8bfed7e0e5\\8f1c1aa351a44452ae6ed2b737afc8e3\\working_26daf210.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\adaptation_cad_oval_stl_8bfed7e0e5\\8f1c1aa351a44452ae6ed2b737afc8e3\\checkpoint_r4_nsc_objects_146a5f15.zos', 'requires_reconnect': False, 'mode': 'NonSequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '8f1c1aa351a44452ae6ed2b737afc8e3'}}, 'error': {'code': 'NSC_TRACE_ERRORS', 'message': '原生追迹出现错误光线；Succeeded不代表请求光线均已完成。', 'details': {'dead_ray_errors': 1.0, 'native_succeeded': True, 'native_zrd': '<REPO>\\.local\\runs\\runs\\adaptation_cad_oval_stl_8bfed7e0e5\\8f1c1aa351a44452ae6ed2b737afc8e3\\mcp_c70472ac84fa4c52b257460c63743ec9.zrd'}}, 'close_attempted': True, 'native_trace_complete': False, 'native_dead_ray_errors': 1.0, 'result_path': '<REPO>\\.local\\runs\\runs\\adaptation_cad_oval_stl_8bfed7e0e5\\8f1c1aa351a44452ae6ed2b737afc8e3\\f442dbd323d64a0bbd9e21a0c1d36add.json', 'elapsed_seconds': 0.457}, 'checkpoint': '<REPO>\\.local\\runs\\runs\\adaptation_cad_oval_stl_8bfed7e0e5\\8f1c1aa351a44452ae6ed2b737afc8e3\\checkpoint_r4_nsc_objects_146a5f15.zos', 'result_schema_version': 1, 'context': {'session_id': '8f1c1aa351a44452ae6ed2b737afc8e3', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\adaptation_cad_oval_stl_8bfed7e0e5\\8f1c1aa351a44452ae6ed2b737afc8e3\\working_26daf210.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\adaptation_cad_oval_stl_8bfed7e0e5\\8f1c1aa351a44452ae6ed2b737afc8e3\\checkpoint_r4_nsc_objects_146a5f15.zos', 'requires_reconnect': False, 'mode': 'NonSequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '8f1c1aa351a44452ae6ed2b737afc8e3'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_model_dll_live.py::test_object_dll_controlled_native[DiffractionGrating.DLL]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_model_dll_live.py", line 98, in test_object_dll_controlled_native
  |     asyncio.run(execute('adaptation_object_reference_'+name.replace('.','_'),work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_model_dll_live.py", line 86, in work
      |     result,segments=await trace(e,'object',use_polarization=True,split_rays=name=='DiffractionGrating.DLL')
      |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\nsc.py", line 19, in trace
      |     r=await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(save_zrd=str(zrd),random_seed=42,**options))))
      |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': 'fad72fdbe911427c9fc598825de8f2dc', 'request_id': '3b7758782e394d76bfb2c0c2389fc5d9', 'kind': 'nsc_ray_trace', 'state': 'failed', 'created_at': '2026-11-15T08:11:13.745838+00:00', 'finished_at': '2026-11-15T08:11:14.252617+00:00', 'progress': 0, 'native_progress': 0, 'status': 'None', 'can_cancel': True, 'cancel_requested': False, 'settings': {'IsAsynchronous': True, 'IsFiniteDuration': True, 'IsValid': True, 'CanCancel': True, 'RayMultiplier': 1.0, 'AutoUpdate': False, 'NumberOfCores': 1, 'UsePolarization': True, 'IgnoreErrors': False, 'SplitNSCRays': True, 'ScatterNSCRays': False, 'SaveRays': True, 'SaveRaysFile': 'mcp_a5425ef5270f4003810c015aff69e07b.zrd', 'SavePaths': True, 'SavePathsFile': 'working_a5c6ac50.PAF', 'ZRDFormat': 'CompressedFullData', 'Filter': '', 'DeadRayErrors': 0.0, 'DeadRayThreshold': 0.0, 'IsHPCEnabled': False, 'HPCEstimatedTimeS': 0.0, 'HPCRemainingTimeS': 0.0, 'HPCTimeToStartS': 0.0, 'HPCQueuePosition': 0, 'HPCState': 'NotRunning', 'HPCHasTimeEstimate': False, 'HasHPCUnsupportedDetectors': False, 'IsCancelling': False, 'Progress': 0, 'Status': None, 'IsRunning': False, 'Succeeded': False, 'ErrorMessage': None, 'detector_policy': 'clear', 'random_seed': 42, 'optical_model_snapshot': {'state': 'captured', 'object_count': 3, 'path': '<REPO>\\.local\\runs\\runs\\adaptation_object_reference_DiffractionGrating_DLL_5b07fcf54c\\41c3827cc94642cba91a79f444bb0b77\\nsc_model_snapshot_71e4bfd3120e4318bfd0cf91f3cb2847.json'}, 'trace_options': {'use_polarization': True, 'split_rays': True, 'scatter_rays': False, 'ignore_errors': False, 'number_of_cores': 1, 'random_seed': 42, 'filter': ''}}, 'context': {'session_id': '41c3827cc94642cba91a79f444bb0b77', 'model_revision': 4, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\adaptation_object_reference_DiffractionGrating_DLL_5b07fcf54c\\41c3827cc94642cba91a79f444bb0b77\\working_a5c6ac50.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\adaptation_object_reference_DiffractionGrating_DLL_5b07fcf54c\\41c3827cc94642cba91a79f444bb0b77\\checkpoint_r3_nsc_objects_e0ce52fd.zos', 'requires_reconnect': False, 'mode': 'NonSequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 4, 'session_id': '41c3827cc94642cba91a79f444bb0b77'}}, 'error': {'code': 'NSC_TRACE_ERRORS', 'message': '原生追迹出现错误光线；Succeeded不代表请求光线均已完成。', 'details': {'dead_ray_errors': 0.9500000000010113, 'native_succeeded': True, 'native_zrd': '<REPO>\\.local\\runs\\runs\\adaptation_object_reference_DiffractionGrating_DLL_5b07fcf54c\\41c3827cc94642cba91a79f444bb0b77\\mcp_a5425ef5270f4003810c015aff69e07b.zrd'}}, 'close_attempted': True, 'native_trace_complete': False, 'native_dead_ray_errors': 0.9500000000010113, 'result_path': '<REPO>\\.local\\runs\\runs\\adaptation_object_reference_DiffractionGrating_DLL_5b07fcf54c\\41c3827cc94642cba91a79f444bb0b77\\fad72fdbe911427c9fc598825de8f2dc.json', 'elapsed_seconds': 0.506}, 'checkpoint': '<REPO>\\.local\\runs\\runs\\adaptation_object_reference_DiffractionGrating_DLL_5b07fcf54c\\41c3827cc94642cba91a79f444bb0b77\\checkpoint_r3_nsc_objects_e0ce52fd.zos', 'result_schema_version': 1, 'context': {'session_id': '41c3827cc94642cba91a79f444bb0b77', 'model_revision': 4, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\adaptation_object_reference_DiffractionGrating_DLL_5b07fcf54c\\41c3827cc94642cba91a79f444bb0b77\\working_a5c6ac50.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\adaptation_object_reference_DiffractionGrating_DLL_5b07fcf54c\\41c3827cc94642cba91a79f444bb0b77\\checkpoint_r3_nsc_objects_e0ce52fd.zos', 'requires_reconnect': False, 'mode': 'NonSequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 4, 'session_id': '41c3827cc94642cba91a79f444bb0b77'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_net_callback_live.py::test_controlled_net_callback_loader_and_disposal

结果：failed。

```text
tests\native\test_net_callback_live.py:25: in test_controlled_net_callback_loader_and_disposal
    assert callback is not None, 'LoadNETCallback returned null for the controlled assembly/type/settings'
E   AssertionError: LoadNETCallback returned null for the controlled assembly/type/settings
E   assert None is not None
```

### tests/native/test_nsc_analyses_live.py::test_critical_controlled_pass_fail_and_model_restoration

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_nsc_analyses_live.py", line 54, in test_critical_controlled_pass_fail_and_model_restoration
  |     asyncio.run(execute('paths027_critical',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_nsc_analyses_live.py", line 50, in work
      |     result=await e.finish(await e.call('run_analysis',dict(request=dict(kind='critical_ray_trace',path=str(path),position_tolerance=1e-5,angle_tolerance_deg=1e-5))))
      |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': '6dd6fd57cdfd44f8b6d3d5539f46caa5', 'request_id': 'db57b4f9c531460c91e091384cda7760', 'kind': 'critical_ray_trace', 'state': 'failed', 'created_at': '2026-11-15T08:21:39.454294+00:00', 'finished_at': '2026-11-15T08:21:39.603799+00:00', 'progress': None, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'critical_ray_trace', 'requested': {'kind': 'critical_ray_trace', 'path': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\controlled.CRS', 'position_tolerance': 1e-05, 'angle_tolerance_deg': 1e-05, 'rays_to_display': 'AllRays', 'display_xyz': True, 'display_lmn': True, 'display_actual_end_data': True, 'display_target_end_data': True, 'display_start_data': True}, 'native': {'PositionTolerance': 1e-05, 'AngleTolerance': 1e-05, 'Filename': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\6ea846a5e75f48de8e7c8d8cf3f4d7e6\\critical_adabb5aecca44563bf6448bdfde1b072.CRS', 'RaysToDisplay': 'AllRays', 'DisplayXYZ': True, 'DisplayLMN': True, 'DisplayActualEndData': True, 'DisplayTargetEndData': True, 'DisplayStartData': True, 'IsValid': True, 'IsActiveWindow': True}, 'source_file': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\controlled.CRS', 'working_file': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\6ea846a5e75f48de8e7c8d8cf3f4d7e6\\critical_adabb5aecca44563bf6448bdfde1b072.CRS'}, 'context': {'session_id': '6ea846a5e75f48de8e7c8d8cf3f4d7e6', 'model_revision': 3, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\6ea846a5e75f48de8e7c8d8cf3f4d7e6\\working_faf98e58.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\6ea846a5e75f48de8e7c8d8cf3f4d7e6\\checkpoint_r2_nsc_objects_295ec27d.zos', 'requires_reconnect': False, 'mode': 'NonSequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 3, 'session_id': '6ea846a5e75f48de8e7c8d8cf3f4d7e6'}}, 'error': {'code': 'RESULT_UNAVAILABLE', 'message': '原生未提供CriticalRayData。', 'details': {'native_report': {'analysis_kind': 'critical_ray_trace', 'computation_method': 'native_analysis', 'rows': [], 'artifacts': [{'kind': 'native_text', 'path': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\6ea846a5e75f48de8e7c8d8cf3f4d7e6\\6dd6fd57cdfd44f8b6d3d5539f46caa5_native.txt'}], 'native_header': [], 'native_messages': []}}}, 'close_attempted': True, 'result_path': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\6ea846a5e75f48de8e7c8d8cf3f4d7e6\\6dd6fd57cdfd44f8b6d3d5539f46caa5.json', 'elapsed_seconds': 0.142}, 'checkpoint': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\6ea846a5e75f48de8e7c8d8cf3f4d7e6\\checkpoint_r2_nsc_objects_295ec27d.zos', 'result_schema_version': 1, 'context': {'session_id': '6ea846a5e75f48de8e7c8d8cf3f4d7e6', 'model_revision': 3, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\6ea846a5e75f48de8e7c8d8cf3f4d7e6\\working_faf98e58.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\paths027_critical_e957754ede\\6ea846a5e75f48de8e7c8d8cf3f4d7e6\\checkpoint_r2_nsc_objects_295ec27d.zos', 'requires_reconnect': False, 'mode': 'NonSequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 3, 'session_id': '6ea846a5e75f48de8e7c8d8cf3f4d7e6'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_nsc_conversion_live.py::test_nsc_group_conversion_reference_rays

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_nsc_conversion_live.py", line 35, in test_nsc_group_conversion_reference_rays
  |     asyncio.run(execute('conversion026_group',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_nsc_conversion_live.py", line 22, in work
      |     result=await e.finish(await e.call('run_nsc_conversion',dict(request=dict(first_surface=1,last_surface=last))))
      |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 19, in call
      |     if okay:assert r and r["ok"],r
      |                    ^^^^^^^^^^^^^
      | AssertionError: {'ok': False, 'data': None, 'error': {'code': 'TASK_START_FAILED', 'message': 'An unknown error occurred', 'details': {'task_id': 'ee13c9db3c3240bd9061e3df9acc8f17', 'command': 'run_nsc_conversion', 'partial_changes_possible': True}}, 'warnings': [], 'context': {'session_id': '231a09059c7544c0bc6c53776a1c3845', 'model_revision': 4, 'source_file': '<USER_HOME>\\Documents\\Zemax\\Samples\\Sequential\\Objectives\\Cooke 40 degree field.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\conversion026_group_4daa425a91\\231a09059c7544c0bc6c53776a1c3845\\working_53da9475.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\conversion026_group_4daa425a91\\231a09059c7544c0bc6c53776a1c3845\\checkpoint_r3_convert_to_nsc_e883ac15.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 4, 'session_id': '231a09059c7544c0bc6c53776a1c3845'}, 'request_id': '2d14cdf0131842dbbd9c45cfb0a6d835'}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_nsc_paths_reference_live.py::test_path_uncategorized_flux_against_independent_database_sum

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_nsc_paths_reference_live.py", line 113, in test_path_uncategorized_flux_against_independent_database_sum
  |     asyncio.run(execute('paths063_uncategorized',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_nsc_paths_reference_live.py", line 109, in work
      |     assert result['uncategorized'] is not None,result.get('uncategorized_native_message')
      | AssertionError: There are no uncategorized paths.
      | assert None is not None
      +------------------------------------
```

### tests/native/test_property_pages_live.py::test_property_pages_stdio

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_property_pages_live.py", line 38, in test_property_pages_stdio
  |     asyncio.run(execute('property_pages',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_property_pages_live.py", line 29, in work
      |     result=await e.call('get_system_resources',{'request':{'kind':'scattering_files','scattering_type':kind}},okay=kind not in {'User','BSDF'})
      |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 19, in call
      |     if okay:assert r and r["ok"],r
      |                    ^^^^^^^^^^^^^
      | AssertionError: {'ok': False, 'data': None, 'error': {'code': 'UNSUPPORTED_SETTING', 'message': '本机该散射类型的资源接口没有返回可用资源。', 'details': {'type': 'ABgFile', 'resource_query': 'GetAvailableFileNames', 'placeholder_values': ['无'], 'native_names': ['无'], 'command': 'get_system_resources', 'partial_changes_possible': False}}, 'warnings': [], 'context': {'session_id': 'a39eb924bc0047aba4b18e3753603272', 'model_revision': 16, 'source_file': '<USER_HOME>\\Documents\\Zemax\\Samples\\Sequential\\Objectives\\Cooke 40 degree field.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\property_pages_5f66d116e2\\a39eb924bc0047aba4b18e3753603272\\working_21a2b81d.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\property_pages_5f66d116e2\\a39eb924bc0047aba4b18e3753603272\\checkpoint_r15_settings_06b6ccf6.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 16, 'session_id': 'a39eb924bc0047aba4b18e3753603272'}, 'request_id': '1c892ee55da34c1f8bd14f30ef1b0586'}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_quick_yield_refractive_live.py::test_quick_yield_refractive_fit_diagnostic[3]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_quick_yield_refractive_live.py", line 75, in test_quick_yield_refractive_fit_diagnostic
  |     asyncio.run(execute('quickyield572_refractive_'+str(angle),work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_quick_yield_refractive_live.py", line 68, in work
      |     for record in records:e.check('field'+str(record['field'])+' uniform-area batch versus GaussQuad',
      |                           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |         record['gauss_quad_rms'],record['batch_reference_rms'],atol=1e-5,rtol=.01)
      |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 35, in check
      |     assert passed,self.checks[-1]
      |            ^^^^^^
      | AssertionError: {'label': 'field2 uniform-area batch versus GaussQuad', 'actual': 0.18174988988464108, 'expected': 0.19253773305191196, 'atol': 1e-05, 'rtol': 0.01, 'passed': False}
      +------------------------------------
```

### tests/native/test_quick_yield_refractive_live.py::test_quick_yield_refractive_fit_diagnostic[6]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_quick_yield_refractive_live.py", line 75, in test_quick_yield_refractive_fit_diagnostic
  |     asyncio.run(execute('quickyield572_refractive_'+str(angle),work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_quick_yield_refractive_live.py", line 68, in work
      |     for record in records:e.check('field'+str(record['field'])+' uniform-area batch versus GaussQuad',
      |                           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |         record['gauss_quad_rms'],record['batch_reference_rms'],atol=1e-5,rtol=.01)
      |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 35, in check
      |     assert passed,self.checks[-1]
      |            ^^^^^^
      | AssertionError: {'label': 'field2 uniform-area batch versus GaussQuad', 'actual': 0.7183109424707351, 'expected': 0.7311379201455365, 'atol': 1e-05, 'rtol': 0.01, 'passed': False}
      +------------------------------------
```

### tests/native/test_rms_map_reference_live.py::test_rms_map_native_quadrature

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_rms_map_reference_live.py", line 76, in test_rms_map_native_quadrature
  |     asyncio.run(execute('rmsmap078',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_rms_map_reference_live.py", line 62, in work
      |     e.check('map '+reference+' '+metric,grid['values'][iy][ix],expected,atol=.05,rtol=.01)
      |     ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 35, in check
      |     assert passed,self.checks[-1]
      |            ^^^^^^
      | AssertionError: {'label': 'map Centroid SpotRadius', 'actual': 7.576542632172178, 'expected': 7.095468368553093, 'atol': 0.05, 'rtol': 0.01, 'passed': False}
      +------------------------------------
```

### tests/native/test_spectral_phosphor_live.py::test_installed_phosphor_reference_native

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_spectral_phosphor_live.py", line 59, in test_installed_phosphor_reference_native
  |     asyncio.run(execute("phosphor_installed_resource",work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_spectral_phosphor_live.py", line 44, in work
      |     _,segments=await trace(e,"phosphor",scatter_rays=True,max_segments=30000)
      |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\nsc.py", line 19, in trace
      |     r=await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(save_zrd=str(zrd),random_seed=42,**options))))
      |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': 'c7822a7582bf401cb1ff004ec7cd703d', 'request_id': '75724d7165c34fd7b0ef78d7954fd4c4', 'kind': 'nsc_ray_trace', 'state': 'failed', 'created_at': '2026-11-15T09:57:34.110355+00:00', 'finished_at': '2026-11-15T09:57:34.595826+00:00', 'progress': 0, 'native_progress': 0, 'status': 'None', 'can_cancel': True, 'cancel_requested': False, 'settings': {'IsAsynchronous': True, 'IsFiniteDuration': True, 'IsValid': True, 'CanCancel': True, 'RayMultiplier': 1.0, 'AutoUpdate': False, 'NumberOfCores': 1, 'UsePolarization': False, 'IgnoreErrors': False, 'SplitNSCRays': False, 'ScatterNSCRays': True, 'SaveRays': True, 'SaveRaysFile': 'mcp_ac06dab3c14c4e1aaaa5ce4a1adc5caa.zrd', 'SavePaths': False, 'SavePathsFile': 'working_28f06849.PAF', 'ZRDFormat': 'CompressedFullData', 'Filter': '', 'DeadRayErrors': 0.0, 'DeadRayThreshold': 0.0, 'IsHPCEnabled': False, 'HPCEstimatedTimeS': 0.0, 'HPCRemainingTimeS': 0.0, 'HPCTimeToStartS': 0.0, 'HPCQueuePosition': 0, 'HPCState': 'NotRunning', 'HPCHasTimeEstimate': False, 'HasHPCUnsupportedDetectors': False, 'IsCancelling': False, 'Progress': 0, 'Status': None, 'IsRunning': False, 'Succeeded': False, 'ErrorMessage': None, 'detector_policy': 'clear', 'random_seed': 42, 'optical_model_snapshot': {'state': 'captured', 'object_count': 3, 'path': '<REPO>\\.local\\runs\\runs\\phosphor_installed_resource_15fcc6d792\\6f154fe1d7cd4193b7cfccd9621f3bef\\nsc_model_snapshot_4cc255169bfe4cb6a09bf2e7e4006a50.json'}, 'trace_options': {'use_polarization': False, 'split_rays': False, 'scatter_rays': True, 'ignore_errors': False, 'number_of_cores': 1, 'random_seed': 42, 'filter': ''}}, 'context': {'session_id': '6f154fe1d7cd4193b7cfccd9621f3bef', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\phosphor_installed_resource_15fcc6d792\\6f154fe1d7cd4193b7cfccd9621f3bef\\working_28f06849.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\phosphor_installed_resource_15fcc6d792\\6f154fe1d7cd4193b7cfccd9621f3bef\\checkpoint_r4_nsc_objects_f1f49b73.zos', 'requires_reconnect': False, 'mode': 'NonSequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '6f154fe1d7cd4193b7cfccd9621f3bef'}}, 'error': {'code': 'NSC_TRACE_ERRORS', 'message': '原生追迹出现错误光线；Succeeded不代表请求光线均已完成。', 'details': {'dead_ray_errors': 0.0016112682322880641, 'native_succeeded': True, 'native_zrd': '<REPO>\\.local\\runs\\runs\\phosphor_installed_resource_15fcc6d792\\6f154fe1d7cd4193b7cfccd9621f3bef\\mcp_ac06dab3c14c4e1aaaa5ce4a1adc5caa.zrd'}}, 'close_attempted': True, 'native_trace_complete': False, 'native_dead_ray_errors': 0.0016112682322880641, 'result_path': '<REPO>\\.local\\runs\\runs\\phosphor_installed_resource_15fcc6d792\\6f154fe1d7cd4193b7cfccd9621f3bef\\c7822a7582bf401cb1ff004ec7cd703d.json', 'elapsed_seconds': 0.485}, 'checkpoint': '<REPO>\\.local\\runs\\runs\\phosphor_installed_resource_15fcc6d792\\6f154fe1d7cd4193b7cfccd9621f3bef\\checkpoint_r4_nsc_objects_f1f49b73.zos', 'result_schema_version': 1, 'context': {'session_id': '6f154fe1d7cd4193b7cfccd9621f3bef', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\phosphor_installed_resource_15fcc6d792\\6f154fe1d7cd4193b7cfccd9621f3bef\\working_28f06849.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\phosphor_installed_resource_15fcc6d792\\6f154fe1d7cd4193b7cfccd9621f3bef\\checkpoint_r4_nsc_objects_f1f49b73.zos', 'requires_reconnect': False, 'mode': 'NonSequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '6f154fe1d7cd4193b7cfccd9621f3bef'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_standalone_macro_live.py::test_standalone_macro_arguments_output_and_process_close

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_standalone_macro_live.py", line 50, in test_standalone_macro_arguments_output_and_process_close
  |     asyncio.run(scenario())
  |     ~~~~~~~~~~~^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\native\test_standalone_macro_live.py", line 28, in scenario
  |     async with Client(params, read_timeout_seconds=120) as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\native\test_standalone_macro_live.py", line 46, in scenario
      |     assert "ARGUMENT=" in output.read_text(encoding="utf-8")
      |                           ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\pathlib\__init__.py", line 787, in read_text
      |     with self.open(mode='r', encoding=encoding, errors=errors, newline=newline) as f:
      |          ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\pathlib\__init__.py", line 771, in open
      |     return io.open(self, mode, buffering, encoding, errors, newline)
      |            ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      | FileNotFoundError: [Errno 2] No such file or directory: '<REPO>\\.local\\runs\\runs\\standalone_macro_30af87f29c\\macro_result.txt'
      +------------------------------------
```

### tests/native/test_star_analysis_live.py::test_star_analysis_availability_and_generic_creation

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_star_analysis_live.py", line 29, in test_star_analysis_availability_and_generic_creation
  |     asyncio.run(execute('d012r1', work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_star_analysis_live.py", line 25, in work
      |     attempts = [await probe_kind(e, kind) for kind in KINDS]
      |                 ^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\star_analysis_probe.py", line 50, in probe_kind
      |     payload = await evidence.finish(response)
      |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': 'cbdf687e56c54af5937ce5568715d260', 'request_id': '98745bd2945449a48248d4b71f0c40c6', 'kind': 'star_inspect_fea', 'state': 'failed', 'created_at': '2026-11-15T09:59:20.451601+00:00', 'finished_at': '2026-11-15T09:59:20.532876+00:00', 'progress': None, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'star_inspect_fea', 'analysis': 'star_inspect_fea', 'native_analysis': 'STARInspectFEA', 'analysis_id': 160, 'requested': {'kind': 'star_inspect_fea'}, 'native': {'IsValid': True, 'IsActiveWindow': True}, 'settings_surface': [], 'settings_support': 'probed at run time; no IAS_ interface is documented for this analysis', 'availability': {'enabled': True, 'source': 'live read of IZOSAPI_Application.IsSTARModuleEnabled'}}, 'context': {'session_id': 'a457704d52c344048bd4520c73c8cfb4', 'model_revision': 1, 'source_file': '<USER_HOME>\\Documents\\Zemax\\Samples\\Sequential\\Objectives\\Cooke 40 degree field.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\d012r1_b312672240\\a457704d52c344048bd4520c73c8cfb4\\working_0024e7c7.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'a457704d52c344048bd4520c73c8cfb4'}}, 'error': {'code': 'NO_RESULT_DATA', 'message': 'STAR 专题分析没有提供有效的曲线、网格或散点。', 'details': {'analysis': 'star_inspect_fea', 'native_messages': [], 'native_header': [], 'text_export': {'attempted': True, 'exported': False, 'path': None, 'error': 'GetTextFile returned false', 'line_count': None, 'non_blank_lines': None, 'encoding': 'utf-16'}, 'empty_collections': [], 'note': 'an exported but empty or title-only text file, an empty series or an empty scatter block is not a valid result; only non-empty series, grids and scatter points are'}}, 'close_attempted': True, 'result_path': '<REPO>\\.local\\runs\\runs\\d012r1_b312672240\\a457704d52c344048bd4520c73c8cfb4\\cbdf687e56c54af5937ce5568715d260.json', 'elapsed_seconds': 0.076}, 'checkpoint': None, 'result_schema_version': 1, 'context': {'session_id': 'a457704d52c344048bd4520c73c8cfb4', 'model_revision': 1, 'source_file': '<USER_HOME>\\Documents\\Zemax\\Samples\\Sequential\\Objectives\\Cooke 40 degree field.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\d012r1_b312672240\\a457704d52c344048bd4520c73c8cfb4\\working_0024e7c7.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'a457704d52c344048bd4520c73c8cfb4'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_star_live.py::test_native_star_controlled_constant_data_and_shutdown[deformation]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_star_live.py", line 40, in test_native_star_controlled_constant_data_and_shutdown
  |     asyncio.run(execute('star_'+data_kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_star_live.py", line 22, in work
      |     imported=await e.finish(await e.call('run_star_operation',{'request':{
      |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |         'kind':'import_'+data_kind,'surface':1,'path':str(source),
      |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |         'coordinate_system':'local','length_unit':'Millimeters'}}))
      |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'rows': [], 'summary': {}, 'restoration': {'restored': True, 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\checkpoint_r5_star_import_deformation_da207bf0.zos', 'context': {'session_id': '771b1396889e4ccf9014f1c17f25e1fb', 'model_revision': 7, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\working_a23eacab.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\checkpoint_r5_star_import_deformation_da207bf0.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 7, 'session_id': '771b1396889e4ccf9014f1c17f25e1fb'}}}, 'baseline': {'path': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\checkpoint_r5_star_import_deformation_da207bf0.zos', 'context': {'session_id': '771b1396889e4ccf9014f1c17f25e1fb', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\working_a23eacab.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\checkpoint_r4_surfaces_f235878b.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '771b1396889e4ccf9014f1c17f25e1fb'}}}, 'error': {'code': 'SETTING_REJECTED', 'message': 'STAR import file did not match on readback.', 'details': {'requested': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\star_input_07ab1f8662c5406f99e57790200397a8\\controlled_deformation.txt', 'actual': '<USER_HOME>\\Documents\\Zemax\\OBJECTS\\STOP Files\\269129.zst'}}, 'operation': 'import_deformation', 'data_kind': 'deformation', 'cancellation': 'cooperative between native calls; an active import/refit call completes before cancellation', 'source_resource': {'source': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\controlled_deformation.txt', 'staged': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\star_input_07ab1f8662c5406f99e57790200397a8\\controlled_deformation.txt', 'length_unit': 'Millimeters', 'coordinate_system': 'local'}, 'result_schema_version': 1, 'task': {'task_id': '346f0e3791ac4ed5898543372ef829d6', 'request_id': 'f1cd2f5257cd4365963567ee698fe9a0', 'kind': 'star_operation', 'state': 'failed', 'created_at': '2026-11-15T10:00:25.515604+00:00', 'finished_at': '2026-11-15T10:00:25.612366+00:00', 'progress': 0, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'import_deformation', 'surface': 1, 'path': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\controlled_deformation.txt', 'coordinate_system': 'local', 'length_unit': 'Millimeters'}, 'context': {'session_id': '771b1396889e4ccf9014f1c17f25e1fb', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\working_a23eacab.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\checkpoint_r4_surfaces_f235878b.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '771b1396889e4ccf9014f1c17f25e1fb'}}, 'error': {'code': 'SETTING_REJECTED', 'message': 'STAR import file did not match on readback.', 'details': {'requested': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\star_input_07ab1f8662c5406f99e57790200397a8\\controlled_deformation.txt', 'actual': '<USER_HOME>\\Documents\\Zemax\\OBJECTS\\STOP Files\\269129.zst'}}, 'result_path': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\346f0e3791ac4ed5898543372ef829d6.json', 'result_artifacts': [{'kind': 'json', 'path': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\346f0e3791ac4ed5898543372ef829d6.json'}], 'elapsed_seconds': 0.086}, 'context': {'session_id': '771b1396889e4ccf9014f1c17f25e1fb', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\working_a23eacab.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\checkpoint_r4_surfaces_f235878b.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '771b1396889e4ccf9014f1c17f25e1fb'}}, 'system_settings': {'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'source_units': 'Watts', 'source_unit_prefix': 'None', 'analysis_units': 'WattsPerCMSq', 'analysis_unit_prefix': 'None', 'afocal_image_space': False, 'aperture': {'type': 'EntrancePupilDiameter', 'value': 10.0}, 'field_type': 'Angle', 'field_normalization': 'Radial', 'fields': [{'number': 1, 'x': 0.0, 'y': 0.0, 'weight': 1.0, 'vdx': 0.0, 'vdy': 0.0, 'vcx': 0.0, 'vcy': 0.0, 'van': 0.0}], 'wavelength_unit': 'micrometers (environmental air reference)', 'wavelengths': [{'number': 1, 'wavelength_um': 0.55, 'weight': 1.0, 'primary': True}], 'temperature_c': 20.0, 'pressure_atm': 1.0, 'adjust_index_to_environment': False, 'afocal_mode_units': 'Milliradians', 'settings_activity': {'apodization_factor_is_used': False}, 'author': '', 'aperture_options': {'apodization_type': 'Uniform', 'apodization_factor': 0.0, 'semi_diameter_margin': 0.0, 'semi_diameter_margin_pct': 0.0, 'telecentric_object_space': False, 'afocal_image_space': False, 'iterate_solves_when_updating': False, 'fast_semi_diameters': True, 'check_grin_apertures': False}, 'advanced': {'reference_opd': 'ExitPupil', 'paraxial_rays': 'IgnoreCoordinateBreaks', 'f_num_method': 'TracingRays', 'dont_print_coordinate_break_data': False, 'turn_off_threading': False, 'opd_modulo_2pi': False, 'include_calculated_data_in_session_file': True, 'include_tolerance_data_in_session_file': True, 'huygens_integral_method': 'Auto'}, 'global_reference_surface': 2, 'material_catalogs': ['SCHOTT'], 'polarization': {'unpolarized': True, 'jx': 0.0, 'jy': 1.0, 'x_phase': 0.0, 'y_phase': 0.0, 'method': 'XAxisMethod', 'convert_thin_film_phase': True}, 'ray_aiming': {'mode': 'Off', 'method': 'Heuristic', 'cache': True, 'robust': False, 'scale_pupil_shift_by_field': False, 'auto_pupil_shift': True, 'enhanced': False, 'advanced_convergence': False, 'fallback_search': False, 'pupil_shift_x': 0.0, 'pupil_shift_y': 0.0, 'pupil_shift_z': 0.0, 'pupil_compress_x': 0.0, 'pupil_compress_y': 0.0, 'cache_steps': 10}, 'files': {'coating_file': 'COATING.DAT', 'scatter_profile': 'SCATTER_PROFILE.DAT', 'abg_file': 'ABG_DATA.DAT', 'gradium_profile': 'PROFILE.GRD'}, 'title': '', 'notes': ''}, 'artifacts': [{'kind': 'json', 'path': '<REPO>\\.local\\runs\\runs\\star_deformation_71f8d4298b\\771b1396889e4ccf9014f1c17f25e1fb\\346f0e3791ac4ed5898543372ef829d6.json'}], 'total': 0, 'next_start': None}
      +------------------------------------
```

### tests/native/test_star_live.py::test_native_star_controlled_constant_data_and_shutdown[temperature]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_star_live.py", line 40, in test_native_star_controlled_constant_data_and_shutdown
  |     asyncio.run(execute('star_'+data_kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_star_live.py", line 22, in work
      |     imported=await e.finish(await e.call('run_star_operation',{'request':{
      |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |         'kind':'import_'+data_kind,'surface':1,'path':str(source),
      |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |         'coordinate_system':'local','length_unit':'Millimeters'}}))
      |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'rows': [], 'summary': {}, 'restoration': {'restored': True, 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\checkpoint_r5_star_import_temperature_933bc019.zos', 'context': {'session_id': '2a9525f8f2eb43bc9f8275eac6193678', 'model_revision': 7, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\working_29179f55.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\checkpoint_r5_star_import_temperature_933bc019.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 7, 'session_id': '2a9525f8f2eb43bc9f8275eac6193678'}}}, 'baseline': {'path': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\checkpoint_r5_star_import_temperature_933bc019.zos', 'context': {'session_id': '2a9525f8f2eb43bc9f8275eac6193678', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\working_29179f55.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\checkpoint_r4_surfaces_573331b0.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '2a9525f8f2eb43bc9f8275eac6193678'}}}, 'error': {'code': 'SETTING_REJECTED', 'message': 'STAR import file did not match on readback.', 'details': {'requested': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\star_input_2221246568a24bcaad9852d1ebbafe49\\controlled_temperature.txt', 'actual': '<USER_HOME>\\Documents\\Zemax\\OBJECTS\\STOP Files\\bbf971.zst'}}, 'operation': 'import_temperature', 'data_kind': 'temperature', 'cancellation': 'cooperative between native calls; an active import/refit call completes before cancellation', 'source_resource': {'source': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\controlled_temperature.txt', 'staged': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\star_input_2221246568a24bcaad9852d1ebbafe49\\controlled_temperature.txt', 'length_unit': 'Millimeters', 'coordinate_system': 'local'}, 'result_schema_version': 1, 'task': {'task_id': 'e350ef6bac284519a9179ce0dfb927cc', 'request_id': '16107cbde8834a929c60eff0692e68f3', 'kind': 'star_operation', 'state': 'failed', 'created_at': '2026-11-15T10:00:33.909530+00:00', 'finished_at': '2026-11-15T10:00:34.011547+00:00', 'progress': 0, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'import_temperature', 'surface': 1, 'path': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\controlled_temperature.txt', 'coordinate_system': 'local', 'length_unit': 'Millimeters'}, 'context': {'session_id': '2a9525f8f2eb43bc9f8275eac6193678', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\working_29179f55.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\checkpoint_r4_surfaces_573331b0.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '2a9525f8f2eb43bc9f8275eac6193678'}}, 'error': {'code': 'SETTING_REJECTED', 'message': 'STAR import file did not match on readback.', 'details': {'requested': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\star_input_2221246568a24bcaad9852d1ebbafe49\\controlled_temperature.txt', 'actual': '<USER_HOME>\\Documents\\Zemax\\OBJECTS\\STOP Files\\bbf971.zst'}}, 'result_path': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\e350ef6bac284519a9179ce0dfb927cc.json', 'result_artifacts': [{'kind': 'json', 'path': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\e350ef6bac284519a9179ce0dfb927cc.json'}], 'elapsed_seconds': 0.088}, 'context': {'session_id': '2a9525f8f2eb43bc9f8275eac6193678', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\working_29179f55.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\checkpoint_r4_surfaces_573331b0.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '2a9525f8f2eb43bc9f8275eac6193678'}}, 'system_settings': {'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'source_units': 'Watts', 'source_unit_prefix': 'None', 'analysis_units': 'WattsPerCMSq', 'analysis_unit_prefix': 'None', 'afocal_image_space': False, 'aperture': {'type': 'EntrancePupilDiameter', 'value': 10.0}, 'field_type': 'Angle', 'field_normalization': 'Radial', 'fields': [{'number': 1, 'x': 0.0, 'y': 0.0, 'weight': 1.0, 'vdx': 0.0, 'vdy': 0.0, 'vcx': 0.0, 'vcy': 0.0, 'van': 0.0}], 'wavelength_unit': 'micrometers (environmental air reference)', 'wavelengths': [{'number': 1, 'wavelength_um': 0.55, 'weight': 1.0, 'primary': True}], 'temperature_c': 20.0, 'pressure_atm': 1.0, 'adjust_index_to_environment': False, 'afocal_mode_units': 'Milliradians', 'settings_activity': {'apodization_factor_is_used': False}, 'author': '', 'aperture_options': {'apodization_type': 'Uniform', 'apodization_factor': 0.0, 'semi_diameter_margin': 0.0, 'semi_diameter_margin_pct': 0.0, 'telecentric_object_space': False, 'afocal_image_space': False, 'iterate_solves_when_updating': False, 'fast_semi_diameters': True, 'check_grin_apertures': False}, 'advanced': {'reference_opd': 'ExitPupil', 'paraxial_rays': 'IgnoreCoordinateBreaks', 'f_num_method': 'TracingRays', 'dont_print_coordinate_break_data': False, 'turn_off_threading': False, 'opd_modulo_2pi': False, 'include_calculated_data_in_session_file': True, 'include_tolerance_data_in_session_file': True, 'huygens_integral_method': 'Auto'}, 'global_reference_surface': 2, 'material_catalogs': ['SCHOTT'], 'polarization': {'unpolarized': True, 'jx': 0.0, 'jy': 1.0, 'x_phase': 0.0, 'y_phase': 0.0, 'method': 'XAxisMethod', 'convert_thin_film_phase': True}, 'ray_aiming': {'mode': 'Off', 'method': 'Heuristic', 'cache': True, 'robust': False, 'scale_pupil_shift_by_field': False, 'auto_pupil_shift': True, 'enhanced': False, 'advanced_convergence': False, 'fallback_search': False, 'pupil_shift_x': 0.0, 'pupil_shift_y': 0.0, 'pupil_shift_z': 0.0, 'pupil_compress_x': 0.0, 'pupil_compress_y': 0.0, 'cache_steps': 10}, 'files': {'coating_file': 'COATING.DAT', 'scatter_profile': 'SCATTER_PROFILE.DAT', 'abg_file': 'ABG_DATA.DAT', 'gradium_profile': 'PROFILE.GRD'}, 'title': '', 'notes': ''}, 'artifacts': [{'kind': 'json', 'path': '<REPO>\\.local\\runs\\runs\\star_temperature_043889f313\\2a9525f8f2eb43bc9f8275eac6193678\\e350ef6bac284519a9179ce0dfb927cc.json'}], 'total': 0, 'next_start': None}
      +------------------------------------
```

### tests/native/test_star_live.py::test_native_star_controlled_constant_data_and_shutdown[direct_index]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_star_live.py", line 40, in test_native_star_controlled_constant_data_and_shutdown
  |     asyncio.run(execute('star_'+data_kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_star_live.py", line 22, in work
      |     imported=await e.finish(await e.call('run_star_operation',{'request':{
      |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |         'kind':'import_'+data_kind,'surface':1,'path':str(source),
      |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |         'coordinate_system':'local','length_unit':'Millimeters'}}))
      |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'rows': [], 'summary': {}, 'restoration': {'restored': True, 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\checkpoint_r5_star_import_direct_index_57cc43b6.zos', 'context': {'session_id': '7b4d0691f6064221ad3a4f7ff4894f4c', 'model_revision': 7, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\working_332a5429.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\checkpoint_r5_star_import_direct_index_57cc43b6.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 7, 'session_id': '7b4d0691f6064221ad3a4f7ff4894f4c'}}}, 'baseline': {'path': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\checkpoint_r5_star_import_direct_index_57cc43b6.zos', 'context': {'session_id': '7b4d0691f6064221ad3a4f7ff4894f4c', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\working_332a5429.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\checkpoint_r4_surfaces_dbec4316.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '7b4d0691f6064221ad3a4f7ff4894f4c'}}}, 'error': {'code': 'SETTING_REJECTED', 'message': 'STAR import file did not match on readback.', 'details': {'requested': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\star_input_0a57e97f33374bc783bdc5e72bc2244a\\controlled_direct_index.txt', 'actual': '<USER_HOME>\\Documents\\Zemax\\OBJECTS\\STOP Files\\4a398d.zst'}}, 'operation': 'import_direct_index', 'data_kind': 'direct_index', 'cancellation': 'cooperative between native calls; an active import/refit call completes before cancellation', 'source_resource': {'source': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\controlled_direct_index.txt', 'staged': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\star_input_0a57e97f33374bc783bdc5e72bc2244a\\controlled_direct_index.txt', 'length_unit': 'Millimeters', 'coordinate_system': 'local'}, 'result_schema_version': 1, 'task': {'task_id': '9f2de7d1a7b74db2ad11de55ac2fe512', 'request_id': '019f9e1000764114a35903b80150fdc1', 'kind': 'star_operation', 'state': 'failed', 'created_at': '2026-11-15T10:00:42.190537+00:00', 'finished_at': '2026-11-15T10:00:42.295564+00:00', 'progress': 0, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'import_direct_index', 'surface': 1, 'path': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\controlled_direct_index.txt', 'coordinate_system': 'local', 'length_unit': 'Millimeters'}, 'context': {'session_id': '7b4d0691f6064221ad3a4f7ff4894f4c', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\working_332a5429.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\checkpoint_r4_surfaces_dbec4316.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '7b4d0691f6064221ad3a4f7ff4894f4c'}}, 'error': {'code': 'SETTING_REJECTED', 'message': 'STAR import file did not match on readback.', 'details': {'requested': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\star_input_0a57e97f33374bc783bdc5e72bc2244a\\controlled_direct_index.txt', 'actual': '<USER_HOME>\\Documents\\Zemax\\OBJECTS\\STOP Files\\4a398d.zst'}}, 'result_path': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\9f2de7d1a7b74db2ad11de55ac2fe512.json', 'result_artifacts': [{'kind': 'json', 'path': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\9f2de7d1a7b74db2ad11de55ac2fe512.json'}], 'elapsed_seconds': 0.091}, 'context': {'session_id': '7b4d0691f6064221ad3a4f7ff4894f4c', 'model_revision': 5, 'source_file': None, 'working_file': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\working_332a5429.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\checkpoint_r4_surfaces_dbec4316.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 5, 'session_id': '7b4d0691f6064221ad3a4f7ff4894f4c'}}, 'system_settings': {'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'source_units': 'Watts', 'source_unit_prefix': 'None', 'analysis_units': 'WattsPerCMSq', 'analysis_unit_prefix': 'None', 'afocal_image_space': False, 'aperture': {'type': 'EntrancePupilDiameter', 'value': 10.0}, 'field_type': 'Angle', 'field_normalization': 'Radial', 'fields': [{'number': 1, 'x': 0.0, 'y': 0.0, 'weight': 1.0, 'vdx': 0.0, 'vdy': 0.0, 'vcx': 0.0, 'vcy': 0.0, 'van': 0.0}], 'wavelength_unit': 'micrometers (environmental air reference)', 'wavelengths': [{'number': 1, 'wavelength_um': 0.55, 'weight': 1.0, 'primary': True}], 'temperature_c': 20.0, 'pressure_atm': 1.0, 'adjust_index_to_environment': False, 'afocal_mode_units': 'Milliradians', 'settings_activity': {'apodization_factor_is_used': False}, 'author': '', 'aperture_options': {'apodization_type': 'Uniform', 'apodization_factor': 0.0, 'semi_diameter_margin': 0.0, 'semi_diameter_margin_pct': 0.0, 'telecentric_object_space': False, 'afocal_image_space': False, 'iterate_solves_when_updating': False, 'fast_semi_diameters': True, 'check_grin_apertures': False}, 'advanced': {'reference_opd': 'ExitPupil', 'paraxial_rays': 'IgnoreCoordinateBreaks', 'f_num_method': 'TracingRays', 'dont_print_coordinate_break_data': False, 'turn_off_threading': False, 'opd_modulo_2pi': False, 'include_calculated_data_in_session_file': True, 'include_tolerance_data_in_session_file': True, 'huygens_integral_method': 'Auto'}, 'global_reference_surface': 2, 'material_catalogs': ['SCHOTT'], 'polarization': {'unpolarized': True, 'jx': 0.0, 'jy': 1.0, 'x_phase': 0.0, 'y_phase': 0.0, 'method': 'XAxisMethod', 'convert_thin_film_phase': True}, 'ray_aiming': {'mode': 'Off', 'method': 'Heuristic', 'cache': True, 'robust': False, 'scale_pupil_shift_by_field': False, 'auto_pupil_shift': True, 'enhanced': False, 'advanced_convergence': False, 'fallback_search': False, 'pupil_shift_x': 0.0, 'pupil_shift_y': 0.0, 'pupil_shift_z': 0.0, 'pupil_compress_x': 0.0, 'pupil_compress_y': 0.0, 'cache_steps': 10}, 'files': {'coating_file': 'COATING.DAT', 'scatter_profile': 'SCATTER_PROFILE.DAT', 'abg_file': 'ABG_DATA.DAT', 'gradium_profile': 'PROFILE.GRD'}, 'title': '', 'notes': ''}, 'artifacts': [{'kind': 'json', 'path': '<REPO>\\.local\\runs\\runs\\star_direct_index_d56d2cd9c2\\7b4d0691f6064221ad3a4f7ff4894f4c\\9f2de7d1a7b74db2ad11de55ac2fe512.json'}], 'total': 0, 'next_start': None}
      +------------------------------------
```

### tests/native/test_surface_mtf_modes_live.py::test_surface_mtf_circular_pupil_and_complex_identity[fft-128-256-10]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 46, in test_surface_mtf_circular_pupil_and_complex_identity
  |     asyncio.run(execute(f'surface_mtf092_{family}_{pupil}_{image}_{delta}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 45, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.6219384887175782, 'atol': 0.005, 'expected': 0.6276397277764232, 'label': 'circular pupil incoherent fft', ...}, {'actual': 0.38215690998153057, 'atol': 0.005, 'expected': 0.3910091104517681, 'label': 'circular pupil incoherent fft', ...}, {'actual': 0.17481731309724555, 'atol': 0.005, 'expected': 0.18529298913814515, 'label': 'circular pupil incoherent fft', ...}, {'actual': 0.057656789528627565, 'atol': 0.005, 'expected': 0.06710905782261711, 'label': 'circular pupil incoherent fft', ...}, {'actual': 0.3851280815867663, 'atol': 0.005, 'expected': 0.3944557520549891, 'label': 'circular pupil incoherent fft', ...}, {'actual': 0.3851280815867664, 'atol': 0.005, 'expected': 0.39445575205498973, 'label': 'circular pupil incoherent fft', ...}]
      | assert not [{'label': 'circular pupil incoherent fft', 'actual': 0.6219384887175782, 'expected': 0.6276397277764232, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'circular pupil incoherent fft', 'actual': 0.38215690998153057, 'expected': 0.3910091104517681, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'circular pupil incoherent fft', 'actual': 0.17481731309724555, 'expected': 0.18529298913814515, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'circular pupil incoherent fft', 'actual': 0.057656789528627565, 'expected': 0.06710905782261711, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'circular pupil incoherent fft', 'actual': 0.3851280815867663, 'expected': 0.3944557520549891, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'circular pupil incoherent fft', 'actual': 0.3851280815867664, 'expected': 0.39445575205498973, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_surface_mtf_modes_live.py::test_surface_mtf_circular_pupil_and_complex_identity[fft-256-256-10]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 46, in test_surface_mtf_circular_pupil_and_complex_identity
  |     asyncio.run(execute(f'surface_mtf092_{family}_{pupil}_{image}_{delta}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 45, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.18349566351225877, 'atol': 0.005, 'expected': 0.1888391116717572, 'label': 'circular pupil incoherent fft', ...}]
      | assert not [{'label': 'circular pupil incoherent fft', 'actual': 0.18349566351225877, 'expected': 0.1888391116717572, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_surface_mtf_modes_live.py::test_surface_mtf_circular_pupil_and_complex_identity[huygens-256-256-10]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 46, in test_surface_mtf_circular_pupil_and_complex_identity
  |     asyncio.run(execute(f'surface_mtf092_{family}_{pupil}_{image}_{delta}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 45, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.8153229434434659, 'atol': 0.005, 'expected': 0.8084986442937958, 'label': 'circular pupil incoherent huygens', ...}, {'actual': 0.6266189896660249, 'atol': 0.005, 'expected': 0.6214568812316937, 'label': 'circular pupil incoherent huygens', ...}]
      | assert not [{'label': 'circular pupil incoherent huygens', 'actual': 0.8153229434434659, 'expected': 0.8084986442937958, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'circular pupil incoherent huygens', 'actual': 0.6266189896660249, 'expected': 0.6214568812316937, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_surface_mtf_modes_live.py::test_surface_mtf_circular_pupil_and_complex_identity[huygens-256-512-5]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 46, in test_surface_mtf_circular_pupil_and_complex_identity
  |     asyncio.run(execute(f'surface_mtf092_{family}_{pupil}_{image}_{delta}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 45, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.8153234778725806, 'atol': 0.005, 'expected': 0.8088705325774975, 'label': 'circular pupil incoherent huygens', ...}]
      | assert not [{'label': 'circular pupil incoherent huygens', 'actual': 0.8153234778725806, 'expected': 0.8088705325774975, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_surface_mtf_modes_live.py::test_surface_mtf_circular_pupil_and_complex_identity[huygens-512-512-5]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 46, in test_surface_mtf_circular_pupil_and_complex_identity
  |     asyncio.run(execute(f'surface_mtf092_{family}_{pupil}_{image}_{delta}',work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_surface_mtf_modes_live.py", line 45, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.8153979271746893, 'atol': 0.005, 'expected': 0.8088705325774975, 'label': 'circular pupil incoherent huygens', ...}]
      | assert not [{'label': 'circular pupil incoherent huygens', 'actual': 0.8153979271746893, 'expected': 0.8088705325774975, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_surface_mtf_phase_identity_live.py::test_fft_surface_mtf_native_phase_identity_diagnostic

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_surface_mtf_phase_identity_live.py", line 77, in test_fft_surface_mtf_native_phase_identity_diagnostic
  |     asyncio.run(execute('surface_mtf603_phase_identity',guarded))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_surface_mtf_phase_identity_live.py", line 73, in guarded
      |     try:await work(e)
      |         ^^^^^^^^^^^^^
      |   File "<REPO>\tests\native\test_surface_mtf_phase_identity_live.py", line 29, in work
      |     prior=json.loads((source/'autocorrelation.json').read_text(encoding='utf-8'))[0]
      |                      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\pathlib\__init__.py", line 787, in read_text
      |     with self.open(mode='r', encoding=encoding, errors=errors, newline=newline) as f:
      |          ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\pathlib\__init__.py", line 771, in open
      |     return io.open(self, mode, buffering, encoding, errors, newline)
      |            ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      | FileNotFoundError: [Errno 2] No such file or directory: '<REPO>\\.local\\fixtures\\surface_mtf512_primary_89cacce054\\autocorrelation.json'
      +------------------------------------
```

### tests/native/test_surface_mtf_psf_reference_live.py::test_surface_mtf_vs_independent_psf_fourier[fft]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_surface_mtf_psf_reference_live.py", line 107, in test_surface_mtf_vs_independent_psf_fourier
  |     asyncio.run(execute('surface_mtf283_'+family,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_surface_mtf_psf_reference_live.py", line 106, in work
      |     assert not failures,failures
      | AssertionError: [{'actual': 0.5203074799257872, 'atol': 0.005, 'expected': 0.5260027524483305, 'label': 'fft field1 PSF/OTF (50.65779656917897,0.0)', ...}, {'actual': 0.5203074799257873, 'atol': 0.005, 'expected': 0.5260027524483304, 'label': 'fft field1 PSF/OTF (0.0,50.65779656917897)', ...}, {'actual': 0.2752957435435566, 'atol': 0.005, 'expected': 0.28475983818241296, 'label': 'fft field3 PSF/OTF (29.255275630512358,-5.684341886080802e-14)', ...}, {'actual': 0.7482676751672549, 'atol': 0.005, 'expected': 0.7834830450743988, 'label': 'fft field3 PSF/OTF (-5.684341886080802e-14,9.238508093845951)', ...}, {'actual': 0.1849887459320835, 'atol': 0.005, 'expected': 0.12392355061013324, 'label': 'fft field3 PSF/OTF (-5.684341886080802e-14,29.255275630512358)', ...}, {'actual': 0.05334123451725839, 'atol': 0.005, 'expected': 0.13019440647520572, 'label': 'fft field3 PSF/OTF (-5.684341886080802e-14,49.272043167178765)', ...}, ...]
      | assert not [{'label': 'fft field1 PSF/OTF (50.65779656917897,0.0)', 'actual': 0.5203074799257872, 'expected': 0.5260027524483305, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'fft field1 PSF/OTF (0.0,50.65779656917897)', 'actual': 0.5203074799257873, 'expected': 0.5260027524483304, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'fft field3 PSF/OTF (29.255275630512358,-5.684341886080802e-14)', 'actual': 0.2752957435435566, 'expected': 0.28475983818241296, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'fft field3 PSF/OTF (-5.684341886080802e-14,9.238508093845951)', 'actual': 0.7482676751672549, 'expected': 0.7834830450743988, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'fft field3 PSF/OTF (-5.684341886080802e-14,29.255275630512358)', 'actual': 0.1849887459320835, 'expected': 0.12392355061013324, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'fft field3 PSF/OTF (-5.684341886080802e-14,49.272043167178765)', 'actual': 0.05334123451725839, 'expected': 0.13019440647520572, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'fft field3 PSF/OTF (20.01676753666635,29.255275630512358)', 'actual': 0.23066088447302796, 'expected': 0.20146718467846864, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'fft field3 PSF/OTF (-20.016767536666464,29.255275630512358)', 'actual': 0.23066088447302785, 'expected': 0.20146718467846939, 'atol': 0.005, 'rtol': 0, 'passed': False}, {'label': 'fft field3 PSF/OTF (20.01676753666635,-29.25527563051247)', 'actual': 0.23066088447302788, 'expected': 0.20146718467846972, 'atol': 0.005, 'rtol': 0, 'passed': False}]
      +------------------------------------
```

### tests/native/test_finite_imaging_live.py::test_cooke_finite_psf_mtf_energy_native[0-3]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_finite_imaging_live.py", line 66, in test_cooke_finite_psf_mtf_energy_native
  |     asyncio.run(execute(f'finite_imaging_F{field}_W{wavelength}',work,role='fixture'))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_finite_imaging_live.py", line 65, in work
      |     assert records and all(r['passed']for r in records),[r for r in records if not r['passed']]
      | AssertionError: [{'actual': 0.45532490959831085, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.49501377931501184, ...}, {'actual': 0.45643248092857447, 'atol': 0.02, 'check': 'PSF Fourier MTF', 'expected': 0.49586901133529576, ...}]
      | assert ([{'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8697889830730142, 'expected': 0.8673368952521638, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.4931751771081848, 'expected': 0.4928346695918787, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.08044883200236082, 'expected': 0.08208182958716247, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.8670506057231548, 'expected': 0.8642505045758093, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.4739301429800285, 'expected': 0.4746319844237797, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.1453762531010785, 'expected': 0.14595779017180133, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8684963245583323, 'expected': 0.8660065890052625, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.4928196934629315, 'expected': 0.4924813306943372, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.0808709017227359, 'expected': 0.08252237646138003, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.8661574663683032, 'expected': 0.8633096168536013, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.472892378700294, 'expected': 0.4735503823004797, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'huygens', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.1453832245379397, 'expected': 0.14592330183207736, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.849676615346898, 'expected': 0.8611210030081087, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.45532490959831085, 'expected': 0.49501377931501184, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.0909205627844899, 'expected': 0.10452613215314749, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.8678068216937638, 'expected': 0.8664930260043721, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.49104222622765464, 'expected': 0.4948533987079783, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 256, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.15735241240627776, 'expected': 0.1583412651586803, 'atol': 0.02, 'passed': True}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 256, 'radius_um': 10, 'actual': 0.5593897768929827, 'expected': 0.5530683766882097, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 256, 'radius_um': 20, 'actual': 0.939929815408976, 'expected': 0.9373322762007363, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 10, 'actual': 0.8499657193293858, 'expected': 0.8640469740657413, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 25, 'actual': 0.45643248092857447, 'expected': 0.49586901133529576, 'atol': 0.02, 'passed': False}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5b50\u5348', 'frequency_cycles_mm': 50, 'actual': 0.09136101377715022, 'expected': 0.10471484783198519, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 10, 'actual': 0.8681847991532434, 'expected': 0.8698286733916665, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 25, 'actual': 0.4920216603419213, 'expected': 0.49644352317163615, 'atol': 0.02, 'passed': True}, {'check': 'PSF Fourier MTF', 'family': 'fft', 'sampling': 512, 'label': '\u5f27\u77e2', 'frequency_cycles_mm': 50, 'actual': 0.15758343781547085, 'expected': 0.15930679564313083, 'atol': 0.02, 'passed': True}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 512, 'radius_um': 10, 'actual': 0.5569743499948434, 'expected': 0.5544182997406892, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}, {'check': 'PSF energy cross reference', 'family': 'fft', 'sampling': 512, 'radius_um': 20, 'actual': 0.938314863217913, 'expected': 0.940751559688171, 'atol': 0.025, 'passed': True, 'scope': 'FFT PSF versus FFT energy, actual field only; finite window, absolute pupil integral separate'}] and False)
      |  +  where False = all(<generator object test_cooke_finite_psf_mtf_energy_native.<locals>.work.<locals>.<genexpr> at 0x00000211056AE5A0>)
      +------------------------------------
```

### tests/native/test_2026r1_star_preloaded_live.py::test_2026r1_star_fit_read_unload[temperature]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_2026r1_star_preloaded_live.py", line 28, in test_2026r1_star_fit_read_unload
  |     asyncio.run(execute('2026r1_star_fit_unload_'+data_kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_2026r1_star_preloaded_live.py", line 27, in work
      |     e.check('constant '+key,sample[key],expected,atol=1e-6,rtol=1e-7)
      |     ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 35, in check
      |     assert passed,self.checks[-1]
      |            ^^^^^^
      | AssertionError: {'label': 'constant temperature', 'actual': 0.0, 'expected': 21.0, 'atol': 1e-06, 'rtol': 1e-07, 'passed': False}
      +------------------------------------
```

### tests/native/test_2026r1_star_preloaded_live.py::test_2026r1_star_rigid_body_operations[add_coordinate_breaks]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_2026r1_star_preloaded_live.py", line 47, in test_2026r1_star_rigid_body_operations
  |     asyncio.run(execute('2026r1_star_rbm_'+operation,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_2026r1_star_preloaded_live.py", line 44, in work
      |     result=await e.finish(await e.call('run_star_operation',dict(request=request)))
      |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'rows': [], 'summary': {}, 'restoration': {'restored': True, 'checkpoint': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\checkpoint_r2_star_component_rbm_afebf390.zos', 'context': {'session_id': '8e148d93722f467dac3e8b185e63c406', 'model_revision': 4, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_deformation_87afa8928d\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\working_831f910f.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\checkpoint_r2_star_component_rbm_afebf390.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 4, 'session_id': '8e148d93722f467dac3e8b185e63c406'}}}, 'baseline': {'path': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\checkpoint_r2_star_component_rbm_afebf390.zos', 'context': {'session_id': '8e148d93722f467dac3e8b185e63c406', 'model_revision': 2, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_deformation_87afa8928d\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\working_831f910f.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\checkpoint_r1_star_define_component_1866fdd6.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 2, 'session_id': '8e148d93722f467dac3e8b185e63c406'}}, 'star_update_mode': 'Normal'}, 'error': {'code': 'SETTING_REJECTED', 'message': 'STAR component creation or selection was not adopted.', 'details': {}}, 'operation': 'component_rbm', 'cancellation': 'cooperative between native calls', 'resource_ownership': 'STAR objects owned by the optical system; no separate native tool created', 'result_schema_version': 1, 'task': {'task_id': '9fcdeead6e3e477ab9535ff03864f850', 'request_id': 'f08bcc289e8e4773b367f02d5166e21a', 'kind': 'star_operation', 'state': 'failed', 'created_at': '2026-11-15T13:58:38.308303+00:00', 'finished_at': '2026-11-15T13:58:38.445574+00:00', 'progress': 0, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'component_rbm', 'surface': 1, 'action': 'add_coordinate_breaks', 'adjust_index_data_with_rbm': None}, 'context': {'session_id': '8e148d93722f467dac3e8b185e63c406', 'model_revision': 2, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_deformation_87afa8928d\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\working_831f910f.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\checkpoint_r1_star_define_component_1866fdd6.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 2, 'session_id': '8e148d93722f467dac3e8b185e63c406'}}, 'error': {'code': 'SETTING_REJECTED', 'message': 'STAR component creation or selection was not adopted.', 'details': {}}, 'result_path': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\9fcdeead6e3e477ab9535ff03864f850.json', 'result_artifacts': [{'kind': 'json', 'path': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\9fcdeead6e3e477ab9535ff03864f850.json'}], 'elapsed_seconds': 0.126}, 'context': {'session_id': '8e148d93722f467dac3e8b185e63c406', 'model_revision': 2, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_deformation_87afa8928d\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\working_831f910f.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\checkpoint_r1_star_define_component_1866fdd6.zos', 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 2, 'session_id': '8e148d93722f467dac3e8b185e63c406'}}, 'system_settings': {'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'source_units': 'Watts', 'source_unit_prefix': 'None', 'analysis_units': 'WattsPerCMSq', 'analysis_unit_prefix': 'None', 'afocal_image_space': False, 'aperture': {'type': 'EntrancePupilDiameter', 'value': 2.0}, 'field_type': 'Angle', 'field_normalization': 'Radial', 'fields': [{'number': 1, 'x': 0.0, 'y': 0.0, 'weight': 1.0, 'vdx': 0.0, 'vdy': 0.0, 'vcx': 0.0, 'vcy': 0.0, 'van': 0.0}], 'wavelength_unit': 'micrometers (environmental air reference)', 'wavelengths': [{'number': 1, 'wavelength_um': 0.55, 'weight': 1.0, 'primary': True}], 'temperature_c': 20.0, 'pressure_atm': 1.0, 'adjust_index_to_environment': False, 'afocal_mode_units': 'Milliradians', 'settings_activity': {'apodization_factor_is_used': False}, 'author': '', 'aperture_options': {'apodization_type': 'Uniform', 'apodization_factor': 0.0, 'semi_diameter_margin': 0.0, 'semi_diameter_margin_pct': 0.0, 'telecentric_object_space': False, 'afocal_image_space': False, 'iterate_solves_when_updating': False, 'fast_semi_diameters': True, 'check_grin_apertures': False}, 'advanced': {'reference_opd': 'ExitPupil', 'paraxial_rays': 'IgnoreCoordinateBreaks', 'f_num_method': 'TracingRays', 'dont_print_coordinate_break_data': False, 'turn_off_threading': False, 'opd_modulo_2pi': False, 'include_calculated_data_in_session_file': True, 'include_tolerance_data_in_session_file': True, 'huygens_integral_method': 'Auto'}, 'global_reference_surface': 2, 'material_catalogs': ['SCHOTT'], 'polarization': {'unpolarized': True, 'jx': 0.0, 'jy': 1.0, 'x_phase': 0.0, 'y_phase': 0.0, 'method': 'XAxisMethod', 'convert_thin_film_phase': True}, 'ray_aiming': {'mode': 'Off', 'method': 'Heuristic', 'cache': True, 'robust': False, 'scale_pupil_shift_by_field': False, 'auto_pupil_shift': True, 'enhanced': False, 'advanced_convergence': False, 'fallback_search': False, 'pupil_shift_x': 0.0, 'pupil_shift_y': 0.0, 'pupil_shift_z': 0.0, 'pupil_compress_x': 0.0, 'pupil_compress_y': 0.0, 'cache_steps': 10}, 'files': {'coating_file': 'COATING.DAT', 'scatter_profile': 'SCATTER_PROFILE.DAT', 'abg_file': 'ABG_DATA.DAT', 'gradium_profile': 'PROFILE.GRD'}, 'title': '', 'notes': ''}, 'artifacts': [{'kind': 'json', 'path': '<REPO>\\.local\\runs\\runs\\2026r1_star_rbm_add_coordinate_breaks_fb3d717f11\\8e148d93722f467dac3e8b185e63c406\\9fcdeead6e3e477ab9535ff03864f850.json'}], 'total': 0, 'next_start': None}
      +------------------------------------
```

### tests/native/test_2026r1_star_each_live.py::test_2026r1_individual_star_analysis[star_align_check]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 19, in test_2026r1_individual_star_analysis
  |     asyncio.run(execute('2026r1_'+kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 18, in work
      |     await probe_kind(e,kind)
      |   File "<REPO>\tests\support\star_analysis_probe.py", line 50, in probe_kind
      |     payload = await evidence.finish(response)
      |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': '665f123c043f482abe8bd142f5047c0d', 'request_id': '4caf14ddf7f241cbb7a2017d7f746438', 'kind': 'star_align_check', 'state': 'failed', 'created_at': '2026-11-15T13:58:59.836457+00:00', 'finished_at': '2026-11-15T13:58:59.921048+00:00', 'progress': None, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'star_align_check', 'analysis': 'star_align_check', 'native_analysis': 'STARAlignCheck', 'analysis_id': 155, 'requested': {'kind': 'star_align_check'}, 'native': {'IsValid': True, 'IsActiveWindow': True}, 'settings_surface': [], 'settings_support': 'probed at run time; no IAS_ interface is documented for this analysis', 'availability': {'enabled': True, 'source': 'live read of IZOSAPI_Application.IsSTARModuleEnabled'}}, 'context': {'session_id': '5cb250cd19c54dc385cd7e901eb8a430', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_743ccd5863\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_align_check_5448d62677\\5cb250cd19c54dc385cd7e901eb8a430\\working_2014df31.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': '5cb250cd19c54dc385cd7e901eb8a430'}}, 'error': {'code': 'NO_RESULT_DATA', 'message': 'STAR 专题分析没有提供有效的曲线、网格或散点。', 'details': {'analysis': 'star_align_check', 'native_messages': [], 'native_header': [], 'text_export': {'attempted': True, 'exported': False, 'path': None, 'error': 'GetTextFile returned false', 'line_count': None, 'non_blank_lines': None, 'encoding': 'utf-16'}, 'empty_collections': [], 'note': 'an exported but empty or title-only text file, an empty series or an empty scatter block is not a valid result; only non-empty series, grids and scatter points are'}}, 'close_attempted': True, 'result_path': '<REPO>\\.local\\runs\\runs\\2026r1_star_align_check_5448d62677\\5cb250cd19c54dc385cd7e901eb8a430\\665f123c043f482abe8bd142f5047c0d.json', 'elapsed_seconds': 0.076}, 'checkpoint': None, 'result_schema_version': 1, 'context': {'session_id': '5cb250cd19c54dc385cd7e901eb8a430', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_743ccd5863\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_align_check_5448d62677\\5cb250cd19c54dc385cd7e901eb8a430\\working_2014df31.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': '5cb250cd19c54dc385cd7e901eb8a430'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_2026r1_star_each_live.py::test_2026r1_individual_star_analysis[star_sys_viewer]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 19, in test_2026r1_individual_star_analysis
  |     asyncio.run(execute('2026r1_'+kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 18, in work
      |     await probe_kind(e,kind)
      |   File "<REPO>\tests\support\star_analysis_probe.py", line 50, in probe_kind
      |     payload = await evidence.finish(response)
      |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': 'cf5777b230a6466e9ee576f242106b21', 'request_id': '167ed26a30374f37a730bb3e720539e9', 'kind': 'star_sys_viewer', 'state': 'failed', 'created_at': '2026-11-15T13:52:07.980782+00:00', 'finished_at': '2026-11-15T13:52:08.065721+00:00', 'progress': None, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'star_sys_viewer', 'analysis': 'star_sys_viewer', 'native_analysis': 'STARSysViewer', 'analysis_id': 156, 'requested': {'kind': 'star_sys_viewer'}, 'native': {'IsValid': True, 'IsActiveWindow': True}, 'settings_surface': [], 'settings_support': 'probed at run time; no IAS_ interface is documented for this analysis', 'availability': {'enabled': True, 'source': 'live read of IZOSAPI_Application.IsSTARModuleEnabled'}}, 'context': {'session_id': 'e8486089005949b4a95e7946a2ce858d', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_5ab8483786\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_sys_viewer_b4c4b96bf7\\e8486089005949b4a95e7946a2ce858d\\working_83fe35e4.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'e8486089005949b4a95e7946a2ce858d'}}, 'error': {'code': 'NO_RESULT_DATA', 'message': 'STAR 专题分析没有提供有效的曲线、网格或散点。', 'details': {'analysis': 'star_sys_viewer', 'native_messages': [], 'native_header': [], 'text_export': {'attempted': True, 'exported': False, 'path': None, 'error': 'GetTextFile returned false', 'line_count': None, 'non_blank_lines': None, 'encoding': 'utf-16'}, 'empty_collections': [], 'note': 'an exported but empty or title-only text file, an empty series or an empty scatter block is not a valid result; only non-empty series, grids and scatter points are'}}, 'close_attempted': True, 'result_path': '<REPO>\\.local\\runs\\runs\\2026r1_star_sys_viewer_b4c4b96bf7\\e8486089005949b4a95e7946a2ce858d\\cf5777b230a6466e9ee576f242106b21.json', 'elapsed_seconds': 0.076}, 'checkpoint': None, 'result_schema_version': 1, 'context': {'session_id': 'e8486089005949b4a95e7946a2ce858d', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_5ab8483786\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_sys_viewer_b4c4b96bf7\\e8486089005949b4a95e7946a2ce858d\\working_83fe35e4.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'e8486089005949b4a95e7946a2ce858d'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_2026r1_star_each_live.py::test_2026r1_individual_star_analysis[star_2d_def_plot]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 19, in test_2026r1_individual_star_analysis
  |     asyncio.run(execute('2026r1_'+kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 18, in work
      |     await probe_kind(e,kind)
      |   File "<REPO>\tests\support\star_analysis_probe.py", line 50, in probe_kind
      |     payload = await evidence.finish(response)
      |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': 'aac1bea86c2549cca0802f39d7bca0a9', 'request_id': 'd452ce0dc45d458ba0160393bfb9699f', 'kind': 'star_2d_def_plot', 'state': 'failed', 'created_at': '2026-11-15T13:52:26.716244+00:00', 'finished_at': '2026-11-15T13:52:26.807288+00:00', 'progress': None, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'star_2d_def_plot', 'analysis': 'star_2d_def_plot', 'native_analysis': 'STAR2DDefPlot', 'analysis_id': 157, 'requested': {'kind': 'star_2d_def_plot'}, 'native': {'IsValid': True, 'IsActiveWindow': True}, 'settings_surface': [], 'settings_support': 'probed at run time; no IAS_ interface is documented for this analysis', 'availability': {'enabled': True, 'source': 'live read of IZOSAPI_Application.IsSTARModuleEnabled'}}, 'context': {'session_id': 'abaa59bb4f6f4eb799a3eac8d3e33e17', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_c57751bc99\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_2d_def_plot_b30eedad7f\\abaa59bb4f6f4eb799a3eac8d3e33e17\\working_123dbbba.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'abaa59bb4f6f4eb799a3eac8d3e33e17'}}, 'error': {'code': 'NO_RESULT_DATA', 'message': 'STAR 专题分析没有提供有效的曲线、网格或散点。', 'details': {'analysis': 'star_2d_def_plot', 'native_messages': [], 'native_header': [], 'text_export': {'attempted': True, 'exported': False, 'path': None, 'error': 'GetTextFile returned false', 'line_count': None, 'non_blank_lines': None, 'encoding': 'utf-16'}, 'empty_collections': [], 'note': 'an exported but empty or title-only text file, an empty series or an empty scatter block is not a valid result; only non-empty series, grids and scatter points are'}}, 'close_attempted': True, 'result_path': '<REPO>\\.local\\runs\\runs\\2026r1_star_2d_def_plot_b30eedad7f\\abaa59bb4f6f4eb799a3eac8d3e33e17\\aac1bea86c2549cca0802f39d7bca0a9.json', 'elapsed_seconds': 0.081}, 'checkpoint': None, 'result_schema_version': 1, 'context': {'session_id': 'abaa59bb4f6f4eb799a3eac8d3e33e17', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_c57751bc99\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_2d_def_plot_b30eedad7f\\abaa59bb4f6f4eb799a3eac8d3e33e17\\working_123dbbba.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'abaa59bb4f6f4eb799a3eac8d3e33e17'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_2026r1_star_each_live.py::test_2026r1_individual_star_analysis[star_perf_change]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 19, in test_2026r1_individual_star_analysis
  |     asyncio.run(execute('2026r1_'+kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 18, in work
      |     await probe_kind(e,kind)
      |   File "<REPO>\tests\support\star_analysis_probe.py", line 50, in probe_kind
      |     payload = await evidence.finish(response)
      |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': 'b8d6a4132d404416842fadb0659a48a7', 'request_id': '26ce983f5f76490887d7d54ff500fbdb', 'kind': 'star_perf_change', 'state': 'failed', 'created_at': '2026-11-15T13:52:45.788805+00:00', 'finished_at': '2026-11-15T13:52:45.861553+00:00', 'progress': None, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'star_perf_change', 'analysis': 'star_perf_change', 'native_analysis': 'STARPerfChange', 'analysis_id': 158, 'requested': {'kind': 'star_perf_change'}, 'native': {'IsValid': True, 'IsActiveWindow': True}, 'settings_surface': [], 'settings_support': 'probed at run time; no IAS_ interface is documented for this analysis', 'availability': {'enabled': True, 'source': 'live read of IZOSAPI_Application.IsSTARModuleEnabled'}}, 'context': {'session_id': 'a37b17e2094144cbab39da4523ca1cca', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_269bcffca4\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_perf_change_03710a0c6a\\a37b17e2094144cbab39da4523ca1cca\\working_151434ee.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'a37b17e2094144cbab39da4523ca1cca'}}, 'error': {'code': 'NO_RESULT_DATA', 'message': 'STAR 专题分析没有提供有效的曲线、网格或散点。', 'details': {'analysis': 'star_perf_change', 'native_messages': [], 'native_header': [], 'text_export': {'attempted': True, 'exported': False, 'path': None, 'error': 'GetTextFile returned false', 'line_count': None, 'non_blank_lines': None, 'encoding': 'utf-16'}, 'empty_collections': [], 'note': 'an exported but empty or title-only text file, an empty series or an empty scatter block is not a valid result; only non-empty series, grids and scatter points are'}}, 'close_attempted': True, 'result_path': '<REPO>\\.local\\runs\\runs\\2026r1_star_perf_change_03710a0c6a\\a37b17e2094144cbab39da4523ca1cca\\b8d6a4132d404416842fadb0659a48a7.json', 'elapsed_seconds': 0.063}, 'checkpoint': None, 'result_schema_version': 1, 'context': {'session_id': 'a37b17e2094144cbab39da4523ca1cca', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_269bcffca4\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_perf_change_03710a0c6a\\a37b17e2094144cbab39da4523ca1cca\\working_151434ee.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'a37b17e2094144cbab39da4523ca1cca'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_2026r1_star_each_live.py::test_2026r1_individual_star_analysis[star_index_vs_temp]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 19, in test_2026r1_individual_star_analysis
  |     asyncio.run(execute('2026r1_'+kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 18, in work
      |     await probe_kind(e,kind)
      |   File "<REPO>\tests\support\star_analysis_probe.py", line 50, in probe_kind
      |     payload = await evidence.finish(response)
      |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': '79017a6d662849eead870f42e04696e8', 'request_id': '2a5e5e0e0d3644748214ca0c666bbe7d', 'kind': 'star_index_vs_temp', 'state': 'failed', 'created_at': '2026-11-15T13:53:04.587617+00:00', 'finished_at': '2026-11-15T13:53:04.675981+00:00', 'progress': None, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'star_index_vs_temp', 'analysis': 'star_index_vs_temp', 'native_analysis': 'STARIndexVsTemp', 'analysis_id': 159, 'requested': {'kind': 'star_index_vs_temp'}, 'native': {'IsValid': True, 'IsActiveWindow': True}, 'settings_surface': [], 'settings_support': 'probed at run time; no IAS_ interface is documented for this analysis', 'availability': {'enabled': True, 'source': 'live read of IZOSAPI_Application.IsSTARModuleEnabled'}}, 'context': {'session_id': 'fd558c679af94a56bfc70ddd01bfe36b', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_ee1de99bc2\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_index_vs_temp_8b25ddc8d7\\fd558c679af94a56bfc70ddd01bfe36b\\working_96576782.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'fd558c679af94a56bfc70ddd01bfe36b'}}, 'error': {'code': 'NO_RESULT_DATA', 'message': 'STAR 专题分析没有提供有效的曲线、网格或散点。', 'details': {'analysis': 'star_index_vs_temp', 'native_messages': [], 'native_header': [], 'text_export': {'attempted': True, 'exported': False, 'path': None, 'error': 'GetTextFile returned false', 'line_count': None, 'non_blank_lines': None, 'encoding': 'utf-16'}, 'empty_collections': [], 'note': 'an exported but empty or title-only text file, an empty series or an empty scatter block is not a valid result; only non-empty series, grids and scatter points are'}}, 'close_attempted': True, 'result_path': '<REPO>\\.local\\runs\\runs\\2026r1_star_index_vs_temp_8b25ddc8d7\\fd558c679af94a56bfc70ddd01bfe36b\\79017a6d662849eead870f42e04696e8.json', 'elapsed_seconds': 0.079}, 'checkpoint': None, 'result_schema_version': 1, 'context': {'session_id': 'fd558c679af94a56bfc70ddd01bfe36b', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_ee1de99bc2\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_index_vs_temp_8b25ddc8d7\\fd558c679af94a56bfc70ddd01bfe36b\\working_96576782.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': 'fd558c679af94a56bfc70ddd01bfe36b'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_2026r1_star_each_live.py::test_2026r1_individual_star_analysis[star_inspect_fea]

结果：failed。

```text
+ Exception Group Traceback (most recent call last):
  |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 19, in test_2026r1_individual_star_analysis
  |     asyncio.run(execute('2026r1_'+kind,work))
  |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 205, in run
  |     return runner.run(main)
  |            ~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\runners.py", line 128, in run
  |     return self._loop.run_until_complete(task)
  |            ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\asyncio\base_events.py", line 720, in run_until_complete
  |     return future.result()
  |            ~~~~~~~~~~~~~^^
  |   File "<REPO>\tests\support\native.py", line 70, in execute
  |     async with Client(params,read_timeout_seconds=180)as client:
  |                ~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\client.py", line 480, in __aexit__
  |     await self._exit_stack.__aexit__(exc_type, exc_val, exc_tb)
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 768, in __aexit__
  |     raise exc
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
  |     cb_suppress = await cb(*exc_details)
  |                   ^^^^^^^^^^^^^^^^^^^^^^
  |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 235, in __aexit__
  |     await self.gen.athrow(value)
  |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 201, in stdio_client
  |     async with anyio.create_task_group() as tg:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Exception Group Traceback (most recent call last):
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\stdio.py", line 205, in stdio_client
    |     yield read_stream, write_stream
    |   File "<REPO>\.local\python\cpython-3.14.10-windows-x86_64-none\Lib\contextlib.py", line 751, in __aexit__
    |     cb_suppress = await cb(*exc_details)
    |                   ^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\mcp\client\session.py", line 514, in __aexit__
    |     result = await self._task_group.__aexit__(exc_type, exc_val, exc_tb)
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "<REPO>\.venv\Lib\site-packages\anyio\_backends\_asyncio.py", line 847, in __aexit__
    |     raise BaseExceptionGroup(
    |         "unhandled errors in a TaskGroup", self._exceptions
    |     ) from None
    | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
    +-+---------------- 1 ----------------
      | Traceback (most recent call last):
      |   File "<REPO>\tests\support\native.py", line 72, in execute
      |     await work(e)
      |   File "<REPO>\tests\native\test_2026r1_star_each_live.py", line 18, in work
      |     await probe_kind(e,kind)
      |   File "<REPO>\tests\support\star_analysis_probe.py", line 50, in probe_kind
      |     payload = await evidence.finish(response)
      |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
      |   File "<REPO>\tests\support\native.py", line 27, in finish
      |     assert t["state"]=="succeeded",r
      |            ^^^^^^^^^^^^^^^^^^^^^^^
      | AssertionError: {'completed': False, 'task': {'task_id': '662054280d5b4ded9b898c3b9ab28230', 'request_id': '5bc90db0f2684c3cb18bd69145aba453', 'kind': 'star_inspect_fea', 'state': 'failed', 'created_at': '2026-11-15T13:53:23.950205+00:00', 'finished_at': '2026-11-15T13:53:24.045539+00:00', 'progress': None, 'can_cancel': True, 'cancel_requested': False, 'settings': {'kind': 'star_inspect_fea', 'analysis': 'star_inspect_fea', 'native_analysis': 'STARInspectFEA', 'analysis_id': 160, 'requested': {'kind': 'star_inspect_fea'}, 'native': {'IsValid': True, 'IsActiveWindow': True}, 'settings_surface': [], 'settings_support': 'probed at run time; no IAS_ interface is documented for this analysis', 'availability': {'enabled': True, 'source': 'live read of IZOSAPI_Application.IsSTARModuleEnabled'}}, 'context': {'session_id': '5ac5379274c44919b33ea7a0ec366dd6', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_23a9f8e25a\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_inspect_fea_316d913e44\\5ac5379274c44919b33ea7a0ec366dd6\\working_1ee34293.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': '5ac5379274c44919b33ea7a0ec366dd6'}}, 'error': {'code': 'NO_RESULT_DATA', 'message': 'STAR 专题分析没有提供有效的曲线、网格或散点。', 'details': {'analysis': 'star_inspect_fea', 'native_messages': [], 'native_header': [], 'text_export': {'attempted': True, 'exported': False, 'path': None, 'error': 'GetTextFile returned false', 'line_count': None, 'non_blank_lines': None, 'encoding': 'utf-16'}, 'empty_collections': [], 'note': 'an exported but empty or title-only text file, an empty series or an empty scatter block is not a valid result; only non-empty series, grids and scatter points are'}}, 'close_attempted': True, 'result_path': '<REPO>\\.local\\runs\\runs\\2026r1_star_inspect_fea_316d913e44\\5ac5379274c44919b33ea7a0ec366dd6\\662054280d5b4ded9b898c3b9ab28230.json', 'elapsed_seconds': 0.086}, 'checkpoint': None, 'result_schema_version': 1, 'context': {'session_id': '5ac5379274c44919b33ea7a0ec366dd6', 'model_revision': 1, 'source_file': '<REPO>\\.local\\runs\\fixtures\\2026r1_star_preloaded_combined_23a9f8e25a\\preloaded.zos', 'working_file': '<REPO>\\.local\\runs\\runs\\2026r1_star_inspect_fea_316d913e44\\5ac5379274c44919b33ea7a0ec366dd6\\working_1ee34293.zos', 'opticstudio_version': '26.1.0', 'opticstudio_build': '260127', 'license': 'EnterpriseEdition', 'checkpoint': None, 'requires_reconnect': False, 'mode': 'Sequential', 'configuration': 1, 'lens_units': 'Millimeters', 'mtf_units': 'CyclesPerMillimeter', 'geometry': {'state': 'pending', 'model_revision': 1, 'session_id': '5ac5379274c44919b33ea7a0ec366dd6'}}, 'artifacts': []}
      +------------------------------------
```

### tests/native/test_cad_multiple_live.py::test_native_cad_multiple_configurations

结果：skipped。

```text
tests\native\test_cad_multiple_live.py:65: in test_native_cad_multiple_configurations
    if layer_failures:pytest.xfail('v242 CAD IGES layer output differs from adopted settings: '+str(layer_failures))
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   _pytest.outcomes.XFailed: v242 CAD IGES layer output differs from adopted settings: [{'mode': 'all_by_layer', 'actual': [0, 65535], 'expected': [10, 11], 'rejected': True}, {'mode': 'all_at_once', 'actual': [0, 65535], 'expected': [10], 'rejected': True}]
```

### tests/native/test_conversion_optical_reference_live.py::test_conversion_polarized_plane_reference[group]

结果：skipped。

```text
tests\native\test_conversion_optical_reference_live.py:151: in test_conversion_polarized_plane_reference
    if blocked:pytest.xfail(blocked[0])
               ^^^^^^^^^^^^^^^^^^^^^^^^
E   _pytest.outcomes.XFailed: 2024 R2 controlled dummy-boundary group conversion: native unknown start error; checkpoint restore/retrace accepted
```

### tests/native/test_hpc_live.py::test_hpc_native_preferences_success_readback

结果：skipped。

```text
('<REPO>\\.venv\\Lib\\site-packages\\anyio\\_backends\\_asyncio.py', 847, 'unhandled errors in a TaskGroup')
```

### tests/native/test_hpc_live.py::test_hpc_minimal_native_job_result_and_close[nsc]

结果：skipped。

```text
('<REPO>\\.venv\\Lib\\site-packages\\anyio\\_backends\\_asyncio.py', 847, 'unhandled errors in a TaskGroup')
```

### tests/native/test_hpc_live.py::test_hpc_minimal_native_job_result_and_close[tolerance]

结果：skipped。

```text
('<REPO>\\.venv\\Lib\\site-packages\\anyio\\_backends\\_asyncio.py', 847, 'unhandled errors in a TaskGroup')
```

### tests/native/test_hpc_live.py::test_hpc_minimal_native_job_result_and_close[global]

结果：skipped。

```text
('<REPO>\\.venv\\Lib\\site-packages\\anyio\\_backends\\_asyncio.py', 847, 'unhandled errors in a TaskGroup')
```

### tests/native/test_hpc_live.py::test_hpc_minimal_native_job_result_and_close[hammer]

结果：skipped。

```text
('<REPO>\\.venv\\Lib\\site-packages\\anyio\\_backends\\_asyncio.py', 847, 'unhandled errors in a TaskGroup')
```

### tests/native/test_surface_mtf_anisotropic_reference_live.py::test_fft_surface_mtf_independent_meridional_frequency_scales

结果：skipped。

```text
('<REPO>\\tests\\native\\test_surface_mtf_anisotropic_reference_live.py', 20, 'Skipped: Requires preserved native509 independent pupil evidence')
```

### tests/native/test_test_plates_live.py::test_test_plates_selected_native_cfgs_identity_and_reload

结果：skipped。

```text
('<REPO>\\tests\\native\\test_test_plates_live.py', 14, 'Skipped: Provide at least two original native catalog CFG presets in ZEMAX_TEST_PLATE_CFGS')
```

### tests/native/test_wavelength_filter_live.py::test_fluorescence_wavelength_membership_native[native_consistency]

结果：skipped。

```text
('<REPO>\\tests\\native\\test_wavelength_filter_live.py', 83, 'Skipped: explicit recorded fluorescence ZRD input missing')
```

### tests/native/test_wavelength_filter_live.py::test_fluorescence_wavelength_membership_native[numeric_membership]

结果：skipped。

```text
('<REPO>\\tests\\native\\test_wavelength_filter_live.py', 83, 'Skipped: explicit recorded fluorescence ZRD input missing')
```


## 普通测试失败


## 复测通过记录

- tests/native/test_confocal_live.py::test_confocal_two_paths_pinhole_and_reference_stdio：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_conversion_live.py::test_nsc_pure_conversion_sources_and_reload：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_diff_efficiency_live.py::test_diff_efficiency_hologram_runtime：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_diff_efficiency_offaxis_live.py::test_unslanted_hologram_offaxis_reference[native]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_diff_efficiency_offaxis_live.py::test_unslanted_hologram_offaxis_reference[dll]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_directivity_plot_live.py::test_directivity_plot_stdio：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_evaluation_live.py::test_native_ray_reference_and_diagnostic：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_finite_ideal_phase_live.py::test_finite_ideal_surface_native[CoordinateBreak]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_finite_imaging_live.py::test_cooke_finite_psf_mtf_energy_native[1-2]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_finite_surface_live.py::test_finite_geometric_surface_equation_native[ChebyShv]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_finite_surface_live.py::test_finite_geometric_surface_equation_native[Tilted]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_glass_map_live.py::test_glass_map_native_catalog_points_and_lifecycle：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_glass_trials_live.py::test_glass_trials_native_stdio：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_nsc_conversion_live.py::test_nsc_pure_conversion_sources_and_reload：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_nsc_units_live.py::test_nsc_units_native：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_ray_diagrams_live.py::test_image_incidence_reflection_sign_and_before_refraction[mirror]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_ray_diagrams_live.py::test_image_incidence_reflection_sign_and_before_refraction[image_glass]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_ray_diagrams_live.py::test_image_incidence_reflection_sign_and_before_refraction[image_power]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_ray_diagrams_live.py::test_image_incidence_reflection_sign_and_before_refraction[image_power_glass]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_ray_diagrams_live.py::test_ray_diagram_field_range_and_finite_object_reference[fields_mixed]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_ray_diagrams_live.py::test_ray_diagram_field_range_and_finite_object_reference[fields_negative]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_ray_diagrams_live.py::test_ray_diagram_field_range_and_finite_object_reference[finite_object]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_release_handoffs_live.py::test_coating_layer_polarization_to_image_and_reload：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_wavelength_detector_pairs_live.py::test_detector_wavelength_pair_native[fluorescence-DetectorPolar]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_zrd_replay_route_live.py::test_recorded_polar_replay_execution_native：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_2026r1_star_preloaded_live.py::test_2026r1_star_fit_read_unload[deformation]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_2026r1_star_preloaded_live.py::test_2026r1_star_fit_read_unload[direct_index]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_2026r1_star_preloaded_live.py::test_2026r1_star_rigid_body_operations[rigid_body]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_2026r1_star_preloaded_live.py::test_2026r1_star_rigid_body_operations[configure]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。
- tests/native/test_2026r1_star_preloaded_live.py::test_2026r1_star_rigid_body_operations[remove_from_fea]：初次失败，后续复测通过；首次记录保留在 test-results.jsonl。