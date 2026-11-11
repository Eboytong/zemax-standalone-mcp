"""Controlled GRIN profiles, partial patches, variable persistence and trace convergence."""
import json
import math
import time

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config, DEFAULT_INSTALL
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_gradient2_gradient3_profiles_and_convergence():
    output = run_dir("grin_specialized")
    backend = Backend(Config(DEFAULT_INSTALL, output))
    evidence = dict(calls=[], checks=[], output=str(output))

    def call(command, payload=None, *, error=None):
        response = backend.dispatch(command, payload or {})
        evidence["calls"].append(dict(command=command, payload=payload, response=response))
        if error:
            assert not response["ok"] and response["error"]["code"] == error, response
            return response
        assert response["ok"], response
        return response["data"]

    def finish(task):
        deadline = time.monotonic() + 60
        while task["state"] not in {"succeeded", "failed", "cancelled"}:
            if time.monotonic() >= deadline:
                call("cancel_task", dict(task_id=task["task_id"]))
                pytest.fail("GRIN task exceeded 60 seconds")
            time.sleep(.02)
            task = call("get_task_status", dict(task_id=task["task_id"]))
        assert task["state"] == "succeeded", task
        return backend._full_result(task["task_id"])

    try:
        call("connect")
        evidence.update(version=backend.version, build=backend.build_id)
        capabilities = call("get_capabilities")
        assert {"Gradient2", "Gradient3"} <= set(capabilities["implemented_surface_types"])
        for kind in ("Gradient2", "Gradient3"):
            call("new_system")
            call("insert_surfaces", dict(at=2, count=1))
            call("update_system_settings", dict(aperture_value=1,
                wavelengths=[dict(wavelength_um=.55), dict(wavelength_um=.635)]))
            coefficients = ([.02, 2.25, -.02, .001, -.0001, .00001, -.000001, .0000001]
                            if kind == "Gradient2" else [.02, 1.5, -.02, .001, -.0001, .003, -.0004, .00005])
            created = call("update_surfaces", dict(changes=[dict(surface=0, thickness=10),
                dict(surface=1, surface_type=kind, radius="Infinity", thickness=2,
                     semi_diameter=.5, parameters={str(i): v for i, v in enumerate(coefficients, 1)},
                     replace_solves=True), dict(surface=2, thickness=2, semi_diameter=.5, replace_solves=True)]))
            assert created["surfaces"][1]["surface_type"] == kind
            # Updating one coefficient must keep all omitted cells, including the step.
            coefficients[2] = -.025
            call("update_surfaces", dict(changes=[dict(surface=1, parameters={"3": coefficients[2]},
                                                       solves={"parameter_3": dict(mode="variable")})]))
            call("update_surfaces", dict(changes=[dict(surface=1, surface_type="Standard")]),
                 error="SOLVE_PROTECTED")
            path = output / f"{kind}.zos"
            call("save_lens_as", dict(path=str(path), overwrite=True))
            call("open_lens", dict(path=str(path)))
            row = call("get_surfaces", dict(start=1, count=1))["surfaces"][0]
            for i, value in enumerate(coefficients, 1):
                assert row["cells"][f"parameter_{i}"]["value"] == pytest.approx(value, abs=1e-15)
            assert row["cells"]["parameter_3"]["solve"]["type"] == "Variable"
            assert len(row["grin"]["parameters"]) == 8
            optimizer = backend.system.Tools.OpenLocalOptimization()
            try:
                assert int(optimizer.Variables) == 1
            finally:
                optimizer.Close()
            maximum_index_error = 0
            for wavelength in (1, 2):
                profile = finish(call("run_analysis", dict(request=dict(kind="grin_profile", surface=1,
                    wavelength=wavelength, show_index_vs="X", minimum_x=-.5, maximum_x=.5,
                    y_value=0, z_value=1))))
                assert profile["series"]
                for series in profile["series"]:
                    for x, values in zip(series["x"], series["y"]):
                        if kind == "Gradient2":
                            polynomial = coefficients[1] + sum(coefficients[i+1]*x**(2*i) for i in range(1, 7))
                            expected = math.sqrt(polynomial)
                        else:
                            expected = coefficients[1] + sum(coefficients[i+1]*x**(2*i) for i in range(1, 4)) + sum(coefficients[5:])
                        error = abs(values[0] - expected)
                        maximum_index_error = max(maximum_index_error, error)
                        assert error <= 1e-10 + 1e-9*abs(expected)
            traced = []
            for step in (.02, .01, .005):
                call("update_surfaces", dict(changes=[dict(surface=1, parameters={"1": step})]))
                result = finish(call("run_batch_ray_trace", dict(
                    rays=[dict(px=x) for x in (-.8, -.4, 0, .4, .8)], target_surface=3)))
                assert len(result["rows"]) == 5
                assert all(r["state"] == "succeeded" for r in result["rows"])
                traced.append(result["rows"])
            position_delta = max(abs(a-b) for left, right in zip(traced[-2], traced[-1])
                                 for a, b in zip(left["position"], right["position"]))
            direction_delta = max(abs(a-b) for left, right in zip(traced[-2], traced[-1])
                                  for a, b in zip(left["direction"], right["direction"]))
            assert position_delta <= 1e-5
            assert direction_delta <= 1e-7
            evidence["checks"].append(dict(surface_type=kind, actual=row,
                max_index_error=maximum_index_error, position_delta=position_delta,
                direction_delta=direction_delta, traces=traced))
    finally:
        try:
            call("disconnect")
            evidence["application_closed"] = backend.native.application is None
        finally:
            (output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")

