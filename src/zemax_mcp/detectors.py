"""Detector coordinates and checked native scalar settings for local 2024 R2."""
import math
from .errors import ZemaxError
from .analyses import native_setting


def checked_setting(native, obj, name, value):
    native_setting(native, obj, name, value)
    check_setting_readback(obj, name, value)


def check_setting_readback(obj, name, value):
    try:actual = getattr(obj, name)
    except Exception as exc:
        raise ZemaxError("SETTING_REJECTED","请求属性无法回读。",setting=name,requested=value,reason=str(exc)) from exc
    check_setting_value(name,value,actual)


def check_setting_value(name,value,actual):
    try:
        matches = str(actual) == value if isinstance(value, str) else (
            type(value) is bool and type(actual) is bool and actual == value
            or type(value) in (int, float) and not isinstance(actual, bool)
            and math.isfinite(float(actual)) and math.isclose(float(actual), value, rel_tol=1e-12, abs_tol=1e-12)
        )
    except (TypeError,ValueError,OverflowError):matches=False
    if not matches:
        raise ZemaxError("SETTING_REJECTED", "原生对象设置未采用请求值。",
                         setting=name, requested=value, actual=str(actual))


def polar_coordinates(np, na, maximum_angle):
    if np < 2 or na < 1 or not math.isfinite(maximum_angle) or not 1 <= maximum_angle <= 180:
        raise ZemaxError("INVALID_DETECTOR_DATA", "Polar 像素数量或角度范围无效。")
    step = maximum_angle / (np - 1)
    centers = [i * step for i in range(np)]
    bounds = [[max(0, c-step/2), min(maximum_angle, c+step/2)] for c in centers]
    az_step = 360 / na
    az = [i * az_step for i in range(na)]
    az_bounds = [[c-az_step/2, c+az_step/2] for c in az]
    solid = [math.radians(az_step) * (math.cos(math.radians(a))-math.cos(math.radians(b)))
             for a, b in bounds]
    return dict(
        coordinate_system="detector-local angular",
        x_axis=dict(name="polar", unit="degrees", centers=centers, bounds=bounds),
        y_axis=dict(name="azimuth", unit="degrees", centers=az, bounds=az_bounds,
                    periodic=True, period=360, bounds_interpretation="unwrapped about pixel center"),
        pixel_solid_angle_sr=solid,
        solid_angle_layout="per polar column; repeated for every azimuth row",
        definition="polar from local +Z; azimuth from local +X toward +Y",
        source="OpticStudio 2024 R2 section 2.3.2.4.3",
    )


def detector_metadata(kind, coherent_type, units, prefix, analysis_units, analysis_prefix,
                      detector_type="DetectorRectangle"):
    # Polar Power/PowerSolidAngle are radiometric even when sources are in lumens.
    # NSDP uses the source prefix and switches W to J in energy mode.
    power_unit = ("Joules" if units=="Joules" else "Watts") if detector_type=="DetectorPolar" else units
    quantity = dict(flux="power per pixel", irradiance="irradiance",
                    intensity="power per steradian", coherent="native coherent " + str(coherent_type))[kind]
    if kind == "flux" or kind == "coherent" and coherent_type == "Power":
        value_unit = power_unit
        value_prefix = prefix
    elif kind == "intensity":
        value_unit = power_unit + "/sr"
        value_prefix = prefix
    elif kind == "coherent":
        value_unit = "sqrt(" + units + ")"
        value_prefix = prefix
        quantity = {"Real":"normalized coherent field real component",
                    "Imaginary":"normalized coherent field imaginary component",
                    "Amplitude":"native coherent Amplitude display value; 1x1 behavior differs from unnormalized S_amp"}.get(coherent_type,quantity)
    else:
        value_unit = analysis_units
        if units == "Joules":
            value_unit = value_unit.replace("Watts","Joules").replace("Lumens","Talbots")
        value_prefix = analysis_prefix
    if units == "Joules":
        quantity = quantity.replace("power","energy").replace("irradiance","energy density")
    return dict(quantity=quantity, value_unit=value_unit, value_unit_prefix=value_prefix)


def detector_capabilities():
    return {
        "DetectorRectangle": dict(kinds=["flux", "irradiance", "intensity", "coherent"],
            mode="NonSequential", implemented=True,
            validation_status="native_numeric_reference",
            verified_scope=["direct source flux","equal-path coherent phase and normalization","controlled reflection/refraction","flux/coherent Power: Watts/Lumens/Joules, source prefixes None/Milli"],
            vector_interference_status="Polarization=0 intentionally uses scalar intensity/geometric phase; flags 1/2 select local Ex/Ey, separately verified for orthogonal axial inputs",
            coordinates="native spatial or angular matrix; coherent data uses detector normalization",
            coherent_types=["Real", "Imaginary", "Amplitude", "Power"],
            verification="See docs/nonsequential-validation.md for model-specific native evidence"),
        "DetectorPolar": dict(kinds=["flux", "intensity"],
            mode="NonSequential", implemented=True,
            validation_status="native_numeric_reference",
            verified_scope=["four angular quadrants","azimuth seam and polar limits","power and solid angle","radiometric Power under lumen sources; energy in joules; prefixes None/Milli"],
            native_types=dict(flux="Power", intensity="PowerSolidAngle"),
            coordinates="rows azimuth, columns polar; local +Z polar axis, +X azimuth origin",
            verification="See docs/nonsequential-validation.md for model-specific native evidence"),
        "DetectorColor":dict(kinds=["flux","irradiance","intensity","spectral"],mode="NonSequential",implemented=True,
            validation_status="native_flux_and_file_roundtrip",coordinates="native x-fast pixels reshaped into rows Y and columns X",
            channels=["radiometric_flux","radiometric_density","photometric_flux","photometric_density","chromaticity_x","chromaticity_y","u_prime","v_prime","tristimulus_x","tristimulus_y","tristimulus_z"],
            spectral_scope="native spectral-bin centroid and RMS; no spectral power spectrum adapter",
            verification="1W, x-fast non-square pixels and spectral-bin centroid; official CIE1931 2deg XYZ/xy/u-prime/v-prime/lumens at 450/550/650nm, unequal three-line mixture and 360-830nm discrete/trapezoidal flat spectra; radiometric spectra remain separate"),
        "DetectorVolume":dict(kinds=["flux","absorbed_flux","absorbed_density"],mode="NonSequential",implemented=True,
            validation_status="native_incident_absorption_density_and_file_roundtrip",coordinates="values[z][y][x]; native x-fast voxel index",
            maximum_voxels=1000000,verification="N-BK7 catalog transmittance at 0.3um, bulk absorption and density per lens-unit^3; incident flux repeats over traversed voxels"),
        "DetectorSurface":dict(kinds=["flux","irradiance"],mode="NonSequential",implemented=True,
            validation_status="native_controlled_facet_hits",coordinates="native triangular pixel rows; FastRayTrace can reorder pixels",
            geometry=dict(option='include_geometry',frames=['local','global'],interface='INCERow.GetFacetedObjectData / IFaceData',
                pagination='start/count',face_index='zero based',pixel_index='one based; face and pixel radiometry cross-checked'),
            verification="plane/spherical/annular, signed tilt/decenter, FastRayTrace off/on; centroid hits, area and global vertices, save/reload"),
        "ReverseRadianceDetector":dict(kinds=[],mode="NonSequential",implemented=False,
            validation_status="removed_since_23_2",reason="官方23.2版本说明移除Reverse Radiance、REVR及相关Detector/Target；本机2024 R2不提供此能力。",
            evidence="outputs/specialized_routes_20261024/routes.json; reverse.txt"),
    }

