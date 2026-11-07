# AN-04 RMS与五焦面光斑

通过run_analysis调用，返回任务编号。RMS曲线使用series；五焦面统计使用rows分页，另附可直接绘制的RMS/GEO曲线。

RMS Field Map另见[`rms-field-map.md`](rms-field-map.md)，它输出二维RMS/波前/像斑网格。

```json
{"request":{"kind":"rms_vs_field","data_type":"SpotRadius","method":"RectArray","sampling":"S_64x64"}}
```

```json
{"request":{"kind":"rms_vs_focus","minimum_focus":-0.1,"maximum_focus":0.1,"focus_density":20}}
```

```json
{"request":{"kind":"through_focus_spot","field":0,"wavelength":0,"delta_focus_um":100}}
```

RMS默认波长1、SpotRadius、Centroid、RectArray/64×64，偏振与衍射辅助线关闭。GaussQuad使用rings，省略时为3（1–20），与显式sampling互斥。默认RectArray的rings须省略。采样未传时请求记录可为null，实际设置完整回读。

RMS数据类型支持Wavefront、SpotRadius、Spot_X、Spot_Y、StrehlRatio；StrehlRatio要求单色波长。原生拼写StrehlRation由适配层映射。密度接受5–100的5倍数并映射到原生枚举。原生返回的实际曲线点数独立记录为actual_point_count。

RMS随视场默认Plus_Y、密度20、移除渐晕因子开启；随焦移默认范围−0.1到+0.1镜头单位、密度20，绘制各定义视场。波长0按原生分析语义处理，结果保留native_labels与column_metadata，区分单色、多色和视场。未识别的标签原样保留。光斑单位µm，波前waves，Strehl无量纲，焦移轴为镜头单位。

离焦光斑固定五面：−2、−1、0、1、2倍delta_focus_um。默认步长100µm、全部视场/波长、Centroid、Hexapolar和密度6。先执行原生ThroughFocusSpot，本机GetTextFile可返回false，此时记录native_text_exported=false及导出原因；各面的统计来自工作副本中独立运行的标准光斑，明确记录child_task_id及computation_method。

临时焦移按镜头单位换算并加到像面前厚度。每面从基线加载，完成、异常和取消均恢复。原生求解暂时固定并随原镜头恢复；恢复失败保留检查点并要求重连。模型修订随内部恢复推进，外层结果保留初始上下文与restoration。

RMS与ThroughFocusSpot及其标准光斑子任务使用New_Analysis_SettingsFirst创建，先设置后计算。原有其他分析的创建路径保持现有实现。

验收入口：tests/test_rms_analyses.py、tests/test_rms_analyses_live.py。覆盖五面独立对照、矩形瞳采样RMS/OPD、焦移传播参考、GaussQuad、多色与偏振、镜面负厚度和取消恢复。Centroid波前及Strehl执行原生采用检查，独立波前参考使用ChiefRay。记录见verification/rms-analyses-summary.json。
