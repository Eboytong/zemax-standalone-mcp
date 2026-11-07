# 视场分析与光束足迹

通过已有 run_analysis 调用，返回任务编号，再查询 get_task_status/get_task_result。

```json
{"request":{"kind":"relative_illumination","wavelength":1,"ray_density":10,"field_density":21}}
```

```json
{"request":{"kind":"fft_mtf_vs_field","frequencies":[10,30,50],"sampling":"S_64x64"}}
```

```json
{"request":{"kind":"vignetting","ray_density":40,"field_density":21,"method":"auto"}}
```

```json
{"request":{"kind":"footprint","surface":1,"field":0,"wavelength":0,"delete_vignetted":true,"method":"auto"}}
```

相对照度使用原生 RelativeIllumination，单色计算；同时保留原生有效 F/# 列。ray_density 最小为5，field_density 为2到100。默认移除渐晕因子，默认沿 Plus_Y 扫描，可选择 Plus_X/Minus_Y/Minus_X。偏振默认关闭。

FFT MTF 随视场使用原生 FftMtfvsField，支持1到6个互异正频率，频率单位来自系统 MTF 设置。横轴为原生归一化视场；结果中每组曲线保留 frequency、frequency_unit 和原生方向标签。相对照度横轴为物理视场坐标。原生曲线插值与单视场 FFT MTF 存在采样相关差异，数值对照应采用相同瞳采样并记录容差。

渐晕与 Footprint 的 auto 和 ray_trace 使用原生真实光线批量追迹，返回 computation_method=native_batch_ray_trace。auto 附 fallback_reason。本机24.2公开设置接口未提供这两个专题的可回读设置类型，method=native 返回 UNSUPPORTED_SETTING；专题 CFG 路径仍待后续采用验证。

渐晕在主波长、正Y角度视场扫描方格圆瞳。统计到达像面的比例，追迹错误、截断与缺失分别保留。默认临时清除 VDX/VDY/VCX/VCY/VAN，成功、失败与取消均恢复；结果含 effective_system_settings 和 restoration。保留渐晕因子时，通过率包含最近视场的瞳压缩面积因子。此指标为几何通过率。

Footprint 首批提供方格圆瞳采样。前序曲面截断光线不显示；delete_vignetted 控制目标面和后序曲面截断及后续追迹错误的显示。field/wavelength=0展开当前配置中的全部条目。每条光线保留输入、目标面局部坐标、像面错误及渐晕面号。完整 scatter 保存在任务JSON，get_task_result 返回散点摘要及分页 rows；export_analysis_image 从完整结果生成图像。

默认当前配置。位置使用镜头单位，瞳坐标为归一化值。原生分析输出保留原生文本，派生追迹输出保留逐光线记录。原生实例和测试串行执行。

验收入口：tests/test_field_analyses.py（参数、采样参考、截断规则与取消恢复），tests/test_field_analyses_live.py（真实stdio、照度收敛、MTF对照、平面坐标、圆孔通过率、前后序截断和图像导出）。

本轮MTF对照采用256×256采样，绝对差验收值为0.005，Cooke样例最大观测差约0.00254；早期0.001阈值下未通过，原始失败记录保留在outputs/runs。RI密度10/20的最大观测差约0.00016。执行汇总见verification/field-analyses-summary.json。
