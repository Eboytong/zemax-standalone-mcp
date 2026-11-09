"""C2/C3 control probe: does the native cell adopt a SurfacePickup solve, and when?

C2 keeps the request identical and varies only the *readback moment* (immediately, after
UpdateStatus, after a ray trace, after save+reload), so "not adopted now" and "adopted
after an update" become distinguishable.  C3 runs only when C2 never adopted, varying the
binding instead (MakePickupFromCurrentColumn, MakeSolveFixed first, non-zero value first).

The probe is diagnostic: it records the native answer and never asserts a contract, never
retries past the configured budget, and keeps the original failure separate from cleanup.
"""
import sys
from pathlib import Path

_workspace = next(p for p in Path(__file__).resolve().parents if (p / "pyproject.toml").is_file())
sys.path[:0] = [str(_workspace), str(_workspace / "src")]

import json
import os
import time

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean

WAVELENGTH = .5875618
TASK_TIMEOUT_SECONDS = 180
PICKUP_SURFACE = 2  # surface carrying the target pickup cell
CELLS = [
    dict(name="chip_zone", values=(0.5, 0.2), label="ChipZone"),
    dict(name="mechanical_semi_diameter", values=(5.5, 5.2), label="MechanicalSemiDiameter"),
]
STEPS = ["immediate", "after_update_status", "after_ray_trace", "after_save_reload"]


class TaskFailure(RuntimeError):
    def __init__(self, state, task, result):
        super().__init__("原生任务未成功：" + str(state))
        self.state = state
        self.task = task
        self.result = result


def readback(backend, surface, name):
    """Three-way readback: cell.Solve, GetSolveData().Type, and the pickup payload."""
    row = backend._row(surface)
    cell = backend._cell(row, name)
    data = cell.GetSolveData()
    out = dict(surface=surface, cell=name, cell_solve=str(cell.Solve),
               solve_data_type=str(data.Type), solve_data_valid=bool(data.IsValid),
               is_active=bool(cell.IsActive), is_read_only=bool(cell.IsReadOnly),
               value=float(cell.Value))
    if str(data.Type) == "SurfacePickup":
        pickup = data._S_SurfacePickup
        out["pickup"] = dict(surface=int(pickup.Surface), column=str(pickup.Column),
                             scale=float(pickup.ScaleFactor) if pickup.SupportsScale else None,
                             offset=float(pickup.Offset) if pickup.SupportsOffset else None,
                             from_current_column=bool(pickup.IsPickupFromCurrentColumn))
    return out


