"""Run the installed official UDOC sample through a temporary MFE row."""
import json
import math
import shutil
import subprocess
import threading
import time
from pathlib import Path
import pytest
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_official_udoc_host_execution():
    from zemax_mcp.config import Config
    from zemax_mcp.native import NativeSession

    folder = run_dir("official_udoc_host")
    operand_dir = Path.home() / "Documents/Zemax/ZOS-API/Operands"
    program_number = next(
        number for number in range(99, 0, -1)
        if not (operand_dir / f"UDOC{number:02d}.exe").exists()
    )
    source = Path(__file__).parents[1] / "fixtures/user_operand/NativeSagOperand.cs"
    compiler = Path("C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe")
    install = Config.from_env().install_dir
    fixture = folder / f"UDOC{program_number:02d}.exe"
    command = [
        str(compiler), "/nologo", "/target:exe", "/platform:x64", f"/out:{fixture.resolve()}",
        f"/reference:{install / 'ZOSAPI_Interfaces.dll'}", f"/reference:{install / 'ZOSAPI.dll'}",
        f"/reference:{install / 'ZOSAPI_NetHelper.dll'}", str(source),
    ]
    build = subprocess.run(command, capture_output=True, text=True, timeout=25,
                           creationflags=subprocess.CREATE_NO_WINDOW)
    if build.returncode:
        raise RuntimeError({"command": command, "stdout": build.stdout, "stderr": build.stderr})
    shutil.copy2(install / "ZOSAPI_NetHelper.dll", folder / "ZOSAPI_NetHelper.dll")
    target = operand_dir / fixture.name
    shutil.copy2(fixture, target)
    session = NativeSession()
    record = {"analysis_session_closed": False, "program_number": program_number,
              "fixture_build_returncode": build.returncode, "fixture_path": str(target)}
    monitor_stop = threading.Event()
    processes_seen = {}
    watcher = None
    try:
        app = session.connect(Config.from_env().install_dir)
        record["version"] = str(app.OpticStudioVersion)
        record["mode"] = str(app.Mode)
        system = app.PrimarySystem
        sample = Path.home() / "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"
        record["sample_loaded"] = bool(system.LoadFile(str(sample), False))
        executable = target
        record["fixture_exists"] = executable.is_file()
        record["net_helper_copied"] = (folder / "ZOSAPI_NetHelper.dll").is_file()
        mfe = system.MFE
        record["baseline_operand_count"] = int(mfe.NumberOfOperands)
        while mfe.NumberOfOperands > 0:
            before = int(mfe.NumberOfOperands)
            mfe.RemoveOperandAt(before)
            after = int(mfe.NumberOfOperands)
            if after == before and after == 1 and str(mfe.GetOperandAt(1).Type) == "BLNK":
                break
        row = mfe.GetOperandAt(1) if mfe.NumberOfOperands == 1 and str(mfe.GetOperandAt(1).Type) == "BLNK" else mfe.AddOperand()
        change_result = row.ChangeType(session.api.Editors.MFE.MeritOperandType.UDOC)
        record["change_type_return"] = str(change_result)
        record["row_type"] = str(row.Type)
        x, y = 0.1, 0.2
        requested = {2: program_number, 3: 0, 4: 1, 5: 0, 6: x, 7: y, 8: 60000.0}
        for column, value in requested.items():
            cell = row.GetCellAt(column)
            if str(cell.DataType) == "Integer":
                cell.IntegerValue = int(value)
            else:
                cell.DoubleValue = float(value)
        record["settings_readback"] = {
            str(row.GetCellAt(column).Header): (
                int(row.GetCellAt(column).IntegerValue)
                if str(row.GetCellAt(column).DataType) == "Integer"
                else float(row.GetCellAt(column).DoubleValue)
            )
            for column in requested
        }
        surface = system.LDE.GetSurfaceAt(1)
        radius = float(surface.Radius)
        conic = float(surface.Conic)
        curvature = 0.0 if math.isinf(radius) else 1.0 / radius
        radial2 = x * x + y * y
        radicand = 1.0 - (1.0 + conic) * curvature * curvature * radial2
        if radicand < 0 or not math.isfinite(radicand):
            raise AssertionError({"radius": radius, "conic": conic, "radicand": radicand})
        expected_sag = curvature * radial2 / (1.0 + math.sqrt(radicand))
        record["independent_reference"] = {
            "method": "conic sag equation",
            "surface": 1,
            "radius": radius,
            "conic": conic,
            "x": x,
            "y": y,
            "expected_sag": expected_sag,
            "unit": "lens units",
        }
        from System.Diagnostics import Process

        def watch_operand_process():
            while not monitor_stop.is_set():
                try:
                    for process in Process.GetProcessesByName(f"UDOC{program_number:02d}"):
                        process_id = int(process.Id)
                        if process_id not in processes_seen:
                            try:
                                image_path = str(process.MainModule.FileName)
                            except Exception as exc:
                                image_path = str(exc)
                            processes_seen[process_id] = {"handle": process, "path": image_path}
                except Exception:
                    pass
                time.sleep(0.01)

        watcher = threading.Thread(target=watch_operand_process, daemon=True)
        watcher.start()
        merit_value = float(mfe.CalculateMeritFunction())
        monitor_stop.set()
        watcher.join(timeout=2)
        watcher = None
        record["udoc_process_ids_observed"] = sorted(processes_seen)
        record["udoc_process_exits"] = []
        for process_id, info in processes_seen.items():
            process = info["handle"]
            try:
                record["udoc_process_exits"].append({
                    "pid": process_id,
                    "path": info["path"],
                    "has_exited": bool(process.HasExited),
                    "exit_code": int(process.ExitCode) if process.HasExited else None,
                })
            except Exception as exc:
                record["udoc_process_exits"].append({"pid": process_id, "error": str(exc)})
        record["udoc_processes_remaining"] = len(Process.GetProcessesByName(f"UDOC{program_number:02d}"))
        trace_path = Path.home() / "AppData/Local/Temp" / f"UDOC{program_number:02d}.trace"
        record["fixture_trace"] = trace_path.read_text(encoding="utf-8") if trace_path.exists() else None
        error_path = Path.home() / "AppData/Local/Temp" / f"UDOC{program_number:02d}.error.txt"
        record["fixture_error"] = error_path.read_text(encoding="utf-8") if error_path.exists() else None
        record["merit_value"] = merit_value
        record["operand_value"] = float(row.Value)
        record["operand_contribution"] = float(row.Contribution)
        record["finite_result"] = (
            abs(record["merit_value"]) < float("inf")
            and abs(record["operand_value"]) < float("inf")
        )
        record["reference_error"] = abs(record["operand_value"] - expected_sag)
        record["reference_tolerance"] = 1e-10 + 1e-7 * abs(expected_sag)
        record["reference_passed"] = record["reference_error"] <= record["reference_tolerance"]
        record["acceptance_state"] = "accepted" if record["reference_passed"] else "result_mismatch"
        record["expected_merit"] = expected_sag * expected_sag
        record["merit_error"] = abs(merit_value - record["expected_merit"])
    except Exception as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        monitor_stop.set()
        if watcher is not None:
            watcher.join(timeout=2)
        record["udoc_process_ids_observed"] = sorted(processes_seen)
        try:
            session.disconnect()
            record["analysis_session_closed"] = True
        except Exception as exc:
            record["close_error"] = {"type": type(exc).__name__, "message": str(exc)}
        target.unlink(missing_ok=True)
        (Path.home() / "AppData/Local/Temp" / f"UDOC{program_number:02d}.trace").unlink(missing_ok=True)
        (Path.home() / "AppData/Local/Temp" / f"UDOC{program_number:02d}.error.txt").unlink(missing_ok=True)
        record["fixture_removed"] = not target.exists()
        (folder / "execution.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if "close_error" in record:
            raise AssertionError(record)
    assert record.get("row_type") == "UDOC", record
    assert record.get("analysis_session_closed"), record
