"""Offline audit of the saved native Hologram1 diff-efficiency evidence.

Reads only files under the main project's .local/runs (read-only) and recomputes the
independent Kogelnik reference for every saved 2D node. No native execution, no
product-code import beyond tests/support/kogelnik.py, no writes outside .local/.

Usage (cwd = worktree root):
    python -B .local/coordination/audit_evidence.py
"""
import importlib.util
import json
import math
from pathlib import Path

RUN = Path(r"C:\Users\tonge\Desktop\Zemax_MCP\.local\runs\runs\diff_efficiency_offaxis059_native_bdfaeee137")
OUT = Path(".local/coordination/evidence-audit.json")
KOGELNIK = Path("tests/support/kogelnik.py")
ATOL = 1e-6
RTOL = 1e-5
BRAGG = math.degrees(math.atan(0.5))


def load_kogelnik():
    spec = importlib.util.spec_from_file_location("kogelnik_reference", KOGELNIK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.unslanted_transmission


unslanted = load_kogelnik()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def close_enough(actual, expected, atol=ATOL, rtol=RTOL):
    return abs(actual - expected) <= atol + rtol * abs(expected)


calls = read_json(RUN / "calls.json")
checks = read_json(RUN / "checks.json")
reference_status = read_json(RUN / "reference_status.json")
close_receipt = read_json(RUN / "state" / "close_receipt.json")
cancellation = read_json(RUN / "cancellation.json")
session = next(p for p in RUN.iterdir() if p.is_dir() and (p / "_task_index").is_dir())

tasks = {}
for path in session.glob("*.json"):
    if path.stem.startswith("image_request"):
        continue
    data = read_json(path)
    if isinstance(data, dict) and "task" in data:
        tasks[path.stem] = data

# ---------------------------------------------------------------- request/readback
MAPPING = {
    "min_angle": "MinAngle",
    "max_angle": "MaxAngle",
    "min_wavelength": "MinWavelength",
    "max_wavelength": "MaxWavelength",
    "sample_size": "SampleSize",
}


def polarization_of(task):
    pol = (task.get("system_settings") or {}).get("polarization") or {}
    jx, jy = pol.get("jx"), pol.get("jy")
    if jx == 1 and jy == 0:
        return "S"
    if jx == 0 and jy == 1:
        return "P"
    return f"jx={jx},jy={jy}"


def find_scan(kind, pol):
    candidates = []
    for task_id, data in tasks.items():
        task = data["task"]
        settings = task.get("settings") or {}
        requested = settings.get("requested") or {}
        if requested.get("kind") != kind:
            continue
        if polarization_of(data) != pol:
            continue
        if kind == "diff_efficiency_2d":
            if requested.get("sample_size") != "S_64x64" or not data.get("grids"):
                continue
        else:
            series = data.get("series") or []
            if not series or len(series[0]["x"]) != 64:
                continue
        candidates.append((task.get("created_at", ""), task_id))
    if not candidates:
        return None, None
    _, task_id = sorted(candidates)[0]
    return task_id, tasks[task_id]


def kogelnik_checks(prefix):
    rows = [c for c in checks if c["label"].startswith(prefix + " ")]
    passed = [c for c in rows if c["passed"]]
    errors = [abs(c["actual"] - c["expected"]) for c in passed]
    worst = max(rows, key=lambda c: abs(c["actual"] - c["expected"])) if rows else None
    return dict(
        count=len(rows),
        passed=len(passed),
        failed=len(rows) - len(passed),
        max_absolute_error=max(errors) if errors else None,
        worst_label=worst["label"] if worst else None,
        atol=rows[0]["atol"] if rows else None,
        rtol=rows[0]["rtol"] if rows else None,
    )


def page_calls(task_id):
    return [c for c in calls if c["tool"] == "get_task_result" and (c["arguments"] or {}).get("task_id") == task_id]


# Closing facts come from calls.json only: the per-task result file never stores
# close_attempted, so the last get_task_status response for that task id is the source.
last_status = {}
for index, call in enumerate(calls):
    if call["tool"] != "get_task_status":
        continue
    data = call["response"]["data"] or {}
    task_id = data.get("task_id")
    if task_id:
        last_status[task_id] = dict(
            call_index=index,
            state=data.get("state"),
            close_attempted=data.get("close_attempted"),
            active=data.get("active"),
            error=data.get("error"),
        )


def close_of(task_id):
    """close_attempted/state for one task plus the calls.json index that states them."""
    status = last_status.get(task_id)
    if status is None:
        return dict(source=dict(file="calls.json", tool="get_task_status", task_id=task_id,
                                status_seen=False),
                    close_attempted="not_observed", state="not_observed")
    return dict(
        source=dict(file="calls.json", call_index=status["call_index"], tool="get_task_status",
                    task_id=task_id, status_seen=True),
        close_attempted=status["close_attempted"] if status["close_attempted"] is not None else "not_observed",
        state=status["state"],
    )


items = {}
for kind in ("diff_efficiency_angular", "diff_efficiency_chromatic", "diff_efficiency_2d"):
    items[kind] = {}
    for pol in ("S", "P"):
        task_id, data = find_scan(kind, pol)
        if task_id is None:
            items[kind][pol] = dict(found=False)
            continue
        task = data["task"]
        settings = task.get("settings") or {}
        requested = settings.get("requested") or {}
        native = settings.get("native") or {}
        readback = {}
        for key, native_name in MAPPING.items():
            if key in requested and requested[key] is not None:
                readback[native_name] = dict(
                    requested=requested[key],
                    actual=native.get(native_name),
                    matches=native.get(native_name) == requested[key],
                )
        paging = []
        for call in page_calls(task_id):
            args = call["arguments"]
            paged = call["response"]["data"]
            entry = dict(arguments={k: v for k, v in args.items() if k != "task_id"})
            if "grid" in paged and args.get("width"):
                page = paged["grid"]
                full = data["grids"][0]
                ys = range(args["y_start"], args["y_start"] + len(page["values"]))
                xs = range(args["x_start"], args["x_start"] + len(page["values"][0]))
                expected = [[full["values"][y][x] for x in xs] for y in ys]
                entry.update(
                    shape=dict(rows=len(page["values"]), cols=len(page["values"][0])),
                    values_match_full_grid=page["values"] == expected,
                    max_absolute_difference=max(
                        (abs(page["values"][i][j] - expected[i][j]) for i in range(len(expected)) for j in range(len(expected[0]))),
                        default=0.0,
                    ),
                    axes=dict(x_start=page["x_start"], y_start=page["y_start"], next_x=page.get("next_x"), next_y=page.get("next_y")),
                )
            elif "series" in paged and args.get("start") is not None:
                page = paged["series"][0]
                full = data["series"][0]
                start = args["start"]
                count = args["count"]
                expected_x = full["x"][start:start + count]
                expected_y = [row[0] for row in full["y"][start:start + count]]
                entry.update(
                    points=len(page["x"]),
                    x_match=page["x"] == expected_x,
                    values_match_full_series=[row[0] for row in page["y"]] == expected_y,
                    max_absolute_difference=max(
                        (abs(row[0] - e) for row, e in zip(page["y"], expected_y)), default=0.0
                    ),
                )
            paging.append(entry)
        images = [
            dict(path=str(c["arguments"]["request"]["path"]),
                 name=Path(c["arguments"]["request"]["path"]).name,
                 exists=Path(c["arguments"]["request"]["path"]).exists())
            for c in calls
            if c["tool"] == "export_analysis_image" and c["arguments"]["request"]["task_id"] == task_id
        ]
        entry = dict(
            found=True,
            task_id=task_id,
            result_state=task.get("state"),
            close=close_of(task_id),
            requested={k: v for k, v in requested.items() if v is not None},
            readback=readback,
            native_readback_key_count=len(native),
            native_readback=native,
            evaluation_conditions=settings.get("evaluation_conditions"),
            kogelnik=kogelnik_checks(pol + " " + kind),
            paging=paging,
            images=images,
        )
        if data.get("grids"):
            grid = data["grids"][0]
            entry["grid"] = {
                key: grid[key]
                for key in ("nx", "ny", "dx", "dy", "min_x", "min_y", "x_label", "y_label", "value_label",
                            "x_unit", "y_unit", "value_unit", "array_order", "invalid_count")
            }
            entry["grid"]["last_column_angle"] = grid["min_x"] + (grid["nx"] - 1) * grid["dx"]
            entry["grid"]["last_row_wavelength"] = grid["min_y"] + (grid["ny"] - 1) * grid["dy"]
        if data.get("series"):
            series = data["series"][0]
            entry["series"] = dict(
                description=series.get("description"),
                x_count=len(series["x"]),
                x_first=series["x"][0],
                x_last=series["x"][-1],
                x_unit=series.get("x_unit"),
                y_unit=series.get("y_unit"),
                value_quantity=series.get("value_quantity"),
                labels=series.get("labels"),
                labels_source=series.get("labels_source"),
                invalid_count=series.get("invalid_count"),
            )
        items[kind][pol] = entry

# ------------------------------------------------------------- central slice checks
slices = {}
for pol in ("S", "P"):
    grid_task = items["diff_efficiency_2d"].get(pol, {})
    ang = items["diff_efficiency_angular"].get(pol, {})
    chrom = items["diff_efficiency_chromatic"].get(pol, {})
    if not (grid_task.get("found") and ang.get("found") and chrom.get("found")):
        slices[pol] = dict(available=False)
        continue
    grid = tasks[grid_task["task_id"]]["grids"][0]
    grid_values = grid["values"]
    angular_series = tasks[ang["task_id"]]["series"][0]
    chrom_series = tasks[chrom["task_id"]]["series"][0]
    center_x = len(grid_values[0]) // 2
    center_y = len(grid_values) // 2
    row_at_center_wave = [grid_values[center_y][x] for x in range(len(grid_values[0]))]
    column_at_center_angle = [grid_values[y][center_x] for y in range(len(grid_values))]
    angular_values = [row[0] for row in angular_series["y"]]
    chrom_values = [row[0] for row in chrom_series["y"]]
    angle_axis = [grid["min_x"] + x * grid["dx"] for x in range(grid["nx"])]
    wave_axis = [grid["min_y"] + y * grid["dy"] for y in range(grid["ny"])]
    slices[pol] = dict(
        available=True,
        grid_task=grid_task["task_id"],
        center_x=center_x,
        center_y=center_y,
        center_angle=angle_axis[center_x],
        center_wavelength=wave_axis[center_y],
        angle_axis_matches_angular_scan=max(abs(a - b) for a, b in zip(angle_axis, angular_series["x"])),
        wavelength_axis_matches_chromatic_scan=max(abs(a - b) for a, b in zip(wave_axis, chrom_series["x"])),
        row_center_wave_vs_angular=dict(
            points=len(angular_values),
            max_absolute_difference=max(abs(a - b) for a, b in zip(row_at_center_wave, angular_values)),
            identical=row_at_center_wave == angular_values,
        ),
        column_center_angle_vs_chromatic=dict(
            points=len(chrom_values),
            max_absolute_difference=max(abs(a - b) for a, b in zip(column_at_center_angle, chrom_values)),
            identical=column_at_center_angle == chrom_values,
        ),
    )

# ------------------------------------------------------- full 2D grid offline check
full_grid = {}
for pol in ("S", "P"):
    entry = items["diff_efficiency_2d"].get(pol, {})
    if not entry.get("found"):
        full_grid[pol] = dict(available=False)
        continue
    grid = tasks[entry["task_id"]]["grids"][0]
    worst = None
    outside = 0
    total = 0
    errors = []
    sampled = []
    for y, row in enumerate(grid["values"]):
        wavelength = grid["min_y"] + y * grid["dy"]
        for x, value in enumerate(row):
            angle = grid["min_x"] + x * grid["dx"]
            expected = unslanted(angle, wavelength, pol)
            error = abs(value - expected)
            total += 1
            errors.append(error)
            if not close_enough(value, expected):
                outside += 1
            if worst is None or error > worst["absolute_error"]:
                worst = dict(absolute_error=error, angle=angle, wavelength=wavelength, actual=value, expected=expected)
            if x % 8 == 0 and y % 8 == 0:
                sampled.append((angle, wavelength, value, expected))
    sampled_errors = [abs(v - e) for _, _, v, e in sampled]
    errors.sort()
    full_grid[pol] = dict(
        available=True,
        nodes=total,
        nodes_outside_tolerance=outside,
        max_absolute_error=worst["absolute_error"],
        max_error_node=worst,
        median_absolute_error=errors[len(errors) // 2],
        p95_absolute_error=errors[int(len(errors) * 0.95)],
        recorded_sample_nodes=len(sampled),
        recorded_sample_max_absolute_error=max(sampled_errors),
        recorded_sample_outside_tolerance=sum(1 for _, _, v, e in sampled if not close_enough(v, e)),
        atol=ATOL,
        rtol=RTOL,
    )

# ------------------------------------------------------------------- Hologram1 model
surface_snapshots = []
for index, call in enumerate(calls):
    if call["tool"] != "get_surfaces":
        continue
    payload = call["response"]["data"]
    rows = payload.get("surfaces") or []
    surface = next((row for row in rows if row.get("surface") == 1), None)
    if surface is None:
        continue
    cells = surface.get("cells") or {}
    parameters = {name: cells[name]["value"] for name in cells if name.startswith("parameter_")}
    surface_snapshots.append(dict(
        call_index=index,
        units=payload.get("units"),
        surface_type=surface.get("surface_type"),
        thickness=cells.get("thickness", {}).get("value") if "thickness" in cells else None,
        thickness_header=cells.get("thickness", {}).get("header") if "thickness" in cells else None,
        material=cells.get("material", {}).get("value") if "material" in cells else None,
        parameter_headers={name: cells[name].get("header") for name in parameters},
        parameters=parameters,
        solve_types={name: cells[name]["solve"] for name in parameters},
    ))

# --------------------------------------- Hologram1 write read-back (parameters 1-21)
# get_surfaces exposes parameter_count=20 for this surface, so Par21 cannot come from a
# snapshot. The formal read-back of a written parameter is the update_surfaces response
# field response.data.updated_parameters[].cells[<n>] = {value, solve}.
write_readback = []
for index, call in enumerate(calls):
    if call["tool"] != "update_surfaces":
        continue
    response = call["response"]
    written = {}
    for change in (call["arguments"] or {}).get("changes") or []:
        if change.get("surface") != 1:
            continue
        for name, value in (change.get("parameters") or {}).items():
            written[name] = value
        for name in ("surface_type", "thickness"):
            if name in change:
                written[name] = change[name]
    returned = {}
    for entry in (response.get("data") or {}).get("updated_parameters") or []:
        if entry.get("surface") != 1:
            continue
        for name, cell in (entry.get("cells") or {}).items():
            returned[name] = dict(value=cell.get("value"), solve=cell.get("solve"))
    write_readback.append(dict(call_index=index, ok=response.get("ok"),
                               warnings=response.get("warnings"),
                               written=written, returned=returned))

parameter_21 = dict(requested=0, get_surfaces_exposed=False, sources=[])
for entry in write_readback:
    if "21" in entry["returned"]:
        parameter_21["sources"].append(dict(
            kind="api_readback",
            file="calls.json",
            call_index=entry["call_index"],
            ok=entry["ok"],
            warnings=entry["warnings"],
            json_path="response.data.updated_parameters[0].cells['21']",
            value=entry["returned"]["21"]["value"],
            solve=entry["returned"]["21"]["solve"],
        ))

# Saved lens corroboration: HOLOGRM1 stores Par13..Par21 as the nine XDAT words of SURF 1.
saved_lens = dict(path=str(RUN / "offaxis_saved.zos"), exists=(RUN / "offaxis_saved.zos").exists(),
                  surf1_xdat=[], surf1_parm={})
if saved_lens["exists"]:
    text = (RUN / "offaxis_saved.zos").read_bytes().decode("utf-16")
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "SURF 1"), None)
    if start is not None:
        for line in lines[start + 1:]:
            stripped = line.strip()
            if stripped.startswith("SURF ") and stripped != "SURF 1":
                break
            if stripped.startswith("XDAT "):
                parts = stripped.split()
                saved_lens["surf1_xdat"].append(dict(word=int(parts[1]), value=float(parts[2])))
            elif stripped.startswith("PARM "):
                parts = stripped.split()
                saved_lens["surf1_parm"][parts[1]] = float(parts[2])
