# Scatter Polar Plot Native Probe

OpticStudio 24.2.0 Build 240529, PremiumEdition, Python 3.14. Input was the installed `ABg scattering surface.zos` sample in NonSequential mode. `get_nsc_objects` confirmed object 2 is a Rectangle with face 0 set to ABg and resource `ABG-EXAMPLE`.

`ScatterPolarPlotSettings` returned valid `AS_Default` and `AR_Default`; the result contained one 181x90 native grid, no text export, no series, no messages, and no axis labels. The grid values were all `0.3183098861837907` (`1/pi`). On the owned working copy, object 2 face 0 was changed to Lambertian with ScatterFraction 1.0; readback succeeded. The analysis was run again and returned the identical grid dimensions, axis metadata, and constant values. Both analysis objects closed and the session disconnected.

The native grid has no axis semantics and did not respond to the model's ABg/Lambertian selection. It cannot serve as an identified scatter polar distribution. Raw evidence: `.local/evidence/development/NS-03/scatter-polar-20261108-control-02/summary.json`. Resume when a formal angle mapping and an output that reflects the selected scattering model are available.

Repeat on 2026-11-08 reconfirmed baseline grid `Nx=181`, `Ny=90`, `Dx=1.0112359550561798`, `Dy=1.988950276243094`, `MinX=MinY=0`, and min/max/center value `0.3183098861837907`. The adopted Lambertian control read back on object 2 face 0 with `ScatterFraction=1.0`; its grid remained identical. The native text export remained false; both analysis tools, control tool, and session closed. Repeat record: `.local/evidence/development/NS-03/scatter-polar-repeat-20261108/summary.json`.
