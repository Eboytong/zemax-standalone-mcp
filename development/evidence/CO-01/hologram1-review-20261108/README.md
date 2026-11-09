# D010：原生 Hologram1 三类衍射效率审查

日期：2026-11-08。条目为 `CO-01.DiffEfficiencyAngular`、`CO-01.DiffEfficiencyChromatic`、`CO-01.DiffEfficiency2D`。声明范围来自当前 `development/tracking/development-groups.json` 的 D010；原生 Hologram1 的角度、波长及二维效率沿用既有数值门槛。

## 来源与版本

- 发行/源码版本均为 0.1.62；当前审查另有尚未发行的标题修正。共同源码起点为 `34e1a18494015c2b383ec700b958015020b660fe`，工作区修改尚未提交。
- 原生为 OpticStudio 24.2.0 build 240529 PremiumEdition。已保存运行自 UTC 2026-11-07 20:24:23 开始，即本地 2026-11-08；本轮重新读取该运行，未重新启动原生。
- 实际运行目录：`.local/runs/runs/diff_efficiency_offaxis059_native_bdfaeee137/`；会话为 `d5946d8262334d3cb2ff2ca6358a2622`。早期 `acceptance059.json` 引用的另一运行保持原历史归属。
- 输入是安装样例 `Sequential/Diffractive components/Transmission hologram.zos` 的自有工作副本，保存重载文件为该运行的 `offaxis_saved.zos`。
- 审查脚本：`scripts/probes/CO-01/hologram_saved_evidence.py`；逐项结果为本目录 `evidence-audit.json`，三个 `evidence-matrix-*.md` 保存具体证据定位。

## 请求与实际设置

曲面 1 为 Hologram1；记录点 `(0,-100,-200)`、`(0,100,-200)` mm，记录波长 0.55 µm，体全息标志开启，厚度 0.01 mm，n1=n2=1，平均折射率 1.5，调制 0.02，收缩和折射率偏移为 0，Fresnel 关闭。S 为 X 电场、P 为 Y 电场，系统采用 XAxisMethod。当前配置、视场 1、波长 1。

角度范围为 20.16505117707799° 至 32.96505117707799°；波长范围为 0.45 至 0.65 µm。一维采样 `S_65` 实际返回 64 点；二维 `S_64x64` 返回 64×64，扫描上边界不包含在节点中。请求与专用原生设置回读一致。

参数 21 的证据来自 `calls.json[5].response.data.updated_parameters[0].cells['21']`：value=0、solve=Fixed，响应 ok=true、warnings=[]。保存文件 SURF 1 的 XDAT 9=0 提供佐证。默认 `get_surfaces` 只返回 1—20 号参数，审查没有将其作为参数 21 的回读来源。

## 数值、结果与生命周期

独立参考为 `tests/support/kogelnik.py::unslanted_transmission` 的非倾斜透射耦合波及在壳衍射方向，比较门槛保持 `1e-6 + 1e-5 × |参考值|`。

| 检查 | S 最大绝对误差 | P 最大绝对误差 |
|---|---:|---:|
| 角度 64 点 | 5.212286158240431e-11 | 4.1728842603561134e-11 |
| 波长 64 点 | 5.219868981498621e-11 | 4.155475963329991e-11 |
| 二维完整 4096 节点 | 5.752720522167465e-11 | 5.245337497683522e-11 |

原运行 384 项检查通过；本轮离线逐节点复算补齐二维全网格，每个偏振均为 0 个超限节点。二维中心切片与对应一维扫描完全一致。角度用 degrees、波长用 micrometers、效率无量纲；二维列为角度、行为波长。曲线分页、2×3 网格区域与对应完整结果一致，六张原始 PNG 存在。

十个任务的最终状态从 `calls.json` 各任务最后一条状态响应取得：8 succeeded、1 failed、1 cancelled，均 close_attempted=true。ObjectHeight 引起的原生失败保留错误，恢复 Angle 后成功复用；2048×2048 活动任务取消后成功复用。五次曲面状态与保存重载前后的配置、视场、波长、偏振及 solve 保持。断开回执 native.attempted=true、native.closed=true、error=null、forced=false。

## 本轮显示修正与检查

原生二维 description 把波长最小/最大标签颠倒。产品结果逐字保留为 `native_description`，显示标题改为 `Diffraction efficiency versus angle and wavelength`；原生消息、轴和数值沿用。协调者已查看离线导出的修正图，原始及修正图在 `.local/evidence/development/CO-01/hologram1-review-20261108/`。

协调者在来源工作区运行：

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& C:/Users/tonge/Desktop/Zemax_MCP/.venv/Scripts/python.exe -B -X utf8 -m pytest tests/unit/test_diff_efficiency.py -q -p no:cacheprovider --junitxml=C:/Users/tonge/Desktop/Zemax_MCP/.local/evidence/development/BASE-04/parallel-01/review-hologram-title.xml
```

结果 28 passed in 0.35s。默认任务查询只暴露 close_attempted，最终应用关闭另由 close_receipt 证明。

## 主区集成与最终决定

runtime worker 已合入两个最小产品 hunk 和四个测试，保留主区已集成的材料报告解析。主区命令为：

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_diff_efficiency.py tests/unit/test_contracts.py tests/unit/test_plotting_units.py tests/unit/test_imaging.py tests/unit/test_native_bitmap.py -q -p no:cacheprovider --junitxml=.local/evidence/development/BASE-04/parallel-01/review-hologram-integration.xml
```

结果 122 passed in 1.41s；协调者读取 XML 确认 122 tests、0 failures、0 errors、0 skipped。主区集成报告为 `.local/coordination/integration-hologram.md`。显示修改未改变光学计算路径，已有原生数值和生命周期证据继续适用。

三项当前声明均审查通过，操作和分析台账同步为 done；D010 为 3/3，自上次集中检查后新增 3 项。各原生任务在既有运行中均已达到终态，最终原生实例正常关闭。当前版本保持 0.1.62；集中检查在累计十项后执行。本轮审查使用上述共同起点及未提交显示补丁；原运行未另提供 Git 提交标识。
