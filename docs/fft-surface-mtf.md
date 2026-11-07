# FFT Surface MTF

`run_analysis` accepts `kind="fft_surface_mtf"` for the native FFT surface MTF analysis. The typed request supports native field and wavelength indices (default 1), native MTF component, rotation, sampling, display mode, polarization, and positive scale factor. The adapter writes these settings through the native setting checker, which verifies each accepted value, and the standard analysis task returns native text and curve/grid data with its usual artifact and close handling.

```json
{
  "request": {
    "kind": "fft_surface_mtf",
    "field": 1,
    "wavelength": 1,
    "mtf_type": "MTF_Incoherent",
    "rotation": "Rotate_0",
    "sampling": "S_64x64",
    "show_as": "FalseColor",
    "use_polarization": false,
    "scale_factor": 1
  }
}
```

The installed OpticStudio 2024 R2 reflection lists writable `Type`, `Rotation`, `SampleSize`, `ShowAs`, `UsePolarization`, and `ScaleFactor` properties on `IAS_FftSurfaceMtf`. Enum values are recorded in `verification/development/BASE-01/probe/api-interfaces.json`. Native setting adoption and result access are available. Frequency grids use values[y][x], preserve native axes and original labels, and provide Spatial frequency X/Y labels for plotting. Numerical acceptance remains implemented; the outstanding conditions are recorded below.

2026-11-06 numerical diagnosis: fixed and automatic FFT PSF spacing were compared through an independent irradiance Fourier transform at Cooke fields1/3. At pupil256/image512, the automatic-spacing on-axis maximum difference was0.005695 and the chief-ray-projection off-axis maximum difference was0.076853, against the unchanged absolute tolerance0.005. Projection alone does not resolve the difference. No production frequency scaling or data correction was applied. Native data, the initial direct comparison and all failed checks remain in `verification/development/CV-01/progress285-fft.json`.

The next action is an independent pupil-autocorrelation reference and a confirmed native FFT Surface/PSF sampling and projection definition. The FFT label/7×5 pagination/PNG regression passed in native287-labels.xml. Huygens has separate accepted PSF/OTF and analytic mirror references; see `huygens-surface-mtf.md`.

2026-11-07 follow-up: Cooke fields 1 and 3 were compared against an independent DFT of the native FFT PSF at 256 pupil / 512 image sampling. Maximum absolute differences were 0.0056952725 on axis and 0.0768531720 off axis; the fixed 0.005 threshold remains. All ten axial/oblique frequency checks per field are preserved in `outputs/runs/surface_mtf283_fft_29f918eac5/fourier-comparison.json`. Analysis tasks succeeded and closed, and system settings and surfaces matched their baseline. Next isolate off-axis image-plane projection and native interpolation before changing the adapter.

2026-11-07 independent pupil experiments509–512: 50613 valid OPD/intensity rays per field at256 pupil sampling were used for a512 zero-padded linear autocorrelation. The on-axis paraxial-scale maximum error is0.0024336204, within0.005. Off-axis remains0.187954524. Separating the two frequency scales using actual marginal-ray sagittal/tangential F numbers gives off-axis0.121862626; changing to primary wavelength gives0.217957400 with the paraxial scale. These hypotheses do not close off-axis acceptance. Original native axes and values remain unchanged. Native511/512 diagnostics passed their execution/lifecycle checks;510 retained a harness assertion failure caused by requiring an analysis-only close flag on a batch-ray parent. See CV-01/progress509-pupil.json and progress512-pupil-controls.json. The shared reference helper is checked against direct complex pair summation on a rectangular pupil (ordinary514:21passed/2native skipped).


2026-11-07 执行531/536：表观瞳Fs/Ft仿射缩放的离轴最佳误差0.111733815；进一步使用已保存真实光线的出射方向作角坐标，线性三角插值OPD及sqrt(intensity)，再以方向余弦间距/波长作为频率步长。像面角坐标256/512网格差0.0691353/0.0692007，主光线法向角坐标差0.1144350/0.1142439，均高于0.005。三角凸包边界、出口振幅输运及折叠映射仍有未覆盖条件。531的诊断执行和关闭通过，536无新原生会话；两者均未通过完整数值验收。未改生产坐标或数值。详见CV-01/progress536-pupil-mapping.json。

2026-11-07 执行601–610：固定主光线法平面投影后最佳离轴差.065179468；近轴中心方向Jacobian控制最佳.077659377。原生604确认波前与独立批量OPD的入瞳50613点、表观出瞳46939点均在原相位门槛内，最大差分别1.6795e-10、1.9823e-10waves；其复瞳自相关差小于4.01e-12。相位来源和已验证常规网格映射之间的差异已排除。

新增正式相干OTF结果探查605：以Real_Coherent+i Imaginary_Coherent形成复瞳，再独立计算自相关。与同条件MTF_Incoherent全512×512网格相比，轴上最大差6.6613e-16、离轴.0049501971，均在.005内。离轴相干支持域41361点，Y索引152–358、X128–382，与原生波前的表观瞳不同。606的中心椭圆支持约束下限104.4184大于上限103.3340，因此拒绝该椭圆模型；名义中点控制有148个支持点冲突，不能据此恢复内部瞳坐标。

608正式GetPupil取得出瞳直径10.2337278824mm、位置−50.9613388516mm；609将独立光线输运到轴向出瞳平面、主光线法平面和参考球后插值，自相关最佳离轴差.0699747161，仍超.005。尚需内部相干复瞳与独立光线的采样/坐标/幅度归属，跨出口一致性继续作为诊断证据。功能仍implemented，原生值、坐标和容差保持。

普通610定向25通过；原生604/605各1个诊断用例通过，合计九个分析正常关闭；608只读探查关闭会话，源曲面/solve、系统、MFE保持。603测试导入失败发生于收集阶段；607误用另一枚举的Uniform名称，失败后已断连，608按已存DLL枚举None修正。原失败记录保留。汇总CV-01/progress610-coherent-pupil.json。
