# 顺序转非序列（0.1.16）

run_nsc_conversion通过IConvertToNSCGroup转换当前顺序工作副本。mode=group保留顺序模式并新增NSC组；mode=pure转为纯非序列。first_surface默认1，last_surface默认像面前一面，均为原生曲面编号。范围必须位于物面和像面之间。

转换前保存检查点并增加修订号；设置逐项写入并最终回读。转换期间及失败、取消后清除旧模型/探测器来源缓存。任务成功结果保留转换前后模式、曲面或对象清单、设置、StopObjectNumber/Face及恢复路径。对象清单最多200项，完整对象可通过get_nsc_objects分页读取。混合模式现有对象工具通过nsc_surface指定组。

默认ignore_errors=false、create_sources_and_detectors=false、convert_to_global_coordinates=false、convert_stop_to_nsc_aperture=true。stop_mechanical_half_width使用镜头单位且要求启用光阑转换。overfill_factor为正数，仅在生成光源/探测器时可设，默认采用1.2。生成光源/探测器要求pure及完整内部范围，原生会转换所有曲面。光学光阑面是否可转为孔径由原生工具检查。

原生手册建议在组边界使用dummy曲面。pure模式会删除选定范围之外的曲面，基线保存在检查点。失败和取消保留实际工作副本及检查点，重新打开检查点恢复。转换属于模型修改，取消不自动撤销原生已应用的部分。

设置失败和终态均关闭工具；同时失败时保留原始原因及cleanup_warnings。原生成功后检查模式、新增NSC组或对象数，再刷新系统设置。普通检查覆盖请求范围、依赖、最终回读、原生失败、缓存失效和关闭错误。父项状态为implemented，纯NSC已有数值验收，混合组保留具体原生限制。

2026-11-06受控验收使用平行N-BK7玻璃：入口前空气2mm、玻璃2mm、出口后空气2mm。四条轴上、偏心与倾斜光线对照顺序DirectPol和纯NSC确定偏振SourceRay的ZRD结果。位置容差1e-7镜头单位+1e-7×参考绝对值，方向绝对差1e-7，功率容差1e-8+1e-7×参考绝对值。对象材料/几何/参数solve、活动光源设置、保存重载后追迹、检查点恢复及MFE保持检查通过。纯NSC379次检查通过；混合组失败恢复187次检查通过。实际误差、请求和原始输出见`verification/development/NS-01/progress282.json`及其运行目录。

本模型在`convert_to_global_coordinates=true`的纯转换后以原像面为原点：原顺序玻璃前表面z=2变为NSC z=-4，原发射点z=0变为-6，像面/探测器z=6变为0。对象映射与实际坐标保留在`converted-object-mapping.json`；转换后发射光线须采用对应的NSC参考系。

原生单光线专题在本轮请求中返回逐次变化的随机入射电场，系统Jones设置不足以固定该专题的入射偏振；功率对照使用显式`RandomPolarization=false,Jx=1,Jy=0`的SourceRay。探测器关闭光谱记录时，非活动`NumberOfSpectralData`在重载后由0变为3，原始前后快照保留；几何、光学面、活动源设置及光线结果通过验收。

混合组在dummy边界、关闭光阑孔径转换的受控模型中仍返回`TASK_START_FAILED / An unknown error occurred`。失败任务关闭、检查点重开及原始光线复测通过；解除条件是可靠的正式组转换路径或修正原生版本，随后补转换光线、功率和对象映射验收。两次会话均正常断连和关闭；普通23项通过，原生1项通过、1项明确预期失败。原生取消及光阑孔径转换保留各自未验收范围。

接口及本机手册摘录：`verification/development/NS-01/probe026.json`。调用例子：`examples/conversion026_requests.json`。完整受控序列见`tests/test_conversion_optical_reference_live.py`。历史初始化与早期失败记录按原路径保留。
