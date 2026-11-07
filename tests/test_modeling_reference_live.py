"""Analytic coordinates and native surface-copy relationships."""
import json
import math
import time

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from support.paths import run_dir


@pytest.mark.zemax
def test_modeling_geometry_and_copy_reference():
    output = run_dir("modeling_reference")
    backend = Backend(Config(Config.from_env().install_dir, output))
    events = []

    def call(command, args=None, ok=True):
        result = backend.dispatch(command, args or {})
        events.append(dict(tool=command, arguments=args, response=result))
        assert result["ok"] == ok, result
        return result["data"] if ok else result

    def prepare():
        call("new_system")
        call("insert_surfaces", dict(at=1, count=3))
        assert backend.system.SystemData.Aperture.GCRS.SetSelectedSurface(1)
        call("update_system_settings", dict(aperture_value=4, fields=[dict(x=0, y=0)],
                                            wavelengths=[dict(wavelength_um=.55)]))
        call("update_surfaces", dict(changes=[dict(surface=i, comment="S"+str(i),
             radius="Infinity", thickness=10, semi_diameter=10, replace_solves=True)
             for i in range(1, 5)]))

    try:
        call("connect")
        prepare()
        before = backend.revision
        invalid = call("update_surfaces", dict(changes=[
            dict(surface=1, aperture=dict(pickup_from=2)),
            dict(surface=2, aperture=dict(pickup_from=1))]), ok=False)
        assert invalid["error"]["code"] == "INVALID_SOLVE" and backend.revision == before
        assert all(not backend._row(i).ApertureData.IsPickedUp for i in (1, 2))
        call("update_surfaces", dict(changes=[dict(surface=1, aperture=dict(pickup_from=2))]))
        call("update_surfaces", dict(changes=[dict(surface=2, aperture=dict(pickup_from=1)),
            dict(surface=1, aperture=dict(type="None", replace_pickup=True))]))
        assert backend._row(2).ApertureData.PickupFrom == 1
        assert not backend._row(1).ApertureData.IsPickedUp
        call("update_surfaces", dict(changes=[dict(surface=2, aperture=dict(type="None", replace_pickup=True))]))
        call("update_surfaces", dict(changes=[dict(surface=3, tilt_decenter=dict(
            before_order="Decenter_Tilt", before_decenter_x=2, before_tilt_y=5))]))
        transform = call("get_surface_geometry", dict(surface=3))["global_transform"]
        c, s = math.cos(math.radians(5)), math.sin(math.radians(5))
        expected = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
        for actual, reference in zip(transform["rotation"], expected):
            assert actual == pytest.approx(reference, rel=1e-7, abs=1e-8), transform
        assert transform["translation"] == pytest.approx([2, 0, 20], rel=1e-7, abs=1e-8), transform
        rays = [dict(px=x, py=y) for x, y in ((0, 0), (.3, .1), (-.2, -.3))]
        task = call("run_batch_ray_trace", dict(rays=rays, target_surface=3))
        deadline = time.monotonic() + 60
        while backend.active:
            assert time.monotonic() < deadline
            backend.tick()
            time.sleep(.01)
        data = call("get_task_result", dict(task_id=task["task_id"]))
        assert data["task"]["state"] == "succeeded", data
        for row, ray in zip(data["rows"], rays):
            assert row["state"] == "succeeded", row
            local = row["position"]
            global_position = [sum(transform["rotation"][i][j]*local[j] for j in range(3))
                               + transform["translation"][i] for i in range(3)]
            x, y = 2*ray["px"], 2*ray["py"]
            assert global_position == pytest.approx(
                [x, y, 20-math.tan(math.radians(5))*(x-2)], rel=1e-7, abs=1e-8)
            direction = [sum(transform["rotation"][i][j]*row["direction"][j]
                             for j in range(3)) for i in range(3)]
            assert direction == pytest.approx([0, 0, 1], rel=1e-7, abs=1e-8)

        mappings = []
        for start, count, at in ((1, 2, 1), (1, 2, 2), (1, 2, 3), (1, 2, 5),
                                 (3, 1, 1), (3, 1, 3), (3, 1, 5), (1, 3, 5)):
            prepare()
            call("update_surfaces", dict(changes=[dict(surface=2, is_stop=True),
                dict(surface=1, radius=50, solves=dict(radius=dict(mode="variable"))),
                dict(surface=3, solves=dict(radius=dict(mode="surface_pickup", source_surface=1,
                                                        scale=2)))]))
            original = [backend._row(i).Comment for i in range(6)]
            copied = call("copy_surfaces", dict(start=start, count=count, at=at))
            rows = call("get_surfaces", dict(start=0, count=20))["surfaces"]
            assert [r["comment"] for r in rows] == original[:at]+original[start:start+count]+original[at:]
            assert [r["surface"] for r in rows if r["is_stop"]] == [2+(count if at <= 2 else 0)]
            source = 1+(count if at <= 1 else 0)
            dependent = 3+(count if at <= 3 else 0)
            assert rows[source]["cells"]["radius"]["solve"]["type"] == "Variable"
            solve = rows[dependent]["cells"]["radius"]["solve"]
            assert solve["type"] == "SurfacePickup" and solve["source_surface"] == source, (start, count, at, solve)
            # Radius pickup scales curvature; it does not support an offset.
            assert rows[dependent]["cells"]["radius"]["value"] == pytest.approx(25, rel=1e-7, abs=1e-8)
            for offset in range(count):
                donor, clone = start+offset, rows[at+offset]
                if donor == 1:
                    assert clone["cells"]["radius"]["solve"]["type"] == "Variable"
                if donor == 3:
                    clone_solve = clone["cells"]["radius"]["solve"]
                    if at == 1:
                        # A copied backward pickup becomes a forward reference;
                        # this native paste fixes the copied value instead.
                        assert clone_solve["type"] == "Fixed"
                    else:
                        assert clone_solve["type"] == "SurfacePickup"
                        reference = rows[clone_solve["source_surface"]]
                        assert reference["comment"] == "S1"
                        assert clone["cells"]["radius"]["value"] == pytest.approx(
                            reference["cells"]["radius"]["value"]/2, rel=1e-7, abs=1e-8)
            mappings.append(dict(start=start, count=count, at=at, stop=copied["stop_surface"],
                original_source=source, original_dependent=dependent,
                pickups=[dict(surface=r["surface"], solve=r["cells"]["radius"]["solve"])
                         for r in rows if r["cells"]["radius"]["solve"]["type"] == "SurfacePickup"]))
        (output/"copy-mappings.json").write_text(json.dumps(mappings, indent=2), encoding="utf-8")
    finally:
        backend.shutdown()
        (output/"calls.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Reference evidence:", output, flush=True)