if len(saved_lens["surf1_xdat"]) >= 9:
    parameter_21["sources"].append(dict(
        kind="saved_lens_text",
        file=saved_lens["path"],
        location="SURF 1, XDAT 9 (HOLOGRM1 extended data, Par13..Par21 -> XDAT 1..9)",
        value=saved_lens["surf1_xdat"][8]["value"],
        solve="Fixed",
        note="XDAT 1..9 equal the written Par13..Par21 values in order: 1, 0.01, 1, 1, 1.5, 0.02, 0, 0, 0.",
    ))


# ----------------------------------------------------------------------- lifecycle
# last_status/close_of are built above, before the per-item block, from calls.json.
outcomes = {}
for task_id, status in last_status.items():
    data = tasks.get(task_id, {})
    settings = (data.get("task", {}).get("settings") or {})
    requested = settings.get("requested") or {}
    outcomes.setdefault(status["state"] or "unknown", []).append(dict(
        task_id=task_id,
        kind=requested.get("kind"),
        sample_size=requested.get("sample_size"),
        call_index=status["call_index"],
        close_attempted=status["close_attempted"],
        has_result_payload=bool(data.get("series") or data.get("grids")),
        task_error=(data.get("task", {}).get("error") or {}).get("code"),
    ))

failed = []
for task_id, data in tasks.items():
    task = data["task"]
    if task.get("state") == "failed":
        failed.append(dict(task_id=task_id, error=task.get("error"), **close_of(task_id),
                           requested={k: v for k, v in (task.get("settings", {}).get("requested") or {}).items() if v is not None}))

