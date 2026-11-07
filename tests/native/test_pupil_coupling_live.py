"""Independent rectangular-pupil and tilted Gaussian overlap references."""
import asyncio
import json
import math

import pytest

from tests.support.native import execute
from zemax_mcp.evaluation import interpolate


def write_reference(e, reference):
    (e.folder / "reference.json").write_text(
        json.dumps(reference, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@pytest.mark.zemax
def test_rectangular_pupil_mtf_native():
    async def work(e):
        wavelength_mm, focal_length_mm = 0.00055, 100
        write_reference(e, dict(
            model="On-axis paraboloidal mirror, uniform rectangular pupil",
            wavelength_mm=wavelength_mm, focal_length_mm=focal_length_mm,
            formula="MTF_axis(f) = max(0, 1 - f * wavelength_mm * focal_length_mm / full_width_axis_mm)",
            axis_definition="Tangential: Y; sagittal: X at the on-axis field",
            absolute_tolerance=0.02,
            scope="Scalar paraxial reference; finite numerical pupil/image sampling",
        ))
        for half_x, half_y in ((4, 3), (3, 4)):
            await e.model()
            await e.call("update_surfaces", dict(changes=[
                dict(surface=1, aperture=dict(
                    type="RectangularAperture", x_half_width=half_x, y_half_width=half_y
                )),
                dict(surface=2, radius=-200, conic=-1, material="MIRROR",
                     thickness=-100, semi_diameter=5, is_stop=True, replace_solves=True),
            ]))
            await e.call("save_lens_as", dict(path=str(e.folder / f"rectangle_{half_x}_{half_y}.zos")))
            # Read actual aperture settings before using them as the numerical reference.
            surfaces = await e.call("get_surfaces", dict(start=1, count=2))
            aperture = surfaces["surfaces"][0]["properties"]["aperture"]
            assert aperture["type"] == "RectangularAperture"
            e.check("actual rectangular X half-width mm", aperture["x_half_width"], half_x)
            e.check("actual rectangular Y half-width mm", aperture["y_half_width"], half_y)
            assert surfaces["surfaces"][1]["is_stop"]
            (e.folder / f"settings_{half_x}_{half_y}.json").write_text(
                json.dumps(surfaces, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            for sampling in ("S_256x256", "S_512x512"):
                result = await e.finish(await e.call("run_analysis", dict(request=dict(
                    kind="huygens_mtf", field=1, wavelength=1, sampling=sampling,
                    image_sampling="S_512x512", maximum_frequency=50, use_polarization=False
                ))))
                assert result["series"]
                for series in result["series"]:
                    # Explicit native labels define the axis; never sort columns by observed values.
                    for column, label in enumerate(series["labels"]):
                        if label in ("子午", "Tangential"):
                            width = 2 * half_y
                        elif label in ("弧矢", "Sagittal"):
                            width = 2 * half_x
                        else:
                            pytest.fail(f"Unrecognized native MTF axis label: {label!r}")
                        for frequency in (10, 25, 50):
                            actual = interpolate(series["x"], [v[column] for v in series["y"]], frequency)
                            expected = max(0, 1 - frequency * wavelength_mm * focal_length_mm / width)
                            e.check(
                                f"rectangle {half_x}x{half_y} half-width mm {sampling} {label} {frequency} cycles/mm",
                                actual, expected, atol=0.02
                            )
    asyncio.run(execute("rectangular_pupil", work))


@pytest.mark.zemax
def test_tilted_gaussian_coupling_native():
    async def work(e):
        await e.model()
        await e.call("save_lens_as", dict(path=str(e.folder / "same_plane.zos")))
        wavelength_mm = 0.00055
        write_reference(e, dict(
            model="Same-plane Gaussian waist fields with receiver angular mismatch",
            wavelength_mm=wavelength_mm,
            amplitude_definition="E = exp(-x^2/wx^2 - y^2/wy^2); w is 1/e amplitude radius",
            formula="eta = product[2*a*b/(a^2+b^2) * exp(-q^2*a^2*b^2/(2*(a^2+b^2)))]",
            angular_phase="qx = k*sin(tilt_about_y), qy = k*sin(tilt_about_x); k = 2*pi/lambda",
            absolute_tolerance=0.0005,
            scope="Small-angle scalar overlap at coincident waist planes, no lateral offset or propagation",
            angles_degrees=[0, 0.02, -0.02],
        ))
        for beam, fiber in (((0.1, 0.1), (0.1, 0.1)), ((0.1, 0.06), (0.08, 0.09))):
            for sampling, window in (("S_256x256", 2), ("S_512x512", 2), ("S_512x512", 4)):
                observed = {}
                for tx, ty in ((0, 0), (0.02, 0), (-0.02, 0), (0, 0.02), (0, -0.02), (0.02, 0.02)):
                    wavevectors = (
                        2 * math.pi / wavelength_mm * math.sin(math.radians(ty)),
                        2 * math.pi / wavelength_mm * math.sin(math.radians(tx)),
                    )
                    expected = math.prod(
                        2 * a * b / (a*a + b*b) * math.exp(-q*q*a*a*b*b / (2*(a*a + b*b)))
                        for a, b, q in zip(beam, fiber, wavevectors)
                    )
                    result = await e.finish(await e.call("run_pop", dict(request=dict(
                        end_surface=2, beam_parameters={0:beam[0], 1:beam[1]},
                        fiber_type="GaussianWaist", fiber_parameters={0:fiber[0], 1:fiber[1]},
                        fiber_tilt_x=tx, fiber_tilt_y=ty,
                        x_sampling=sampling, y_sampling=sampling, x_width=window, y_width=window,
                    ))))
                    actual_settings = result["task"]["settings"]
                    e.check("actual receiver tilt about X degrees", actual_settings["TiltAboutX"], tx)
                    e.check("actual receiver tilt about Y degrees", actual_settings["TiltAboutY"], ty)
                    assert actual_settings["XSampling"] == sampling
                    assert actual_settings["YSampling"] == sampling
                    assert actual_settings["UsePolarization"] is False
                    assert actual_settings["FiberPosition"] == "ChiefRay"
                    for parameters, radii in (
                        (actual_settings["beam_parameters"], beam),
                        (actual_settings["fiber_parameters"], fiber),
                    ):
                        by_index = {p["index"]:p["value"] for p in parameters}
                        for index, radius in enumerate(radii):
                            e.check("actual Gaussian waist radius mm", by_index[index], radius)
                        assert all(by_index[index] == 0 for index in range(2, 8))
                    metrics = result["metrics"]
                    observed[tx, ty] = metrics["receiver_efficiency"]
                    e.check(
                        f"tilt {tx},{ty} deg beam {beam} receiver {fiber} {sampling} window {window} mm",
                        metrics["receiver_efficiency"], expected, atol=5e-4
                    )
                    e.check("total coupling efficiency definition",
                            metrics["total_coupling_efficiency"],
                            metrics["system_efficiency"] * metrics["receiver_efficiency"])
                e.check("X tilt sign symmetry", observed[0.02, 0], observed[-0.02, 0], atol=5e-4)
                e.check("Y tilt sign symmetry", observed[0, 0.02], observed[0, -0.02], atol=5e-4)
                e.check("separable two-axis tilt",
                        observed[0.02, 0.02] * observed[0, 0],
                        observed[0.02, 0] * observed[0, 0.02], atol=5e-4)
    asyncio.run(execute("tilted_gaussian", work))

