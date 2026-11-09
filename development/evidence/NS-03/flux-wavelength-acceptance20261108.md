# Flux vs Wavelength Native Outlet Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Input was the installed Non-sequential Colorimetry sample `Example 1 Two-color mixing gives white.zos`, opened as a working copy in NonSequential mode. The model contains two system wavelengths, 0.46 and 0.57 µm.

The runtime object was `AS_Default`, exposing only `IAS_`; readback showed `IsValid=true` and `IsActiveWindow=true`. The valid `AR_Default` result had no messages, series, grids, RGB grids, or scatter points. `GetTextFile` returned true, but the output was only the two-byte UTF-16 BOM and contained no report rows. The analysis object closed and the session disconnected successfully.

Repeat evidence: `.local/evidence/development/NS-03/flux-wavelength-repeat-20261108/summary.json` records the post-open `NonSequential` mode and system wavelengths 0.46/0.57 µm. It reconfirms valid AS_Default/AR_Default, zero result counts, a two-byte BOM-only text file, analysis close, and session disconnect. Original evidence: `.local/evidence/development/NS-03/flux-wavelength-20261108/summary.json`.

The complete Flux-vs-Wavelength contract remains blocked until a formal applicability/input contract and a nonempty supported result outlet are available. The repeated run confirms the prior empty output was from the intended NSC sample and two-wavelength condition.
