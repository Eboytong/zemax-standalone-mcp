# 入口瞳像差扇形图

`run_analysis.kind=pupil_aberration_fan` 使用本机 `PupilAberrationFan/AS_Fan`，当前顺序配置。默认全部视场、全部波长（编号0）、NumberOfRays=101、自动显示比例、检查孔径、渐晕瞳开启。支持 `field/wavelength/number_of_rays/plot_scale/check_apertures/vignetted_pupil/use_dashes`。分析原生限定 Image 选择，计算位置为光阑面。

输出 `series` 横轴为归一化瞳坐标，纵轴为近轴光阑半径的百分比。原生使用 `100×(轴上主波长近轴截点−真实光线光阑截点)/近轴光阑半径` 的符号。标量结果保留原生子午/弧矢、视场和波长标签及无效槽；NumberOfRays=21实际返回43点。原生文本、曲线分页、图像和报告沿用现有入口。

验收包括入口瞳与光阑平面重合的双波长零参考（344点），Cooke三个视场、子午/弧矢258点与独立批量真实光线/轴上主波长近轴光线对照；固定容差为1e-8+1e-7×参考值（百分点），最大误差2.49e-14。保存重载、曲面保持、分页、三张PNG、分析关闭和disconnect通过。初次参考采用相反符号的失败原始结果保留。见 .local/evidence/development/CV-01/acceptance073.json。
