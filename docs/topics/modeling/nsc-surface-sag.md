# NSC 曲面 Sag

run_analysis(kind="nsc_surface_sag")选择当前配置的对象及原生面号。object_number从1开始；face_number沿用对象原生面号，StandardLens的前/后面为1/2。0号面可无有效采样，返回NO_RESULT_DATA并保留原生文本及消息。

采样默认S_65x65，支持33至8193的2次幂加1方阵。show_as选择原生显示类型；remove_option支持None/BaseROC/BestFitSphere/AverageSag/MinimumSag，BFS选项及偏心、旋转、保留倾斜、探测光线偏移按实际设置回读。长度和Sag值均使用当前镜头单位。Width直接对应原生设置，本机Width=2产生端点范围−2至+2，33点步长0.125。

grids.values[y][x]保留原生采样平面坐标，位置按min+index×step计算；偏心、旋转、对象倾斜条件记录在任务实际设置。sampling_summary记录有效和无效采样数。全空或全无效数据返回NO_RESULT_DATA；部分无效点为null。可按网格区域分页、绘图和报告。

keep_zrd=true与本地.zrd文件名同时提供。ZRDFilename向原生传入文件名，输出位于工作模型目录；已有同名文件返回RESOURCE_EXISTS。结果artifacts提供完整路径，可交给read_zrd读取。
