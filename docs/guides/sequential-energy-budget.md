# 顺序系统逐面能量损耗

`run_analysis`中的`sequential_energy_budget`使用同一组偏振光线逐面终止原生BatchRayTrace，并比较截至目标面的累计强度。每条输入含射线坐标、波长和正权重；`input_mode`选择归一化瞳坐标或曲面局部坐标。Jones幅度满足`jx²+jy²=1`。

```json
{"request":{"kind":"sequential_energy_budget","input_mode":"Normalized","rays":[{"wavelength":1,"hx":0,"hy":0,"px":-0.5,"py":0,"weight":1},{"wavelength":1,"hx":0,"hy":0,"px":0.5,"py":0,"weight":1}],"polarization":{"jx":1,"jy":0},"first_surface":1,"input_power_w":1}}
```

省略`last_surface`时统计至像面。`surfaces`按面号返回成功、渐暈、追迹错误及缺失数量，加权出射强度、累计透过率和相邻目标面的保留率。`rows`分页返回面号、ray_id、状态、坐标、方向及强度。设置`input_power_w`后按射线权重将相对强度换算为W。`series`包含累计透过率和逐面保留率。

原生追迹结果为到达目标面后的累计量：N-BK7平行平板受控试验中，前表面强度0.9576119544，后表面0.9165667153，像面保持0.9165667153。逐面损耗由相邻目标面的累计值差分计算，包含该区间内的原生偏振传播、表面交互和已统计的光线状态。此入口提供的结果可定位渐晕面及衰减区段；膜层吸收、体吸收和分光支路使用各自原生专用分析。

归一化偏振追迹配合同输入的非偏振原生追迹读取渐晕码，每统计面产生两个子任务。`resources.closed_child_tasks`记录完成释放的子任务数；`state`区分成功、渐晕、追迹错误及缺失。Direct输入使用`start_surface`局部坐标和方向余弦，首个统计面须位于该面之后。

结果的区段累计损耗包含界面与介质传播，已用裸板、吸收平板、无损薄膜和MIRROR的原生RTA/材料透射率交叉对照。MIRROR使用当前系统原生反射率。逐面差分和`identified_vignetting_surfaces`分别用于定位衰减与截断。
