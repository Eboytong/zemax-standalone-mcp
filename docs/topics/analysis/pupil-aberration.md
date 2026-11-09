# 入口瞳像差扇形图

`run_analysis.kind=pupil_aberration_fan` 使用本机 `PupilAberrationFan/AS_Fan`，当前顺序配置。默认全部视场、全部波长（编号0）、NumberOfRays=101、自动显示比例、检查孔径、渐晕瞳开启。支持 `field/wavelength/number_of_rays/plot_scale/check_apertures/vignetted_pupil/use_dashes`。分析原生限定 Image 选择，计算位置为光阑面。

输出 `series` 横轴为归一化瞳坐标，纵轴为近轴光阑半径的百分比。原生使用 `100×(轴上主波长近轴截点−真实光线光阑截点)/近轴光阑半径` 的符号。标量结果保留原生子午/弧矢、视场和波长标签及无效槽；NumberOfRays=21实际返回43点。原生文本、曲线分页、图像和报告沿用现有入口。