def run(output):
    folder = Path(output).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ["ZEMAX_STATE_DIR"] = str(folder / "state")
    os.environ["ZEMAX_OUTPUT_DIR"] = str(folder)
    backend = Backend(Config(Config.from_env().install_dir, folder / "native"))
    record = dict(
        item_ids=["ED-02.SurfacePickup.ChipZone", "ED-02.SurfacePickup.MechanicalSemiDiameter"],
        probe="C2/C3 pickup adoption and readback timing",
        evidence_only=True,
        conclusion="not asserted; records adoption, first adopting step, and binding variant",
        acceptance_scope=dict(
            mode_adoption=True,
            value_linkage=False,
            full_save_reload=False,
            note=("C2 decides only whether the native cell adopts the SurfacePickup mode, and at "
                  "which readback moment.  Source-value perturbation linkage and the full "
                  "save/reload acceptance are separate checks and are NOT covered here: the "
                  "after_save_reload step re-reads the mode, it does not verify linkage.")),
        task_polling_seconds=TASK_TIMEOUT_SECONDS, cases=[], calls=[], closed=False)

    def save():
        (folder / "anchors.json").write_text(json.dumps(clean(record), ensure_ascii=False, indent=2),
                                             encoding="utf-8")

    def call(name, args=None):
        response = backend.dispatch(name, args or {})
        record["calls"].append(dict(tool=name, arguments=args, response=response))
        save()
        assert response["ok"], response
        return response["data"]

    def finish(task, timeout_seconds=TASK_TIMEOUT_SECONDS):
        deadline = time.monotonic() + timeout_seconds
        while task["state"] not in ("succeeded", "failed", "cancelled"):
            if time.monotonic() > deadline:
                raise TimeoutError("任务轮询超时，最后状态：" + str(task["state"]))
            time.sleep(.03)
            task = call("get_task_status", dict(task_id=task["task_id"]))
        result = call("get_task_result", dict(task_id=task["task_id"]))
        if task["state"] != "succeeded":
            raise TaskFailure(task["state"], task, result)
        return result

    def probe_cell(surface, name, column_name, bind):
        """Submit one SurfacePickup request and report what the native side did."""
        row = backend._row(surface)
        cell = backend._cell(row, name)
        step = dict(bind=bind,
                    supported=list(str(x) for x in cell.GetAvailableSolveTypes()),
                    is_solve_type_supported=bool(cell.IsSolveTypeSupported(
                        backend.native.enum(backend.native.api.Editors.SolveType, "SurfacePickup"))),
                    is_active=bool(cell.IsActive), is_read_only=bool(cell.IsReadOnly))
        try:
            if bind == "make_solve_fixed_first":
                cell.MakeSolveFixed()
            solve = cell.CreateSolveType(backend.native.api.Editors.SolveType.SurfacePickup)
            pickup = solve._S_SurfacePickup
            pickup.Surface = 1
            if bind == "make_pickup_from_current_column":
                pickup.Column = backend.native.enum(backend.native.api.Editors.LDE.SurfaceColumn, column_name)
                pickup.MakePickupFromCurrentColumn()
            else:
                pickup.Column = backend.native.enum(backend.native.api.Editors.LDE.SurfaceColumn, column_name)
            if pickup.SupportsScale:
                pickup.ScaleFactor = 1.0
            if pickup.SupportsOffset:
                pickup.Offset = 0.0
            step["solve_valid"] = bool(solve.IsValid)
            step["supports_scale"] = bool(pickup.SupportsScale)
            step["supports_offset"] = bool(pickup.SupportsOffset)
            step["column_requested"] = str(pickup.Column)
            step["set_status"] = str(cell.SetSolveData(solve))
        except BaseException as exc:
            step["submit_error"] = dict(type=type(exc).__name__, message=str(exc))
            return step
        return step

    def observe(surface, name, step, label):
        reading = readback(backend, surface, name)
        adopted = (reading["cell_solve"] == "SurfacePickup"
                   and reading["solve_data_type"] == "SurfacePickup")
        step[label] = dict(adopted=adopted, **reading)
        return adopted

    try:
        call("connect")
        call("new_system")
        call("insert_surfaces", dict(at=1))
        call("update_system_settings", dict(
            aperture_value=10, primary_wavelength=1,
            wavelengths=[dict(wavelength_um=WAVELENGTH)],
            fields=[dict(x=0, y=0)]))
        call("update_surfaces", dict(changes=[dict(
            surface=1, radius=50, thickness=50, material="N-BK7",
            semi_diameter=8, is_stop=True, replace_solves=True)]))
        # The pickup cell lives on surface 2.  `insert_surfaces` changed the layout, so the
        # image surface is read from the model instead of assumed from the new_system default.
        layout = call("get_surfaces", dict(start=0, count=1))
        total = int(layout["total"])
        image = total - 1
        record["surface_layout"] = dict(
            total=total, image_surface=image, pickup_surface=PICKUP_SURFACE,
            target_surface=image, target_reaches_pickup=image >= PICKUP_SURFACE,
            basis=("image surface = get_surfaces.total - 1; the ray must pass the pickup cell "
                   "on surface 2, so a target below it would never evaluate that cell"))
        if image < PICKUP_SURFACE:
            raise RuntimeError("追迹目标面未覆盖拾取单元格所在的 surface 2。")
        for spec in CELLS:
            name, (source_value, target_value) = spec["name"], spec["values"]
            case = dict(cell=name, label=spec["label"], values=dict(source=source_value, target=target_value),
                        steps=[], variants=[], first_adoption_step=None, adopted=False,
                        linkage_checked=False,
                        save_reload_scope="mode readback only; value linkage after source perturbation is not verified")
            call("update_surfaces", dict(changes=[
                dict(surface=1, **{name: source_value}, replace_solves=True),
                dict(surface=2, **{name: target_value}, replace_solves=True)]))
            case["before"] = dict(source=readback(backend, 1, name), target=readback(backend, 2, name))

            step = probe_cell(2, name, spec["label"], "explicit_column")
            adopted_at = []
            for label in STEPS:
                if label == "after_update_status":
                    case["update_status_text"] = str(backend.system.UpdateStatus())
                elif label == "after_ray_trace":
                    case["ray_trace"] = dict(target_surface=image, start_surface=0,
                                             reaches_pickup=image >= PICKUP_SURFACE)
                    finish(call("run_batch_ray_trace", dict(
                        input_mode="Normalized", start_surface=0, target_surface=image,
                        rays=[dict(hx=0, hy=0, px=0, py=0, wavelength=1)])))
                elif label == "after_save_reload":
                    saved = folder / "reload.zos"
                    call("save_lens_as", dict(path=str(saved)))
                    call("open_lens", dict(path=str(saved)))
                if observe(2, name, step, label):
                    adopted_at.append(label)
            step["adopted_at"] = adopted_at
            case["steps"].append(step)
            case["first_adoption_step"] = adopted_at[0] if adopted_at else None
            case["adopted"] = bool(adopted_at)

            if not case["adopted"]:
                for bind in ("make_pickup_from_current_column", "make_solve_fixed_first"):
                    call("update_surfaces", dict(changes=[
                        dict(surface=1, **{name: source_value}, replace_solves=True),
                        dict(surface=2, **{name: target_value}, replace_solves=True)]))
                    variant = probe_cell(2, name, spec["label"], bind)
                    variant_at = []
                    for label in ("immediate", "after_update_status"):
                        if label == "after_update_status":
                            case["update_status_text"] = str(backend.system.UpdateStatus())
                        if observe(2, name, variant, label):
                            variant_at.append(label)
                    variant["adopted_at"] = variant_at
                    case["variants"].append(variant)
            record["cases"].append(case)
            save()
        call("disconnect")
        record["closed"] = True
    except BaseException as exc:
        entry = dict(type=type(exc).__name__, message=str(exc))
        if isinstance(exc, TaskFailure):
            entry.update(task_state=exc.state, task=exc.task, task_result=exc.result)
        record["error"] = entry
        try:
            save()
        except BaseException as write_error:
            print("无法写入 anchors.json：" + str(write_error), file=sys.stderr)
        raise
    finally:
        try:
            backend.shutdown()
        except BaseException as exc:
            record["cleanup_error"] = dict(type=type(exc).__name__, message=str(exc))
        record["active_task_after_shutdown"] = bool(getattr(backend, "active", None))
        receipt = Path(os.environ["ZEMAX_STATE_DIR"]) / "close_receipt.json"
        record["close_receipt"] = dict(path=str(receipt), exists=receipt.is_file(), content=None, error=None)
        try:
            if receipt.is_file():
                record["close_receipt"]["content"] = json.loads(receipt.read_text(encoding="utf-8"))
        except BaseException as exc:
            record["close_receipt"]["error"] = type(exc).__name__ + ": " + str(exc)
        try:
            save()
        except BaseException as write_error:
            print("无法写入 anchors.json：" + str(write_error), file=sys.stderr)
    print(json.dumps(dict(
        cases=[dict(cell=c["cell"], adopted=c["adopted"], first_adoption_step=c["first_adoption_step"],
                    variants=[dict(bind=v["bind"], set_status=v.get("set_status"),
                                   adopted_at=v["adopted_at"]) for v in c["variants"]])
               for c in record["cases"]],
        closed=record["closed"], cleanup_error=record.get("cleanup_error"),
        error=record.get("error")), ensure_ascii=False))
    return record


if __name__ == "__main__":
    run(sys.argv[1])
