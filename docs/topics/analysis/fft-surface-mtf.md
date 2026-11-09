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



The next action is an independent pupil-autocorrelation reference and a confirmed native FFT Surface/PSF sampling and projection definition. The FFT label/7×5 pagination/PNG regression passed in native287-labels.xml. Huygens has separate accepted PSF/OTF and analytic mirror references; see `huygens-surface-mtf.md`.






新增正式相干OTF结果探查605：以Real_Coherent+i Imaginary_Coherent形成复瞳，再独立计算自相关。与同条件MTF_Incoherent全512×512网格相比，轴上最大差6.6613e-16、离轴.0049501971，均在.005内。离轴相干支持域41361点，Y索引152–358、X128–382，与原生波前的表观瞳不同。606的中心椭圆支持约束下限104.4184大于上限103.3340，因此拒绝该椭圆模型；名义中点控制有148个支持点冲突，不能据此恢复内部瞳坐标。

608正式GetPupil取得出瞳直径10.2337278824mm、位置−50.9613388516mm；609将独立光线输运到轴向出瞳平面、主光线法平面和参考球后插值，自相关最佳离轴差.0699747161，仍超.005。尚需内部相干复瞳与独立光线的采样/坐标/幅度归属，跨出口一致性继续作为诊断证据。功能仍implemented，原生值、坐标和容差保持。
