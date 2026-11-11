# D022 顺序逐面损耗验收

2026-11-11；源码a099540加本轮修改，实际导入C:/Users/tonge/Desktop/mcp/src/zemax_mcp，产品基线1.1.0。Python3.14、OpticStudio24.2.0/build240529 Premium Standalone，真实stdio。

正式入口OpenBatchRayTrace的CreateNormPol/CreateDirectPol及ReadNextResultFull返回截至目标面后的累计偏振强度。归一化偏振接口缺少渐晕码，每面追加同输入的原生非偏振追迹，合并其渐晕状态；Direct保留原生偏振码。归一化输入每面两项子任务，三面共六项，结果记录关闭计数。

3mm N-BK7平板、0.55µm、5mm入瞳：前表面0.9576119544052238，后表面0.9165667153412831，像面保持后表面结果。原生裸界面Fresnel参考以1e-8 + 1e-7×参考值对照通过。增加0.65µm对照，已知孔径三条光线逐条渐晕归属通过。活动子任务取消取得cancelled，子任务关闭且源模型保持。native-final.xml记录2通过，59.42秒；原始目录.local/runs/runs/d022_target_surface_probe_ce047a98f6/及d022_energy_cancel_6ad0f53d5b/。

吸收/薄膜/反射镜用例通过：25mm N-BK7平板，0.300/0.546µm，本机SCHOTT内部透射率参考0.05/0.996，各三条光线及不同权重，输入2W；入/出界面RTA与介质透射相乘，输出0.9587232720007838W，参考0.9587232789088326W。材料getter为float32，表内波长以5e-8µm容差核对，数值参考采用目录十进制值。无损1.38薄膜与原生RTA一致。MIRROR在0.55µm输出1.8920793987236668W，原生RTA参考1.8920793987280784W。功率门槛1e-8W + 1e-6×参考值；16项检查全部通过。分页、图像/报告导出、模型保持及断开通过。native-references.xml记录1通过、21.49秒；原始目录.local/runs/runs/d022_absorption_film_mirror_3d36d7a5ea/。自有镀膜文件finally清理。

偏心多场用例通过：5mm入瞳、自由传播10mm、面2孔径半径0.5mm、X偏心0.2mm。hx=-1/0/1与px=-0.08/0.08/0.32形成9条光线，解析落点x=2.5px+10tan(hx°)，逐条通过状态与总通过率一致；两子任务关闭。native-decenter.xml记录1通过、16.18秒；原始目录.local/runs/runs/d022_decentered_multifield_f0bc7892f7/。初次请求将x_decenter误写为decenter_x被schema拒绝，已按公开字段修正。

结果包括带权逐面统计、逐光线rows、累计/相邻面series及可选W换算。检查原生命令见对应XML，全部用例位于tests/native/test_sequential_surface_loss_live.py和test_sequential_energy_references_live.py。D022功能验收完成，统一发行回归串行复验。

跨三面截断定位复验：native-clipping-provenance.xml记录1通过、20.20秒，原始目录.local/runs/runs/d022_target_surface_probe_9106b6683b/。三面均保留同一原生渐晕码1，identified_vignetting_surfaces去重为[1]。运行中一次中间历史索引替换返回WinError5，后续最终索引正常保存为succeeded；子任务关闭由resources记录（复合任务自身close_attempted=false）。原始日志保留该警告。
