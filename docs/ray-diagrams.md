# Y-Ybar与入射角随像高

两项均已完成本机原生验收，证据为`.local/evidence/development/CV-02/acceptance400-ray-diagrams.json`。当前源码包含103种分析；发行wheel0.1.60保持100种，待B005十项完成后集中发行。

## 请求

```json
{"request":{"kind":"yybar_diagram","first_surface":1,"last_surface":7,"wavelength":2,"plot_scale":0}}
```

```json
{"request":{"kind":"incident_angle_vs_image_height","wavelength":2,"field_density":21}}
```

YYbar默认首面1、末面为像面、波长1、plot_scale=0自动。曲面编号采用LDE原编号，有限物距可指定首面0；末面必须不早于首面。plot_scale使用镜头单位，正值设置两轴共同的±范围；自动值取所有返回坐标的最大绝对值，零坐标组绘图范围采用±1。绘图使用等比例方形坐标和曲面标注。

入射角默认波长1、field_density=21，密度范围2–1001，包含两端。两项使用当前配置；波长编号从1开始。Cooke原生专题默认主波长2(.55um)，源码请求默认1(.48um)，比较时使用明确相同的波长。

## 原生来源和实际条件

本机两项专题均返回AS_Default，结构化数组为空，原生文本可导出。当前实现使用正式查询/追迹参数：YYbar用PARY读取轴上边缘光线与归一化正Y主光线坐标，并逐面运行原生近轴批量追迹取得有效性；入射角用归一化真实批量追迹取得三条光线的位置、方向、截断和错误状态。actual_settings返回实际首末面、波长值、配置、视场范围或绘图范围，逐行保存原生参数或原始光线。

Y-Ybar的横轴是主光线Y-bar、纵轴是轴上边缘光线Y，两轴均为镜头单位。点按曲面顺序相连，保留原生局部坐标。正式定义见[2024R2 Y-Ybar Drawing](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Y_Ybar_Drawing.html)。

入射角扫描归一化Hy=0至1，使用Py=−1、0、1三条光线。径向归一化的物理范围为0至最大视场半径；矩形归一化为0至最大绝对Y。混合X/Y视场及全负Y视场已与本机专题文本核对。横轴使用该组主光线实际像面Y截距，单位为镜头单位；纵轴为本机有符号Y-Z角度，单位为度。有限物距ObjectHeight的视场值按镜头单位返回。

材料像面在独立原生模型副本中移除像面折射，取得本机专题使用的入射角约定；实际材料读回为空。非标准材料像面先用原生追迹核对交点与法向的平面条件，再在副本中采用中性平面。无材料像面保留其原生面型行为。控制用例显示：无材料Paraxial像面的功率影响专题角度；设置N-BK7后，专题使用中性平面的角度。该本机条件行为连同原生文本、实际面型及副本状态保留在结果/证据中。

原生适用条件为旋转对称、无渐晕且像面为平面，见[2024R2 Incident Angle vs. Image Height](https://ansyshelp.ansys.com/public/Views/Secured/Zemax/v242/en/OpticStudio_User_Guide/OpticStudio_Help/topics/Incident_Angle_vs_Image_Height.html)。trace_conditions_met记录三条光线及局部法向检查结果。截断或追迹失败的角度以null返回，rows保留原始错误/截断编号，summary分别统计；主光线失败时像高为null。无有效曲线返回NO_VALID_RAYS，非平面条件返回具体PRECONDITION_FAILED。

## 任务、分页和图像

rows使用start/count分页；series使用既有曲线分页，YYbar曲面标注随点同步分页。export_analysis_image导出曲线；YYbar记录实际共同轴范围和equal比例，表面编号交错排布并绘制点标记。

批量光线工具由子任务关闭。材料像面副本在成功、失败和取消时均关闭；源模型的曲面、solve、系统设置、配置及评价函数保持。关闭失败进入重连状态并保存原始错误；取消同时遇到关闭失败时返回CLEANUP_FAILED并保留取消原因。入射角结果包含ray_trace_task_id，YYbar包含validation_task_ids。

## 验收

14类原生用例覆盖Cooke原生文本、独立薄透镜和自由传播、有限物距含物面0、厘米单位、双配置、矩形/径向归一化、混合/负Y视场、负厚度镜面、玻璃/功率像面、截断、全遮挡及非平面拒绝，另覆盖分页、固定/自动绘图范围、PNG查看、错误和取消复用、保存重载及正常关闭。当前汇总915次数值检查通过，普通相关135项通过。

预设容差：原生YYbar文本5e-9镜头单位；像高文本1e-5镜头单位；角度文本1e-6度；独立物理参考1e-8+1e-7×参考值。原381日志保留错误使用ILDERow.Curvature的失败，修复使用Radius后通过。原390对混合视场的范围参考由395原生文本确认并修正，399已通过；容差保持原值。
