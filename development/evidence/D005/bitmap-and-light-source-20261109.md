# 几何位图适配与有限共轭光源探查

日期：2026-11-09。主仓C:/Users/tonge/Desktop/mcp；源码版本0.1.62、101工具/132分析。原生24.2.0 build240529 PremiumEdition，项目.venv，进程COMPLUS_LoadFromRemoteSources=1。全部原生串行执行。

## 1. 声明范围与结论

IM-01.GeometricBitmapImageAnalysis从blocked改implemented：有类型请求、正式GBM配置、报告最终回读、原生RGB文本/BMP、三通道网格、分页、PNG及关闭已交付。独立成像参考、完整归一化与其余设置、取消/恢复范围继续验收。

CV-02.LightSourceAnalysis保持blocked：有限共轭适用条件已满足，正式文本出口确认，缺DAT/SDF选择和输入身份。新增有限共轭报告解析；空文件名/零尺寸返回不可用状态。

本次新增完整验收0，累计3/10；剩余93组，100条源记录/95个编号。未构建或发行。

## 2. 正式依据与探查

本机2024 R2手册留存：`.local/evidence/development/NS-04/runtime068-sequential/modifysettings.txt`，GBM_FIELDSIZE/RAYS/XPIX/YPIX/XSIZ/YSIZ/INPUT/OUTPUT/SURFACE/ROTATION；`.local/evidence/development/IM-01/manual-index-831.txt`和`manual-index-832.txt`说明几何位图、全Y视场、角度旋转、每源像素每颜色光线及像素尺寸。

接口仍AS_Default。使用SaveTo→ModifySettings→LoadFrom，并从报告验证采用；未将ModifySettings的true单独当作采用证据。

运行：
```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/D005/bitmap_contracts.py .local/evidence/development/D005/bitmap-contracts-20261109
```

输入为任务自有7×5非对称RGB BMP，红区x<2、绿区y<2、蓝区x>=4/y>=3。原始source.bmp和35个像素值保留于探查目录。原生ImagesDir临时资源在shutdown后删除，owned_resource_removed=true。

五项任务成功：文件名/绝对路径、目标面7/6/1、旋转0°/1°/90°；输出17×11、像素0.05mm。报告面号1/6/7与请求一致；历史GBM_SURFACE=0被原生钳制到1，产品surface要求正编号。所有报告187个RGB像素与BMP顶向下坐标逐点差0；错误翻转方向最大差255。已据此转为产品Y向上像素中心坐标。

原始：`.local/evidence/development/D005/bitmap-contracts-20261109/probe.json`及各TXT/BMP/CFG。原生会话76e17805d981464b9743a88513555031；设置/曲面保持true；shutdown回执was_connected=true、native.closed=true、forced=false、error=null。

## 3. 产品实现与设置回读

新增bitmap_image.py；GeometricBitmapImage请求改为位图专属字段，保留kind、input_file、surface、field_size、rotation，增加rays_per_pixel和独立X/Y像素/像元。此前误继承几何IMA请求的字段返回INVALID_ARGUMENT，防止将总光线数误作每像素数。

输入绝对路径或ImagesDir文件名；验证存在性与BMP/JPG/PNG扩展名。配置和输出均任务自有。最终报告核对文件、面号、角度、视场高、光线/像素与X/Y组合，保留报告舍入精度。结果为RGB显示值，像素坐标X右/Y上、中心0.5起；记录实际像元尺寸，物理原点未确认。原生显示归一化沿当前条件；独立通量含义仍待验。

第一次真实stdio暴露RGB后存在“正常化强度值”附表；已修复解析分段，保留原始报告。失败任务和XML保留，未计成功。

## 4. 普通与真实stdio检查

最终普通命令：
```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/unit/test_light_source_report.py tests/unit/test_bitmap_image.py tests/unit/test_image_viewers.py tests/unit/test_imaging.py tests/unit/test_scene_images.py tests/unit/test_contracts.py tests/unit/test_development_status_report.py -q -p no:cacheprovider --basetemp=.local/tmp/bitmap-light-final-20261109-r2
```
181 passed，1.52秒。覆盖请求语义、有限值/尺寸/旧字段拒绝、RGB缺行/重复/越界、最终回读、设置拒绝/关闭失败与重连状态、资源预检查、有限光源空输入和异常数据，以及受影响既有消费者。此前172项集合包含于最终相关范围，分列历史，不累计测试数。

原生命令：
```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -m pytest tests/native/test_bitmap_image_live.py --run-zemax -q -s -p no:cacheprovider --basetemp=.local/tmp/bitmap-native-20261109-r2 --junitxml=.local/evidence/development/D005/bitmap-native-20261109-r2.xml
```
1 passed，13.71秒。真实stdio依次运行0°、90°和全黑三任务。验证绝对输入名/旋转/曲面/光线数回读、17×11 RGB全部像素、7×5绿通道分页、两张PNG、成功任务关闭无警告、系统/曲面保持及disconnect成功、服务器正常退出。原始`.local/runs/runs/bitmap_cfg_rgb_70baab7b07/`。

另一个原生用例test_geometric_bitmap_invalid_resource_preserves_session通过：拒绝IMA输入后会话可继续查询资源，原始`.local/runs/runs/bitmap_interface050_5be13dc7cf/`。初轮bitmap-native-20261109.xml含1失败/1通过；修复后只复测失败及受影响范围。FRU__delta_init警告仍出现，未定位其原因。

RGB与原生BMP使用整数差0的对应门槛，属于同次原生输出的读取/方向验收；独立光学数值参考尚待建立。没有以该对应关系关闭完整功能。

schema通过scripts/development/export_tool_schemas.py真实stdio导出；版本保持0.1.62。

## 5. LightSource有限共轭控制

```powershell
$env:COMPLUS_LoadFromRemoteSources='1'
.\.venv\Scripts\python.exe -B -X utf8 scripts/probes/D005/runtime_contracts.py .local/evidence/development/D005/light-source-finite-20261109 light_source --finite
```

输入：自有工作模型，物距200mm，Paraxial焦距100mm，像距200mm；ObjectHeight、中心视场、EPD2mm、0.55µm。分析任务成功，AS_Default/AR_Default，八类集合0、文本true、消息0。报告文件名为空，探测器0×0mm（40×40像素），源/通过功率0 Lumens，峰值0 Lumens/cm²；1600行RGB/XYZ全零。解析后available=false、reason=source_or_detector_not_defined，输入身份未确认。

设置与曲面在分析前后保持true。会话cb50f135d4da4762a1f8f9cb0e97eeeb；shutdown回执正常关闭。原始probe.json、TXT、CFG及离线parsed-summary.json保留于上述目录。原探针中的parse_error反映解析扩展之前的实际状态，未覆盖历史。

解除条件：取得正式DAT/SDF文件选择、探测器/通量等设置及最终采用；使用已知光线和波长建立参考。有限共轭条件及RGB/XYZ出口已确认，继续缺口集中于输入和设置选择。

## 6. 后续顺序

D005剩余图像完整参考和文件选择按新依据重返队列；准备D006光谱与方向性受控输入及正式选择探查。依赖未满足条目保留状态，继续可执行项。每项先发布实施计划，沿用逐项定向检查和十项集中检查节奏。
