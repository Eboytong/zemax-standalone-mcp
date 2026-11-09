# Speos LensSystem receiver preflight, 2026-11-08

- Item: `EXT-SPEOS.Receiver.LensSystem`.
- Plan: verify the prior native export file still exists, inspect installed Ansys application registrations and executable paths for a Speos receiver, and attempt import only if a receiver is available.
- Export input: `.local/runs/runs/speos_cartesian_a54755af39/cartesian.OPTDistortion`, 54,523,861 bytes; original export evidence records OpticStudio 24.2.0 build 240529, Cartesian settings readback, successful export, source-state preservation and normal exporter/copy closure.
- Receiver inventory: the Ansys uninstall entries inspected list `Ansys Optics Launcher 2024 R2 for x64` version `24.2.0.3796`; no Speos receiver product entry was returned. Existing product-directory inventory and earlier v242 uninstall review also found no runnable Speos receiver.
- Import, geometry/unit checks, and receiver resource closure were not executable because no Speos receiver is installed. No source model or exported input was modified.
- Conclusion: `blocked`. Unlock condition: install/provide a runnable Speos receiver and license compatible with the OpticStudio 2024 R2 export, then import the retained `.OPTDistortion` and verify sensor extent, coordinates, geometry and referenced resources.
- Existing export evidence: `development/evidence/EXT-SPEOS/lens-system-export-20261108.md`; retained input path above.
- Completion count: 0.
