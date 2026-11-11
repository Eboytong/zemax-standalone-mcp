# 点状荧光共焦响应

`run_analysis` 的 `confocal_response` 使用两个独立光学模型计算点状荧光样品的轴向响应：照明系统将光聚焦到样品，检测系统把样品成像到圆形针孔。原生 Huygens PSF 提供两条光路的强度分布，原生光线提供检测端物方收集锥。

```json
{
  "request": {
    "kind": "confocal_response",
    "illumination": {"model": "C:/optics/illumination.zos", "wavelength": 1},
    "detection": {"model": "C:/optics/detection.zos", "wavelength": 2},
    "offsets_mm": [-2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2],
    "pinhole_diameters_um": [4, 60],
    "detection_magnification": -1,
    "pupil_sampling": "S_512x512",
    "image_sampling": "S_128x128",
    "image_delta_um": 4,
    "window_check": true,
    "budget_seconds": 600
  }
}
```

两文件采用毫米单位的居中顺序透射模型，支持 Standard、EvenAspheric 和 Paraxial 面、轴上第一视场及均匀圆瞳。照明像面是样品平面；检测有限物面是样品，像面是针孔。检测倍率来自 `GetFirstOrderData`；提供 `detection_magnification` 时核对请求与原生名义倍率一致。针孔尺寸始终为检测像面上的实际微米直径。

正样品偏移增加照明末面至样品的空气距离，同时减小检测物面至第一面的空气距离。其余曲率、材料和间隔保持。原生依赖 solve 导致其他参数联动时，返回 `DEPENDENT_MODEL_CHANGE`。两个模型分别选择 `configuration` 和 `wavelength`，编号从1开始；工作副本运行后关闭。

每个 PSF 设置 `Normalize=false`、`Type=Linear`、`UseCentroid=false`、关闭偏振，并保存实际设置和原生子任务。网格的 `min_x/min_y` 是第一采样点坐标，`dx/dy` 为微米。计算将各平面的相对强度除以该物理窗口内的面积积分，得到单位捕获功率密度。圆形针孔与每个像素矩形的重叠面积用解析圆面积积分计算，返回针孔功率占比。

对各向同性点发射体，检测收集比例由原生物方边缘光线确定：

$$
\eta_\Omega(z)=\frac{1-\cos\theta(z)}{2}.
$$

共焦响应为照明轴上密度、检测针孔比例和收集比例的乘积，以零偏移值归一化：

$$
R(z)=\frac{p_\mathrm{ill}(0,z)\,\eta_\mathrm{pin}(z)\,\eta_\Omega(z)}
{p_\mathrm{ill}(0,0)\,\eta_\mathrm{pin}(0)\,\eta_\Omega(0)}.
$$

这一响应采用每单位照明捕获功率和每单位检测收集功率的光学传递定义；`raw_total_um2`、原始峰值及收集比例分别保留，可用于比较归一化条件。绝对光子计数还使用实验光源功率、荧光量子效率与探测器响应。

`offsets_mm` 接受5—101个不重复值，自动加入零偏移并排序。`pinhole_diameters_um` 接受1—10个不同正直径。像面采样支持64、128、256；瞳采样支持64、128、256、512。请求总网格计算量上限800万点。`budget_seconds` 为整次扫描预算，最大3600秒。

`window_check=true` 时保持像素间距，将每条光路的像面网格边长扩大一倍重新计算。结果逐针孔返回响应最大差与半高宽相对差；分别满足0.005、1%时为 `converged`，其余为 `refine_window_or_scan`。窗口边界必须包含整个针孔。扩大窗口、减小像素间距及加密离焦步长分别用于检查窗口、横向与轴向采样。

`summary.curves` 返回逐针孔的相对响应、峰值位置、插值左右半高交点和 `fwhm_mm`。扫描没有包围两侧交点时为 `range_incomplete`，保留已取得的交点。原始分量位于 `cases`，单位功率PSF位于 `grids`，逐偏移/针孔明细位于 `rows`；分页及图像导出沿用现有任务接口。
