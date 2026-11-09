# 本机模型与参数使用范围

适用 Windows x64、OpticStudio 2024 R2 / API 24.2.0。模型准入和逐项验收见清单（历史参考），顺序面型结果见专项验收（历史参考），规则映射、探测器、CAD与DLL依据见对应验收（历史参考）。枚举、原生参数采用、保存重载和光学数值分别判断。

## 规则波前显示坐标映射

```json
{"request":{"kind":"wavefront","field":2,"wavelength":2,"sampling":"S_64x64","remove_tilt":true,"use_exit_pupil":true,"include_pupil_mapping":true}}
```

该请求通过现有任务接口执行。原始波前值和原生坐标轴保持不变；`grids[].pupil_mapping` 提供映射，区域读取与网格使用相同的 `x_start/y_start/width/height`。完整点表保存在任务 JSON，CSV 含有效性、几何残差和 OPD 误差。

已验证条件为轴对称、有焦、无倾斜偏心、圆形无遮挡孔径、角度视场、Radial 归一化及 Y 子午线。所选波长须为主波长。Cooke 0°/14°/20°与单透镜 0°/5°分别具有三个独立单波长设计的 32/64/128 采样依据；这不等同于同一多波长设计中三个波长均已通过。多波长设计的非主波长仍有记录中的 OPD 差异，返回未支持状态及空坐标。

以像面真实主光线与正负边缘光线方向计算两个方向的 F-number：

`F = 1 / (sin(angle(d_plus,d_chief)) + sin(angle(d_minus,d_chief)))`

该量与原生 SFNO/TFNO 核对。原生显示网格的保护采样坐标为 `u=(ix-floor(Nx/2))/(floor(Nx/2)-1)`，Y 同理。令 `Fmin=min(Fs,Ft)`，解析反演为 `Px=u*Fs/Fmin`、`Py=v*Ft/Fmin`。解析逆映射一次完成，返回正雅可比行列式；几何残差表达这一显示坐标变换的逆一致性，不能解释为真实出瞳面的重建精度。

出瞳显示映射构建后逐点独立追迹，以未去倾斜的原生波前核对 CurrentAndChief OPD，单位 waves，容差 `1e-8 + 1e-7*abs(reference)`。`remove_tilt=true` 时额外取得未去倾斜参考，用户请求的波前值仍保留原样。孔径外、追迹失败和 OPD 不符的点返回空坐标及原因。`verified_regular_display_mapping`、`partial_regular_reference` 和 `unsupported_regular_reference` 分别表示该显示关系通过、有无效参考点和超出当前验证范围。取消在分块安全边界处理。

`use_exit_pupil=false` 沿用已验证的入瞳保护采样公式，`valid` 表示坐标位于圆形入瞳域内；该分支不增加逐光线孔径／传播检查，输出 `validity_scope` 明确这一范围。

## DetectorSurface 三角像素几何

```json
{"request":{"detector":2,"kind":"flux","include_geometry":true,"geometry_frame":"global","start":0,"count":200}}
```

`include_geometry` 默认关闭，仅用于 DetectorSurface；`geometry_frame` 为 `local` 或 `global`。每行保留一基 `pixel`，增加零基原生 `face`、三个顶点、顶点法线、面积、质心及原生面通量／辐照度。顶点与长度使用镜头单位，面积为该单位平方；辐照度仍使用系统实际分析单位及前缀。例如毫米镜头的 W/cm² 数值需乘以 0.01 才是 W/mm²。

数据来自 `INCERow.GetFacetedObjectData()` / `IFaceData`。读取后恢复面游标与坐标设置；不推进模型修订号。每面数值与原生探测器像素交叉核对，受控质心命中另行验证编号对应。Fast Ray Trace 可重新排列面，不按建模时的径向顺序推算像素。

## 活动参数与保护

- `get_surfaces` 增加 `parameter_start`、`parameter_count`；默认仍读取前 20 项，编号上限 254。
- `get_nsc_objects` 的请求增加同名参数，默认读取前 20 项，编号上限 250；返回 `parameter_cells`，包含标题、值、可写状态与 solve。
- `update_surfaces.changes[].parameters` 和 `update_nsc_objects.request.changes[].parameters` 接受编号与数值。只有原生活动、可写单元格可以修改；支持列表的编号上限不意味着每个面型均有该参数。
- 先设置决定活动列的阶数，再读取新活动列；无法在当前面型采用的参数明确拒绝。变量枚举、拾取保护及类型切换检查覆盖全部活动参数。已有关系需显式允许替换。
- 曲率半径输入 0 的原生回读可规范化为无穷大；该等价规则仅用于半径单元格。