cancel_calls = [dict(call_index=index, arguments=c["arguments"]) for index, c in enumerate(calls) if c["tool"] == "cancel_task"]
system_settings_calls = [c for c in calls if c["tool"] == "get_system_settings"]
settings_equal = None
if len(system_settings_calls) >= 2:
    first = system_settings_calls[0]["response"]["data"]
    last = system_settings_calls[-1]["response"]["data"]
    settings_equal = all(first.get(key) == last.get(key) for key in ("configuration", "fields", "wavelengths", "polarization"))

lifecycle = dict(
    close_source="last get_task_status response per task_id in calls.json",
    close_attempted_all=all(status["close_attempted"] is True for status in last_status.values()),
    close_attempted_by_task={task_id: dict(call_index=status["call_index"], state=status["state"],
                                           close_attempted=status["close_attempted"])
                             for task_id, status in last_status.items()},
    succeeded_all_have_payload=all(entry["has_result_payload"] for entry in outcomes.get("succeeded", [])),
    outcomes=outcomes,
    task_states={task_id: status["state"] for task_id, status in last_status.items()},
    failed_tasks=failed,
    cancel_calls=cancel_calls,
    cancellation_file=cancellation,
    close_receipt=close_receipt,
    disconnect_present=any(c["tool"] == "disconnect" for c in calls),
    system_settings_before_after_equal=settings_equal,
    save_lens_calls=[c["arguments"] for c in calls if c["tool"] == "save_lens_as"],
    open_lens_calls=[c["arguments"] for c in calls if c["tool"] == "open_lens"],
)

