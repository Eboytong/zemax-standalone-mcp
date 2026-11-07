# 能力与文档索引

当前功能范围见 [能力说明](../能力说明.md)，版本与发行状态见 [README](../README.md#当前状态)。

- [工具清单](tools.md)
- [完整请求模型](tool-schemas.json)
- [调用、单位与故障处理](usage.md)
- [使用示例](../examples/README.md)

- [样板目录：原生活动目录和显式TPD文件读取](test-plates.md)

Power Map增量448：run_analysis新增power_field_map/power_pupil_map，implemented；正式POWF/POWP、单位、范围与验收缺口见[屈光力分布](power-maps.md)。

- `ima_bim_viewer`：读取 IMA/BIM 原始图层并可通过 ImageSimulation SourceBitmap 取得原生 RGB 显示；详见 [IMA/BIM 查看](ima-bim-viewer.md)。
- `ray_database_viewer`：通过正式 RayDatabaseReader 查询 ZRD 光线段并分页；详见 [ZRD 查看](ray-database-viewer.md)。

2026-11-07 B006增量519：`sag_table`返回`statistics_sampling`，明确BFSD摘要独立于请求rows采样，列出本机高阶正/负及环形条件验证的1000区间含端点规则；原生摘要保持原值。能力回读指向MF-01/progress519-statistics.json。Power Map新增离轴球面/双轴与非中心瞳数值证据524/526，范围见power-maps.md。ASAT/ASAB在521正式Run再次拒绝，沿用原cad_formats状态。完整条目仍按剩余验收缺口记录。


2026-11-07 B006增量547：FFT线/边扩散完成本条目数值与生命周期验收。默认FFT瞳拉伸后的独立新光线参考在64/128采样与两焦面通过0.005门槛，最大差0.000810981；复振幅/相位、LSF/ESF和分页/PNG/取消重载回归通过。能力回读指向CV-01/acceptance547-spread.json，B006现3/10。

共用修复542：MCE数值单元格按已探查的九位getter精度检查采用，并返回value_readback和mce_double_readback说明，实际内部曲率精度另以LDE投射检查。FullFieldSpot增加方向余弦单位/坐标量说明及负半径拒绝，真实结果出口继续implemented。SagTable补单位、多配置与Composite证据，完整准则保持implemented。


2026-11-07 执行565：nsc_geometric_mtf新增frequencies原生终点查询，单点/非对称、当前探测器/ZRD共64项DFT最大差2.701e-8，生命周期及重载通过，计入B006。默认原生显示曲线保持历史精度状态。SagTable新增旋转截面检查、孔径来源及无孔径任务副本斜率，13项原生回归和采样中取消通过；完整准则仍implemented。


2026-11-07 QuickYield574完成受控参考验收。结果evaluation返回源主波长/所选波长身份及受控参考条件：Cooke需按所选波长求值主波长相关solve；受控折射波前去活塞和线性瞳倾斜后匹配。源模型保持，原生结果数值保持，Standard高阶近似限制保留。最终原生4项、普通80项通过。B0065/10，详见TO-01/acceptance574-reference.json。


2026-11-07 SagTable582增量：best_fit_sphere三准则及reverse全口径SSAG球面曲线已接入；制造偏移/去除量缺正式契约时明确null。正负曲面402数值检查、7项原生及68项普通通过，详情docs/sag-table.md与MF-01/progress582-criterion-curves.json。完整条目保留implemented，B0065/10。


SagTable589更新：MinimumRMS无偏移约束返回vertex_offset=0，其余待验物理偏移保留null；去除统计按准则适用性区分。独立RMS球面拟合参考通过，587正负曲面2项原生及589定向普通72通过，582七项回归沿用。B006仍5/10；Gradium584共同原生求值与CAD585四组层号65535的具体缺口均已登记。

2026-11-07 增量591–598：FullFieldSpot空结果错误附八类正式计数；三组Cooke探查仍全空。Power Map附中心有效性范围、原生环不可用状态、查询/原值状态及零值计数，偏置独立保留零值身份；原生596八组及分页重载通过。普通597定向71通过。材料临时模型系数的正式接口审计598沿用现有反射，无新增原生会话。B006仍5/10，完整功能验收缺口见各条证据。

2026-11-07 FFT Surface610：原生波前/独立批量OPD约9.8万点相位一致；正式Real/Imaginary_Coherent复瞳的独立自相关与非相干MTF全网格轴上/离轴差6.66e-16/.0049502。离轴支持域和相位尚未由测试的独立物理映射恢复，保留implemented。普通25通过，九个分析及只读几何探查关闭，详情docs/fft-surface-mtf.md与CV-01/progress610-coherent-pupil.json。B006仍5/10。

2026-11-07 SagTable622：RMS两准则新增native_bfs_fit，返回正式DSAG半径、原始Z偏移及SSAG半径一致性。正负EvenAspheric原生617两例通过，普通620为75通过；已知piston与同形Zernike控制仍有制造基准/拟合适用差异，完整条目保留implemented。详见docs/sag-table.md及MF-01/progress622-dsag-fit.json。

2026-11-07 Gradium633：GRIN结果新增正式曲面/材料/轮廓文件/配置及RefN与capping回读。常量Gradient5对照排除共用SGRIN误差；实际Snell折射确认原生GetIndex偏差。正反轮廓右cap行为通过、左cap2/3四组仍报错。普通97、生命周期诊断1及Gradient1回归1通过；完整Gradium继续in_progress，B0065/10。详见docs/grin-profile.md。

执行634/635：PowerMap毫米/厘米16次分析证明屈光度不变、EFL按镜头单位缩放及分页/重载/关闭，8次数值比较通过；Gradium正向同GSF常量Gradient5控制误差<5e-15，而Gradium五点最大6.251e-6。原功能状态和数值门槛保持；证据CV-02/progress636-unit-scaling.json、MA-01/progress636-positive-profile.json。


## 637–641证据同步（2026-11-07）

637–639单项式0–9阶为浮点精度；10/11阶单位幅度误差5.104e-9/6.124e-10，zmax1/5.8归一化结果一致。继续确认高阶正式求值、左端capping及专题选择，保持in_progress。

640普通45项、641正负原生2项通过；新增1001节点径向加权斜率摘要。继续制造偏移符号/基准、面型拟合适用性及反向制造摘要，保持implemented。

当前状态以[交接](development-handoff.md)为准，历史计数属于对应执行记录。