ExtendedAsphere 与 ExtendedOddAsphere 的系数使用归一化半径，分别为偶次幂与整数次幂。ExtendedPolynomial 使用归一化 X/Y 单项式，按总次数及 X 指数递减排序。具体受控系数、法线和折射参考见测试与模型文件。

## 顺序面型与求解范围

六类面型的受控参考与扩展参数检查见专项验收（历史参考）。通过现有 `update_surfaces` 设置类型和实际活动参数，通过 `get_surfaces` 回读标题、数值、可写状态及求解；请求示例见[六类面型](../../../examples/requests/six-surfaces.json)。

| 面型 | 参考与适用条件 |
| --- | --- |
| OddAsphere | 圆锥基面加一至八次径向项；正负系数。一次径向项非零时顶点为尖点，顶点只检查Sag，光滑法线与折射检查使用离轴点 |
| Biconic | X半径和X圆锥系数为参数1/2，Y方向使用Radius/Conic；分别核对不同、交换主方向及X半径为0所表示的无限半径 |
| Conjugate | 六个参数为两个局部构造点，两个Z均非零；同号用距离和、异号用距离差，参考求根取通过局部顶点的连续分支 |
| ABCD | 参数1–4及5–8分别形成X/Y矩阵；受控真实光线按高度和方向斜率 `l/n、m/n` 计算，输出再归一化为方向余弦。该几何参考不提供OPD、衍射MTF或Zernike依据 |
| RetroReflect | 平面空气／玻璃按传播和Snell定律；MIRROR使用原生负折射率／负厚度约定，实际回返路径另行核对，不直接把API余弦取负作为物理方向 |
| JonesMatrix | 参数按Ar/Ai、Br/Bi、Cr/Ci、Dr/Di排列；仅对轴向入射、无倾斜偏心的X/Y/45°/圆偏振及恒等、线偏振器、四分之一波片、实旋转矩阵作结论；以同几何恒等矩阵去除共同传播相位 |

ExtendedAsphere/ExtendedOddAsphere最多240项，对应末系数参数254；ExtendedPolynomial最多230项，对应参数244。参数13控制参与计算的最大项数，参数14为归一化半径。降低项数会使后续系数停用；先增加项数，再读取并写入新活动系数。同一请求降低项数并写入将停用的系数，返回 `CELL_NOT_WRITABLE`，不推进修订号。

系数采用Fixed、Variable或同列SurfacePickup前，须检查该单元格的原生支持。拾取关系未经显式允许不得覆盖；允许替换时须确认Fixed模式实际采用后再写值。模式转换或写入未采用会停止同批后续修改，保留检查点与部分修改详情。数值、模式及关系分别在 `.zos`、`.zmx` 保存重载后核对，具体参数范围以专项验收记录为准。

三类扩展面型的完整求解用例限定参数21，拾取来自前方同类曲面，比例1、偏移0。项数3/30/最大值、归一化半径1.2/2 mm及末系数254或244分别有Sag依据；不由此推定每个系数的全部求解组合已通过。记录中的后方曲面拾取请求未采用SurfacePickup，接口返回明确错误，该条件保留未通过状态。

## CAD、DLL 与版本限制

STL 参考直接读取官方 ASCII 或二进制三角形，以独立射线—三角形交点核对原生结果。STEP/IGES 需要可独立确定的几何、尺寸和变换；原生加载不代替几何依据。每个文件的状态单列。

对象、光源和体介质 DLL 的准入要求本机有对应源码；源码和二进制按一个模型登记。原生参数及重载与源码公式／分布测试分别记录。随机模型固定 seed=42、10000 条输入光线，统计判据采用执行前确定的六标准误差。MIRROR 材料的实际反射率不预设为 1；对象几何反射方向与探测器／原生分支功率对应分别解释。

Reverse Radiance、REVR 及 ReverseRadiance Detector/Target 在 [官方 23.2 版本说明 §2.2](https://community.zemax.com/opticstudio-release-notes-71/opticstudio-23-2-release-notes-4278)中列为移除功能，本机 2024 R2 登记为版本不可用。其余未完成范围见本包能力说明。