# --------------------------------------------------------------- missing fields
expected_task_fields = ["native_preamble", "native_messages", "native_header", "system_settings",
                        "structured_data_available", "units_source", "context"]
missing = {}
for task_id, data in tasks.items():
    absent = [name for name in expected_task_fields if name not in data]
    settings = (data["task"].get("settings") or {})
    if not settings.get("requested"):
        absent.append("task.settings.requested")
    if not settings.get("native"):
        absent.append("task.settings.native")
    if not settings.get("evaluation_conditions"):
        absent.append("task.settings.evaluation_conditions")
    if absent:
        missing[task_id] = dict(kind=(settings.get("requested") or {}).get("kind"),
                                state=data["task"].get("state"), absent=absent)

audit = dict(
    schema_version=1,
    scope="CO-01.DiffEfficiencyAngular/Chromatic/2D native Hologram1 (native-only declaration)",
    source_run=str(RUN),
    session=session.name,
    files=[str(RUN / name) for name in ("calls.json", "checks.json", "reference_status.json",
                                        "cancellation.json")]
    + [str(RUN / "state" / "close_receipt.json")],
    call_counts={tool: sum(1 for c in calls if c["tool"] == tool) for tool in sorted({c["tool"] for c in calls})},
    reference=dict(
        implementation=str(KOGELNIK), atol=ATOL, rtol=RTOL,
        function="unslanted_transmission(angle_deg, wavelength_um, polarization)",
    ),
    reference_status=reference_status,
    checks_total=len(checks),
    checks_passed=sum(1 for c in checks if c["passed"]),
    hologram1_surface=dict(
        snapshots=len(surface_snapshots),
        last=surface_snapshots[-1] if surface_snapshots else None,
        first=surface_snapshots[0] if surface_snapshots else None,
        all_equal=len({json.dumps(s["parameters"], sort_keys=True) for s in surface_snapshots}) == 1
        and len({s["surface_type"] for s in surface_snapshots}) == 1,
        get_surfaces_parameter_count=20,
        write_readback=write_readback,
        parameter_21=parameter_21,
        saved_lens=saved_lens,
    ),
    items=items,
    central_slices=slices,
    full_grid_reference=full_grid,
    lifecycle=lifecycle,
    missing_fields=missing,
    bragg_degrees=BRAGG,
)

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(audit, ensure_ascii=True, indent=1), encoding="utf-8")

