# D009：扫描镜—入瞳共轭与扫描性能

2026-11-11，完成。源码102工具、139分析请求，发行1.0.0保持101工具、132分析请求。环境Python3.14、OpticStudio24.2.0/build240529、PremiumEdition；主仓src，全部原生执行串行。

## 实现与合同

run_analysis:scan_pupil使用相邻输入面、前CoordinateBreak、平面Standard MIRROR、后CoordinateBreak；两断点与镜面共点，前后施加相反扫描增量，保持下游坐标。逐面读回参数、厚度及GetGlobalMatrix；正式CreateDirectUnpol批量追迹至镜面、目标孔径及像面，每次关闭BatchRayTrace。副本关闭后源曲面/solve和修订保持。

九条非退化中心/位置/斜率扰动光线构造四维差分矩阵。状态(x,y,l/n,m/n)，目标共轭局部Z=-B/D、倍率A+zC；孔径在镜面侧前像Z=B/A、倍率1/A。目标面是否系统光阑明确返回，入瞳按物理光阑前像定义。有限圆束等权方格采样通过率，分开追迹错误和截断。输出beam walk、主光线角、线性扫描拟合/畸变、全局物理位置和方向、间距排名及最佳模型。

## 模型、参考与预设容差

镜面后距离50mm至第一片50mm原生Paraxial面，两片间距100mm，第二片后50mm为目标瞳面，再10mm至像面；反射后空气厚度为负值。镜面角-1/0/1度；间距扫描-45/-50/-55mm；单位mm。光束半径1mm、5×5圆内13点；波长采用基线首波长。独立4f矩阵倍率-1，B=-(spacing+50)，光束走离绝对值|(spacing+50)tan(2angle)|；像面方向角Y转轴对应X角-2angle。

预设矩阵/走离门槛1e-8+1e-6×|参考|，方向分量1e-7。正式反射方向=入射方向-2(入射方向·法线)法线，结合GetGlobalMatrix及从输入面起的反射奇偶性。半径0.6mm孔径覆盖13点中的5点，预期通过率5/13，避开采样边界。

## 检查结果

- 56普通测试通过/0.63s，覆盖请求约束、非退化差分、矩阵逆、反射、物理方向、截断统计及相关光线/瞳消费者。
- 最终真实stdio原生1 passed/24.27s，70次数值比较全部通过，最大绝对差1.07e-14。
- 倍率-1，4f B约3.55e-15；1度镜面增量得到2度光束偏转。±5mm离共轭在1度下走离约0.174604mm；最佳间距-50mm。
- X/Y双轴、45度折叠、非中心光束、半步长差分收敛、物理光阑入瞳前像、已知截断通过率、保存重载、rows分页及绘图均通过。图像已查看。
- 失败取得failed、实际取消取得cancelled；副本关闭且源曲面保持，后续分析成功；最后disconnect ok=true。

最终原始记录：.local/runs/runs/scan_pupil_native_c9bc5dd948，calls.json/checks.json、模型、光线CSV和scanner.png。此前3b99dcaa60通过；28d14620ab为独立参考B符号调整前记录；bc51b81ac9为连接阶段REQUEST_TIMEOUT，未运行光学修改，独立重试后恢复。原生未有实例留在运行。

## 接口探查与依据

.local/evidence/development/D009包含reflection-probe.json、coordinate-break-probe.json、four-f-probe.json及对应脚本。AfterSurfaceMode是只读属性，正式模式方法SetAfterSurfaceModeExplicit/Pickup/Reverse可用。面前属性倾斜与原生曲面矩阵含义需分别处理；本请求采用显式CoordinateBreak，记录名义45度折叠及零度模型。

官方手册1068页ENPP为居中系统相对第一面的近轴入瞳位置；本请求返回实际物理孔径的局部差分前像，保留坐标和矩阵。GitHub参考G5固定commit6a197e467c7fceeb51ab651b3dbea21d9781d94e的zemax_scan_pupil_check组织思路，计算独立实现。

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/unit/test_scan_pupil.py tests/unit/test_ray_diagrams.py tests/unit/test_pupil_aberration.py tests/unit/test_development_roadmap.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d009-affected-final
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_scan_pupil_live.py --run-zemax -q -s -p no:cacheprovider --basetemp .local/tmp/pytest-d009-native-final
```

请求示例examples/requests/scan-pupil.json，使用说明docs/topics/analysis/scan-pupil.md，schema已同步。累计9/16，下一项D010鬼像/杂散光路径诊断；达到10项执行集中检查。
