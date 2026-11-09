"""ED-02.MaterialModel.Material A/B/C single-variable matrix (runtime-executed once).

Direct ILDE.GetIndex is used only inside this probe; no public tool surface is added.
Each setting records the active wavelength table, the solve readback, Snell indices at two
incidence angles, the direct index readback, both documented/classic line conventions and
the unchanged original gates.  The reference is the requested Nd/Vd itself: no native curve
is fitted and re-compared, so no self-referential pass is possible.

Layer contract: the MCP tool surface nests the batch-ray body under ``request``
(``server.py`` run_batch_ray_trace(request: BatchRays)); ``Backend.dispatch`` validates the
body itself against the same ``BatchRays`` model (``backend.py`` dispatch ->
``COMMAND_MODELS[command].model_validate(arguments)``).  ``snell_request`` therefore builds
one body that both layers share, and this probe passes it unwrapped.
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
from tests.support.material_reference import (CLASSIC_LINES, PHYSICAL_LINES,
    abbe_from_wavelengths, line_positions, snell_indices_from_rows, snell_request)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from solve_contract import (SOLVE_PARAM_KEYS, close_receipt_verdict, session_closed,
                            solve_actual, solve_readback_checks)  # noqa: E402

WAVELENGTHS = [.5875618, .5876, .4861327, .4861, .6562725, .6563]
BASELINE_MODEL = dict(mode="material_model", index_nd=1.6, abbe_vd=60, dpgf=.001,
                      vary_index=True, vary_dpgf=True)
ND_ATOL, ND_RTOL = 1e-6, 1e-7
VD_ATOL, VD_RTOL = 1e-5, 1e-7
DIAG_ATOL, DIAG_RTOL = 1e-10, 1e-10
WRITE_BUDGET = 12
TASK_TIMEOUT_SECONDS = 180
PLAN = [
    dict(id="B0", kind="model", note="baseline Nd=1.6 Vd=60 dPgF=0.001", model=BASELINE_MODEL),
    dict(id="C1", kind="environment", note="only adjust_index_to_environment", changes=dict(adjust_index_to_environment=False)),
    dict(id="C2", kind="environment", note="only pressure_atm", changes=dict(pressure_atm=0)),
    dict(id="C3", kind="environment", note="only temperature_c", changes=dict(temperature_c=10)),
    dict(id="B1", kind="model", note="only index_nd", model=dict(BASELINE_MODEL, index_nd=1.5)),
    dict(id="B2", kind="model", note="only abbe_vd", model=dict(BASELINE_MODEL, abbe_vd=50)),
    dict(id="B3", kind="model", note="only dpgf", model=dict(BASELINE_MODEL, dpgf=0)),
    dict(id="B4", kind="model", note="only vary_abbe", model=dict(BASELINE_MODEL, vary_abbe=True)),
]


class TaskFailure(RuntimeError):
    """Native task ended without success; the original task/result payloads are kept."""

    def __init__(self, state, task, result):
        super().__init__("原生任务未成功：" + str(state))
        self.state = state
        self.task = task
        self.result = result


def gate(actual, expected, atol, rtol):
    return dict(actual=actual, expected=expected, atol=atol, rtol=rtol,
                error=actual - expected, passed=abs(actual - expected) <= atol + rtol * abs(expected))


def build_gates(direct, model, wavelengths=WAVELENGTHS):
    """Formal-convention gates: Nd uses the physical d line; classic d is diagnostic only.

    The formal definition uses physical d=0.5875618 (PHYSICAL_LINES). The four-decimal
    classic d is kept as a diagnostic; Vd is reported under both conventions. Nd/Vd
    tolerances are unchanged.
    """
    physical_d = line_positions(wavelengths, PHYSICAL_LINES)["d"]
    classic_d = line_positions(wavelengths, CLASSIC_LINES)["d"]
    main = dict(
        nd=gate(direct[physical_d], model["index_nd"], ND_ATOL, ND_RTOL),
        vd_physical=gate(abbe_from_wavelengths(direct, wavelengths, PHYSICAL_LINES),
                         model["abbe_vd"], VD_ATOL, VD_RTOL))
    diagnostic = dict(
        nd_classic=gate(direct[classic_d], model["index_nd"], ND_ATOL, ND_RTOL),
        vd_classic=gate(abbe_from_wavelengths(direct, wavelengths, CLASSIC_LINES),
                        model["abbe_vd"], VD_ATOL, VD_RTOL))
    return main, diagnostic, dict(nd=dict(physical=physical_d, classic=classic_d))


def run(output):
    folder = Path(output).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    os.environ["ZEMAX_STATE_DIR"] = str(folder / "state")
    os.environ["ZEMAX_OUTPUT_DIR"] = str(folder)
    backend = Backend(Config(Config.from_env().install_dir, folder / "native"))
    record = dict(
        item="ED-02.MaterialModel.Material",
        probe="D002.MODEL_GLASS A/B/C single-variable matrix",
        outlet="direct ILDE.GetIndex inside this probe only; no public tool added",
        reference=dict(source="requested Nd/Vd input values, unchanged",
                       self_fit_used=False,
                       lines=dict(physical=PHYSICAL_LINES, classic=CLASSIC_LINES),
                       gates=dict(nd=dict(atol=ND_ATOL, rtol=ND_RTOL),
                                  vd=dict(atol=VD_ATOL, rtol=VD_RTOL)),
                       diagnostics=dict(snell_vs_direct=dict(atol=DIAG_ATOL, rtol=DIAG_RTOL),
                                        angle_agreement=dict(atol=DIAG_ATOL, rtol=DIAG_RTOL))),
        wavelengths_requested=WAVELENGTHS, write_budget=WRITE_BUDGET, task_timeout_seconds=TASK_TIMEOUT_SECONDS,
        solve_parameter_keys=list(SOLVE_PARAM_KEYS),
        writes=[], cases=[], calls=[], closed=False, disconnect_returned=False)

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

    def read_state():
        settings = call("get_system_settings")
        surface = call("get_surfaces", dict(start=1, count=1))["surfaces"][0]
        from System import Array, Double
        indices = Array[Double]([0.] * len(WAVELENGTHS))
        returned = int(backend.system.LDE.GetIndex(1, len(WAVELENGTHS), indices))
        return settings, surface, [float(x) for x in indices], returned

    def snell():
        trace = finish(call("run_batch_ray_trace", snell_request(WAVELENGTHS)))
        indices, angles = snell_indices_from_rows(trace["rows"], len(WAVELENGTHS))
        return indices, angles

    def case(setting):
        settings, surface, direct, returned = read_state()
        snell_values, angles = snell()
        active = settings["wavelengths"]
        entry = dict(id=setting["id"], kind=setting["kind"], note=setting["note"],
                     request=setting.get("model") or setting.get("changes"),
                     environment=dict(temperature_c=settings["temperature_c"],
                                      pressure_atm=settings["pressure_atm"],
                                      adjust_index_to_environment=settings["adjust_index_to_environment"]),
                     native_wavelength_count=int(backend.system.SystemData.Wavelengths.NumberOfWavelengths),
                     active_wavelength_count=len(active),
                     active_wavelengths=[w["wavelength_um"] for w in active],
                     get_index_return=returned, get_index=direct,
                     snell=snell_values, snell_angles=angles,
                     snell_minus_direct=[a - b for a, b in zip(snell_values, direct)],
                     snell_vs_direct=[gate(s, d, DIAG_ATOL, DIAG_RTOL) for s, d in zip(snell_values, direct)],
                     angle_agreement=[gate(a, s, DIAG_ATOL, DIAG_RTOL)
                                      for angle in angles for a, s in zip(angle["indices"], snell_values)],
                     solve_readback=surface["cells"]["material"]["solve"],
                     solve_actual=solve_actual(surface),
                     material_value=surface["cells"]["material"]["value"],
                     vd_classic=abbe_from_wavelengths(direct, WAVELENGTHS, CLASSIC_LINES),
                     vd_physical=abbe_from_wavelengths(direct, WAVELENGTHS, PHYSICAL_LINES),
                     snell_vd_classic=abbe_from_wavelengths(snell_values, WAVELENGTHS, CLASSIC_LINES))
        entry["diagnostics_passed"] = all(
            item["passed"] for item in entry["snell_vs_direct"] + entry["angle_agreement"])
        model = setting.get("model")
        if model:
            main, diagnostic, positions = build_gates(direct, model)
            entry["gates"] = main
            entry["gates_diagnostic"] = diagnostic
            entry["nd_position"] = positions["nd"]
            entry["gate_passed"] = all(item["passed"] for item in main.values())
            entry["solve_readback_checks"] = solve_readback_checks(model, entry["solve_actual"])
            entry["solve_readback_passed"] = all(
                item["match"] for item in entry["solve_readback_checks"].values())
        return entry

    def change(changes):
        record["writes"].append(dict(kind="environment", changes=changes))
        call("update_system_settings", changes)
        actual = call("get_system_settings")
        for key, value in changes.items():
            assert actual[key] == value, (key, actual[key], value)
        return actual

    def restore(baseline, key):
        record["writes"].append(dict(kind="restore", changes={key: baseline[key]}))
        call("update_system_settings", {key: baseline[key]})
        actual = call("get_system_settings")
        assert actual[key] == baseline[key], (key, actual[key], baseline[key])

    try:
        call("connect")
        call("new_system")
        call("insert_surfaces", dict(at=1))
        call("update_system_settings", dict(
            aperture_value=10, primary_wavelength=2, adjust_index_to_environment=True,
            temperature_c=20, pressure_atm=1,
            wavelengths=[dict(wavelength_um=w) for w in WAVELENGTHS]))
        call("update_surfaces", dict(changes=[dict(surface=0, thickness=1),
            dict(surface=1, radius="Infinity", thickness=1, material="N-BK7", replace_solves=True)]))
        baseline = call("get_system_settings")
        record["baseline_environment"] = dict(temperature_c=baseline["temperature_c"],
                                              pressure_atm=baseline["pressure_atm"],
                                              adjust_index_to_environment=baseline["adjust_index_to_environment"])
        for setting in PLAN:
            if setting["kind"] == "model":
                record["writes"].append(dict(kind="model", request=setting["model"]))
                call("update_surfaces", dict(changes=[dict(surface=1, replace_solves=True,
                                                           solves={"material": setting["model"]})]))
                record["cases"].append(case(setting))
                saved_case = record["cases"][-1]
                saved_path = folder / (setting["id"] + ".zos")
                call("save_lens_as", dict(path=str(saved_path)))
                call("open_lens", dict(path=str(saved_path)))
                reloaded_settings, reloaded_surface, reloaded_indices, _ = read_state()
                persisted = dict(
                    path=str(saved_path),
                    solve=solve_readback_checks(setting["model"], solve_actual(reloaded_surface)),
                    indices=[gate(a, b, DIAG_ATOL, DIAG_RTOL)
                             for a, b in zip(reloaded_indices, saved_case["get_index"])],
                    wavelengths=[w["wavelength_um"] for w in reloaded_settings["wavelengths"]])
                persisted["passed"] = (all(v["match"] for v in persisted["solve"].values())
                                       and all(v["passed"] for v in persisted["indices"])
                                       and persisted["wavelengths"] == WAVELENGTHS)
                saved_case["save_reload"] = persisted
                save()
            else:
                try:
                    change(setting["changes"])
                    record["cases"].append(case(setting))
                except AssertionError as exc:
                    failure = exc.args[0] if exc.args else None
                    if not isinstance(failure, dict) or failure.get("error", {}).get("code") != "SETTING_REJECTED":
                        raise
                    record["cases"].append(dict(id=setting["id"], kind=setting["kind"],
                        request=setting["changes"], outcome="setting_rejected", original_failure=failure))
                finally:
                    for key in setting["changes"]:
                        restore(baseline, key)
                    record["environment_restores"] = record.get("environment_restores", []) + [
                        dict(id=setting["id"], settings=call("get_system_settings"))]
                    save()
        assert len(record["writes"]) <= WRITE_BUDGET, record["writes"]
        graded = [case_ for case_ in record["cases"] if "gates" in case_]
        record["acceptance"] = dict(
            rule="original gates unchanged: Nd 1e-6+1e-7*|ref|, Vd 1e-5+1e-7*|ref|",
            formal_convention="physical",
            per_case={case_["id"]: dict(
                nd=case_["gates"]["nd"]["passed"],
                vd_physical=case_["gates"]["vd_physical"]["passed"],
                nd_classic_diagnostic=case_["gates_diagnostic"]["nd_classic"]["passed"],
                vd_classic_diagnostic=case_["gates_diagnostic"]["vd_classic"]["passed"])
                for case_ in graded},
            diagnostics_passed=all(case_.get("diagnostics_passed", False) for case_ in record["cases"]),
            acceptance_passed=(all(case_["gate_passed"] for case_ in graded)
                               and all(case_.get("solve_readback_passed", False) for case_ in graded)
                               and all(case_.get("diagnostics_passed", False) for case_ in record["cases"])),
            solve_readback_passed=all(case_.get("solve_readback_passed", False) for case_ in graded),
            save_reload_passed=all(case_.get("save_reload", {}).get("passed", False) for case_ in graded),
            gaps=["full failure-recovery checkpoint/model comparison remains open; environment values restored here",
                  "dPgF has no numeric reference (write-readback only)",
                  "environment cases are self-consistency cross-checks; no independent environment reference",
                  "正式帮助给出精确 d/F/C 定义与近似精度，完整色散重建公式未公开；Vd偏差待定位"],
            complete=False,
            complete_reason="full failure-recovery restore, dPgF numeric reference and "
                            "independent environment reference remain open; Nd/Vd not passing under the formal "
                            "physical convention (Vd deviation cause not located; full dispersion formula not published in the inspected help)")
        save()
        call("disconnect")
        record["disconnect_returned"] = True
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
            record["close_receipt"]["verdict"] = close_receipt_verdict(record["close_receipt"]["content"])
        except BaseException as exc:
            record["close_receipt"]["verdict"] = dict(passed=False, reason=type(exc).__name__ + ": " + str(exc))
        # ``closed`` is only established after shutdown from these three facts, never from the
        # ``disconnect`` return value.
        record["closed_verdict"] = session_closed(record["close_receipt"]["verdict"],
                                                  record["active_task_after_shutdown"],
                                                  record.get("cleanup_error"))
        record["closed"] = record["closed_verdict"]["closed"]
        try:
            save()
        except BaseException as write_error:
            print("无法写入 anchors.json：" + str(write_error), file=sys.stderr)
    print(json.dumps(dict(cases=len(record["cases"]), writes=len(record["writes"]),
                          disconnect_returned=record["disconnect_returned"], closed=record["closed"],
                          closed_verdict=record.get("closed_verdict"),
                          acceptance_passed=record.get("acceptance", {}).get("acceptance_passed"),
                          diagnostics_passed=record.get("acceptance", {}).get("diagnostics_passed"),
                          solve_readback_passed=record.get("acceptance", {}).get("solve_readback_passed"),
                          close_receipt_passed=(record.get("close_receipt") or {}).get("verdict", {}).get("passed"),
                          cleanup_error=record.get("cleanup_error"), error=record.get("error"))))
    return record


if __name__ == "__main__":
    run(sys.argv[1])
