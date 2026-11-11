# D012：均温热补偿与无热化

## 计划与范围

本项复用现有 `update_system_settings`、MCE 单元格写入/回读、`thermal_pickup` solve、环境折射率设置和顺序光学模型。验收目标是确认均温变化下材料折射率、曲率、厚度、空气间隔和拾取关系的原生采用；STAR 非均匀热模块单独保留许可条件。

## 普通检查

- 两份普通测试合计：53 passed，0.56 s。
- `tests/unit/test_configuration_cell_precision.py`：包含 MCE 双精度回读和 9 位有效数字保护。

独立参考覆盖材料热光系数、环境温度、空气折射率归一化、机械热膨胀和曲面接触修正；非有限热系数和未显式允许的环境温度均按请求合同拒绝。

## 原生验收

执行命令：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_finite_thermal_live.py tests/native/test_thermal_mount_live.py tests/native/test_thermal_asymmetric_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d012-native --junitxml=.local/evidence/development/D012-native.xml
```

结果：`5 passed in 62.13s`，OpticStudio 2024 R2 Standalone 串行执行并正常关闭。原始记录：`.local/evidence/development/D012-native.txt`、`.local/evidence/development/D012-native.xml`；运行目录：`.local/runs/runs/finite_thermal_0_1cef179497`、`finite_thermal_50_e1d4f7cf1f`、`finite_thermal_100_79e8a280bf`、`tilted_thermal_mount_cf190b35ec`、`thermal_asymmetric_a0f761f820`。

覆盖内容：

1. 20 °C 基线、-20 °C、19.99 °C、20.01 °C、60 °C 环境温度。
2. `AdjustIndexToEnvironment`、SCHOTT/N-BK7 热光数据和材料目录回读。
3. MCE 温度单元、THIC/CRVT/SDIA/MCSD/CHZN 热拾取及配置切换。
4. 曲面接触热膨胀：`L=(L0-sag(r0))*scale+sag(r0*scale)`，覆盖平面、曲面接触和边缘截断分支。
5. 机械安装热补偿、前后曲率、基准面、倾斜坐标变换和非对称曲面。
6. 保存、重载、solve 保持、配置恢复和资源关闭。

关键误差门槛：尺寸类沿用 `1e-8 + 1e-7×|参考值|`，第一近轴数据相对误差沿用 `1e-6`。所有测试通过；未启用 STAR 非均匀 FEA 路径，继续作为独立许可/输入条件。

## 结论

底层检查与补偿工作流均已完成，D012计入完成数。D014及后续工作已完成，当前15项交付结束。

## 全温补偿工作流验收

2026-11-11。主仓fc814ef加当前工作区修改，源码版本1.0.0；Windows x64/Python3.14/OpticStudio24.2.0 build240529 Premium。

新增有类型请求 `run_analysis:thermal_compensation`。输入已有TEMP/CRVT/THIC热配置，指定参考配置、视场、波长、补偿面和正间隔边界。副本中以各配置RSCE为目标，使用原生DampedLeastSquares和MCE变量/CTGT/CTLT边界；回读补偿前后几何、材料折射率、波前、EFL及位移，保存推荐ZOS模型。源配置、曲面、solve、系统设置、MFE和修订保持基线。

输入：自建N-BK7双凸透镜，R1=50mm/R2=−50mm、厚3mm，波长550nm、瞳径2mm，机械TCE=100ppm/°C；20/−20/60°C配置，初始后间隔47.6mm，优化边界40—60mm，10轮DLS。配置创建与pickup写入分两次调用。

最终命令：

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m pytest tests/native/test_thermal_compensation_live.py tests/native/test_thermal_chromatic_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d012-final --junitxml=.local/evidence/development/D012/final.xml
```

最终原生2 passed/23.96秒；前述底层5 passed/62.13秒。相关普通测试合计93 passed/3.80秒，包含热请求、共焦、热光参考、MCE精度、协议与工具适配。

| 温度°C | 初始间隔mm | 补偿后间隔mm | 位移mm | RMS前µm | RMS后µm |
|---:|---:|---:|---:|---:|---:|
|20|47.600000000|47.693534745|+0.093534745|1.362047|0.110011|
|−20|47.410532521|47.689679549|+0.279147028|4.068810|0.110857|
|60|47.789460470|47.695254201|−0.094206269|1.363013|0.110373|

24次数值对照通过：独立厚透镜EFL、目录ED热膨胀半径/厚度、温度、保存重载间隔/像质/波前/EFL。最大绝对误差5.79e−12。材料热光另由最终chromatic用例独立Sellmeier、Schott热光和空气折射率/Snell对照。单补偿间隔优化后最差RMS降低约36.7倍。

拾取保护拒绝、配置越界、实际取消、副本关闭、失败后复用、rows分页、PNG查看、推荐模型保存重载和正常disconnect均通过。原始calls.json/checks.json/thermal-result.json/thermal.png见`.local/runs/runs/thermal_compensation_a7fab88c33`；最终XML/TXT见`.local/evidence/development/D012/final.*`。初次用例将配置创建和pickup合并调用而被保护拒绝，原始workflow.xml/txt保留；已按正式请求契约拆分。workflow2/3为修复后的通过记录。
