# D004 Power Map控制与生命周期验收

2026-11-09，主仓C:/Users/tonge/Desktop/mcp，源码0.1.62未发行工作区，主仓.venv Python，进程COMPLUS_LoadFromRemoteSources=1；原生OpticStudio24.2.0/build240529/PremiumEdition，当前配置1，Millimeters，原生执行串行。

## 计划、请求与修复

执行既有E2四半径和E3非对称孔径实验，核对Power/EFL零值、中央参考光线状态和原生查询变化；再用真实stdio验分页、保存重载与模型保持。两种入口保持power_field_map和power_pupil_map，完整字段见原始calls；原容差atol2e-4、rtol2e-5保持。

修正两个直接Backend探针的update_system_settings嵌套：调用层保留原请求，backend_arguments记录实际flat SystemPatch。FakeBackend现在先使用真实COMMAND_MODELS验证每个请求，新增两项检查防止普通测试放过错误包装。

## E2四半径

命令：`python -B -X utf8 scripts/probes/CV-02/power_radius_sweep018.py .local/evidence/development/CV-02/power-radius-20261109`。

模型为单球面折射空气至N-BK7，波长.5875618µm，入口瞳直径10mm，目标面1为光阑，后厚50mm、半口径8mm。两视场(0,0)/(2,2)提供非零归一化范围，3×3网格。正式POWF/POWP显式参数作为替代计算来源，任务自有JSON保留rows、grids及actual_settings。

独立轴上参考EFL=nR/(n-1)，Power=1000/EFL[mm]，n=1.5168000345005883，原生材料查询来源沿用已有记录。四半径各运行field/pupil的Power/EFL，共16项成功任务。

| 半径mm | pupil Power/D | pupil EFL/mm | 既定参考门槛 |
| ---: | ---: | ---: | --- |
| 50 | 6.814355276657183 | 146.7490260488084 | 两项通过 |
| 1000 | .34071731569701136 | 2934.9843812730282 | 两项通过 |
| 1e6 | .0003407173145738674 | 2934984.3909479403 | 两项通过 |
| 1e9 | 3.407173145738663e-7 | 2934984390.94795 | 两项通过 |

同半径field中心值与pupil中心值一致，四组均未观察到零。这限定本次测试范围，零半径返回0的正式语义及更小值阈值仍待依据。

## E3孔径控制

首次命令输出位于`.local/evidence/development/CV-02/power-aperture-20261109`。默认FloatingAperture请求清除为None被正式回读拒绝，PARTIAL_UPDATE完整保留失败曲面、checkpoint及原始cause=SETTING_REJECTED，shutdown正常关闭；本次原生流程未继续使用该失败模型。

随后建立新的独立实例，将无截光基线设为半径8mm的显式CircularAperture，7个受控瞳点均通过。半径4mm对称孔径及X偏心1.5/3mm在同一映射下比较。命令：`python -B -X utf8 scripts/probes/CV-02/power_asymmetric_aperture018.py .local/evidence/development/CV-02/power-aperture-20261109-r2`。

四组全部执行成功。px为[-1,-.6,-.2,0,.2,.6,1]，py=0。基线全部通过；对称孔径截断±1；两种偏心截断-1和-.6。所有位置/方向均可读取，28项映射比较在1e-12门槛内保持。孔径参数实际回读保留。

对称孔径下Power/EFL逐位不变；偏心下Power最大差1.7763568394002505e-15、EFL最大差5.684341886080802e-14。既有value_changed字段仅表示逐位差异，新change_diagnostics明确记录最大差、可比较数量及是否超过原参考容差；本次均未超过。新增两个普通用例区分浮点量级差异与.1量级变化。对已取得原始数据离线生成change-diagnostics.json，原anchors保持原始执行内容。

这些结果说明受控截光变化未造成超过门槛的查询差异，尚未证明原生内部微分采样环的有效性规则。

## 分页、保存重载与关闭

命令：`python -B -m pytest tests/native/test_power_map_value_states_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/power-states-20261109 --junitxml=.local/evidence/development/CV-02/power-states-20261109.xml`。

1 passed in15.26s。原始真实stdio请求、结果和数值检查在`.local/runs/runs/power596_value_states_1348f61238/`。覆盖平面/球面、两种Map和Power/EFL共8项分析，检查原始零值与偏置、1×1区域网格和行分页、成功终态、系统设置/曲面/评价函数保持及保存重载后的相同状态；正常disconnect。

两次直接探针disconnect返回成功，closed=true、cleanup_error=null；随后shutdown生成的回执session_id=null/was_connected=false，未将其作为之前会话的独立关闭回执。E3首次失败流程的shutdown保留了实际连接关闭。所有作业均已终态，未留待运行任务。

stdio原生回归出现一次Task history write failed/WinError5的os.replace警告，任务9835bebb5ccf4db58e057bb44df5e00c最终索引state=succeeded；原始stderr与最终索引保留，原因待定位。另有已有FRU__delta_init警告。

## 检查、状态与下一步

最终定向普通测试48项通过（tests/unit/test_power_probe_contracts.py与test_power_maps.py）。本次实际schema/请求字段未改变，原有示例继续有效。两种Map保持implemented，累计完整验收3/10、剩余93组。

尚缺原生内部采样环有效性和零EFL的正式语义。下一步取得正式定义或可区分内部环状态的实验；已有中心参考光线检查和原始零值保留策略继续采用。按队列处理其他可执行条目，D005文件选择和输入身份为下一组工作。
