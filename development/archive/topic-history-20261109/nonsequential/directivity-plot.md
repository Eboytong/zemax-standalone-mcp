# Directivity Plot

Use `run_analysis` with `{"kind":"directivity_plot"}` in an NSC system. The result retains the native text artifact and returns per-scan-angle `series` and paginated `rows`. Each curve uses degrees on X and native normalized candela on Y; output metadata includes the IES filename, peak intensity in candela, and total luminous flux in lumens.

On the OpticStudio 24.2.0 Colorimetry two-color sample, the native report returned `sample.ies`, 18 cd peak, 112.81 lm total flux, and 37 angular samples at a 0° scan angle. All 37 samples agree with the installed IES file within 5.1e-5. The sampled trapezoidal flux is 112.81009451201489 lm; continuous linear interpolation gives 113.09733552923255 lm. File and scan selection with adopted-value readback remain open. See [IES audit](../../../../development/evidence/NS-03/directivity-ies-audit-20261108.md).