# ASCII-only console summary
print("wrote", OUT, OUT.stat().st_size, "bytes")
print("tasks:", len(tasks), "checks:", len(checks), "passed:", audit["checks_passed"])
for kind, pols in items.items():
    for pol, entry in pols.items():
        if not entry.get("found"):
            print(kind, pol, "MISSING")
            continue
        ko = entry["kogelnik"]
        print(kind, pol, "checks", ko["count"], "failed", ko["failed"], "maxerr", ko["max_absolute_error"])
for pol, entry in slices.items():
    print("slice", pol, {k: v for k, v in entry.items() if k in
                         ("max_absolute_difference", "identical")} if not entry.get("available") else
          dict(row=entry["row_center_wave_vs_angular"]["max_absolute_difference"],
               col=entry["column_center_angle_vs_chromatic"]["max_absolute_difference"],
               axis_angle=entry["angle_axis_matches_angular_scan"],
               axis_wave=entry["wavelength_axis_matches_chromatic_scan"]))
for pol, entry in full_grid.items():
    if entry.get("available"):
        print("fullgrid", pol, "nodes", entry["nodes"], "outside", entry["nodes_outside_tolerance"],
              "maxerr", entry["max_absolute_error"], "p95", entry["p95_absolute_error"])
    else:
        print("fullgrid", pol, "MISSING")
print("lifecycle:", lifecycle["close_attempted_all"], lifecycle["disconnect_present"],
      lifecycle["system_settings_before_after_equal"], "failed", len(lifecycle["failed_tasks"]),
      "cancel", lifecycle["cancellation_file"])
for state, rows in sorted(lifecycle["outcomes"].items()):
    print(" outcome", state, "tasks", len(rows), "closed",
          sum(1 for row in rows if row["close_attempted"] is True),
          "payload", sum(1 for row in rows if row["has_result_payload"]))
print("surface all_equal:", audit["hologram1_surface"]["all_equal"], "snapshots:", audit["hologram1_surface"]["snapshots"])
print("missing-field tasks:", len(missing))
