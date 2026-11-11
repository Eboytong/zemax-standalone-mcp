# D004 非球面与制造几何评价

日期2026-11-10，主仓C:/Users/tonge/Desktop/mcp，源码基线fc814ef及工作区变更，Python3.14/.venv。原生OpticStudio24.2.0 build240529、PremiumEdition。发行包1.0.0；源码新增run_analysis:manufacturing_geometry，当前102工具/134分析请求。

## 声明范围与正式接口

支持Standard、EvenAspheric、ExtendedPolynomial，显式圆盘半径/偏心、径向/二维采样、原生顶点球面或指定球面/平面基准、六项工艺阈值。使用LDE.GetSag及GetGlobalMatrix，只读当前配置。五点一阶/纯二阶及中心混合差分计算斜率和主曲率；厚度将前表面局部+Z直线变换至后表面坐标求交。结果包含取样位置、球面偏离、中心/最小圆周厚度、极值位置、无效点、阈值、粗细采样差值、分页明细/网格/图形。默认加密径向/网格、角采样和差分步长；极值归属明确为采样点。

## 模型、参考与容差

自建球面：前R40mm，后R−60mm，中心间距3mm，N-BK7；EvenAspheric增加k=−0.5、四阶系数1e−5 mm−3。2mm圆盘、9→17方格、16→32方位角。独立圆锥面公式/解析导数、球面曲率1/R及同轴厚度对照。前后间再插入CoordinateBreak，后面偏心(+0.2,−0.1)mm、Y倾斜2度，保存重载；以全局球面二次方程独立求物理直线交点。最后ExtendedPolynomial设置z=.02x²+.01xy+.03y²，平面基准，二维对照。

预设sag/厚度容差1e−8+1e−7×参考值镜头单位；斜率分量绝对差1e−6；球面曲率额外门槛1e−6/mm。3234数值检查通过。球面和EvenAspheric sag最大差6.938893903907228e−18mm；球面斜率分量最大差2.067790383364354e−14；球面曲率最大差6.624073164984701e−10/mm；偏心厚度最大差9.809708600982958e−11mm；自由曲面三类量合计最大差1.9109713811360507e−14。

## 生命周期与结果

模型参数读取前后保持；偏心模型重载后复算通过。大采样任务实际cancelled，取消后参数保持。无专属分析或SystemTool创建，所有查询对象由系统持有；真实stdio两次disconnect均成功。rows分页逐项对应，球面/非球面PNG成功导出并查看。圆盘外网格为null；局部导数或参考球面定义域失效保留点及原因，阈值unverified。原生异常保留类型、消息、面号和坐标。

原始证据 `.local/runs/runs/manufacturing_geometry_316bf8715e/{calls.json,checks.json}`，含原生实际参数、模型、重载、请求、采样变化、3234参考比较、终态及关闭。Standard.png、EvenAspheric.png为该记录的图像；后续补充图形单位字段不改变计算值。

## 命令与检查

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_manufacturing_geometry.py tests/unit/test_geometry_kernel.py tests/unit/test_geometry_validation.py tests/unit/test_geometry_runtime.py tests/unit/test_analysis_scenarios.py -q -p no:cacheprovider --basetemp .local/tmp/pytest-d004-consumers
.\.venv\Scripts\python.exe -B -m pytest tests/native/test_manufacturing_geometry_live.py --run-zemax -q -p no:cacheprovider --basetemp .local/tmp/pytest-d004-native2
```

普通163 passed（5.05秒），真实stdio原生1 passed（27.79秒）。普通覆盖边界、曲率、偏心厚度、网格、无效域、取消和原生错误保留。请求schema及示例同步更新。

## 外部参考与结论

G4固定commit50c225c30fab5cd4e81e134e1988c7d6cd7b5ed3的clearance.py已读取，参考其原生读回、全局坐标与工艺限值组织；本实现独立编写，采用原生sag差分及同一物理直线求交。未复制代码。D004声明范围完成，下一项D005。
