"""Offline ordinary tests for the bounded N1/N2/N3 control probes.

Every probe runs through the real request models (RunAnalysis/SystemPatch) and the
real result contracts (parse_phase_aberration_text), with the native session or
tool dispatcher replaced by an offline fake.  No OpticStudio instance is created.
"""
import copy
import math
import sys
from pathlib import Path

import pytest

PROBES = Path(__file__).resolve().parents[2] / "scripts" / "probes" / "PO-01"
if str(PROBES) not in sys.path:
    sys.path.insert(0, str(PROBES))

import n1_settings_surface as n1  # noqa: E402
import n2_system_polarization as n2  # noqa: E402
import phase_aberration_reference as n3  # noqa: E402
import probe_common as pc  # noqa: E402
import json


def test_n1_non_enum_type_does_not_invoke_enum_reflection():
    class NativeType:
        FullName = 'Native.Settings'
        IsEnum = False

        def GetEnumNames(self):
            raise AssertionError('GetEnumNames requires an enum type')

    class Settings:
        def GetType(self):
            return NativeType()

    actual = n1.describe(Settings(), lambda value: value)
    assert actual['type'] == 'Native.Settings'
    assert actual['enums'] == {}


@pytest.mark.parametrize('tool,wrapper,body', [
    ('update_system_settings', 'settings', {'polarization': {'jx': 1, 'jy': 0}}),
    ('run_batch_ray_trace', 'request', {'rays': [{'hx': 0, 'hy': 0, 'px': 0, 'py': 0}]}),
])
def test_probe_adapter_maps_stdio_body_to_backend_contract(tool, wrapper, body):
    from zemax_mcp.models import COMMAND_MODELS

    class Backend:
        def dispatch(self, name, arguments):
            COMMAND_MODELS[name].model_validate(arguments)
            assert arguments == body
            return {'ok': True, 'data': {}}

    receipts = []
    pc.adapter(Backend(), receipts)(tool, {wrapper: body})
    assert receipts[0]['arguments'] == {wrapper: body}
    assert receipts[0]['backend_arguments'] == body


@pytest.mark.parametrize('session,closed,forced,confirmed', [
    ('current', True, False, True), ('old', True, False, False),
    ('current', False, False, False), ('current', True, True, False),
])
def test_native_close_receipt_requires_current_session_and_normal_close(tmp_path, monkeypatch, session, closed, forced, confirmed):
    monkeypatch.setenv('ZEMAX_STATE_DIR', str(tmp_path))
    (tmp_path / 'close_receipt.json').write_text(json.dumps(dict(
        session_id=session, forced=forced, native=dict(closed=closed, error=None))), encoding='utf-8')
    record = {}
    pc.record_disconnect(record, dict(connected=False, last_session=dict(session_id='current')), [])
    assert record['native_close_receipt']['confirmed'] is confirmed
from zemax_mcp.analysis_models import RunAnalysis  # noqa: E402
from zemax_mcp.errors import ZemaxError  # noqa: E402
from zemax_mcp.models import SystemPatch  # noqa: E402
from zemax_mcp.polarization_topics import parse_phase_aberration_text  # noqa: E402

# ---------------------------------------------------------------- guard rails


@pytest.mark.parametrize("module", [n1, n2, n3])
def test_probes_never_guess_cfg_keys_or_modify_settings(module):
    source = Path(module.__file__).read_text(encoding="utf-8")
    for forbidden in ("ModifySettings(", "PHA_", "PRT_", "TRA_", "FIB_"):
        assert forbidden not in source, forbidden


# ------------------------------------------------------------------------- N1


class _Item:
    def __init__(self, name):
        self.Name = name


class _Type:
    FullName = "ZemaxUI.PhaseAberrationSettings"
    IsEnum = False

    def GetProperties(self):
        return [_Item("IsValid"), _Item("IsActiveWindow")]

    def GetFields(self):
        return [_Item("Wavelength")]

    def GetMethods(self):
        return [_Item("SaveTo"), _Item("LoadFrom")]


class _Settings:
    """Fake settings object whose SaveTo return value is independently set.

    ``SaveToFailed`` is deliberately assigned *inside* SaveTo so a probe that read
    it before the call would see the stale value.
    """

    def __init__(self, save_ok=True, save_return="auto", save_flag=None, payload=None, encoding="utf-8"):
        self.SaveToFailed = not save_ok
        self._save_ok = save_ok
        self._save_return = save_ok if save_return == "auto" else save_return
        self._save_flag = save_flag
        self._payload = payload
        self._encoding = encoding

    def GetType(self):
        return _Type()

    def SaveTo(self, path):
        if self._save_ok:
            data = (self._payload if self._payload is not None
                    else "! saved by SaveTo\nX_CENTROID 1\n".encode(self._encoding))
            Path(path).write_bytes(data)
        self.SaveToFailed = bool(self._save_flag)
        return self._save_return


class _Analysis:
    def __init__(self, kind, settings):
        self.kind = kind
        self._settings = settings

    def GetSettings(self):
        return self._settings


class _Session:
    def __init__(self, fail=(), close_fail=(), save_ok=True, receipt_close=True, **settings):
        self.fail = set(fail)
        self.close_fail = set(close_fail)
        self.settings_kwargs = dict(save_ok=save_ok, **settings)
        self.receipt_close = receipt_close
        self.closed = []

    def new_analysis(self, kind):
        if kind in self.fail:
            raise RuntimeError("New_Analysis failed for " + kind)
        return _Analysis(kind, _Settings(**self.settings_kwargs))

    def unwrap(self, obj):
        return obj

    def close(self, analysis):
        if analysis.kind in self.close_fail:
            raise RuntimeError("close failed")
        self.closed.append(analysis.kind)
        return {"closed": True, "reply": True} if self.receipt_close else True


def test_n1_reflects_surface_and_reads_saved_cfg(tmp_path):
    record = n1.probe(tmp_path, _Session())
    assert [entry["kind"] for entry in record["analyses"]] == list(n1.KINDS)
    first = record["analyses"][0]
    assert first["settings"]["type"] == "ZemaxUI.PhaseAberrationSettings"
    assert first["settings"]["members"] == [
        {"group": "properties", "name": "IsValid"},
        {"group": "properties", "name": "IsActiveWindow"},
        {"group": "fields", "name": "Wavelength"},
        {"group": "methods", "name": "SaveTo"},
        {"group": "methods", "name": "LoadFrom"},
    ]
    assert first["cfg"]["saved"] is True
    assert "X_CENTROID" in first["cfg"]["text"]
    assert Path(first["cfg"]["path"]).is_file()
    assert "/" not in Path(first["cfg"]["path"]).name.replace("\\", "/")
    assert first["closed"] is True
    assert record["close_failures"] == []
    assert (tmp_path / "n1-settings-surface.json").is_file()


def test_n1_keeps_running_after_one_analysis_fails(tmp_path):
    record = n1.probe(tmp_path, _Session(fail={"Transmission"}))
    by_kind = {entry["kind"]: entry for entry in record["analyses"]}
    assert "error" in by_kind["Transmission"] and "settings" not in by_kind["Transmission"]
    assert by_kind["PhaseAberration"]["settings"]["type"].endswith("Settings")
    assert all(entry["closed"] for entry in record["analyses"] if "settings" in entry)


def test_n1_records_unsaved_cfg_without_crashing(tmp_path):
    record = n1.probe(tmp_path, _Session(save_ok=False))
    cfg = record["analyses"][0]["cfg"]
    assert cfg["saved"] is False
    assert cfg["file_created"] is False and cfg["byte_count"] == 0 and cfg["text"] is None
    assert cfg["return_type"] == "bool" and cfg["return_value"] is False


def test_n1_void_save_is_not_treated_as_failure(tmp_path):
    record = n1.probe(tmp_path, _Session(save_return=None))
    cfg = record["analyses"][0]["cfg"]
    assert cfg["return_type"] == "NoneType" and cfg["return_value"] is None
    assert cfg["saved"] is True
    assert cfg["decode_failures"] == [] and cfg["encoding"] == "utf-8"


def test_n1_save_failed_flag_read_after_save_wins(tmp_path):
    record = n1.probe(tmp_path, _Session(save_flag=True))
    cfg = record["analyses"][0]["cfg"]
    assert cfg["save_failed_flag"] is True
    assert cfg["file_created"] is True and cfg["byte_count"] > 0
    assert cfg["saved"] is False


def test_n1_undecodable_cfg_is_not_reported_as_valid_text(tmp_path):
    record = n1.probe(tmp_path, _Session(payload=b"\xff\xff\xff\x00\x81"))
    cfg = record["analyses"][0]["cfg"]
    assert cfg["decoded"] is False and cfg["text"] is None and cfg["encoding"] is None
    assert cfg["text_trusted"] is False
    assert cfg["saved"] is False
    assert cfg["byte_count"] == 5 and cfg["bytes_hex_prefix"] == "ffffff0081"
    assert cfg["decode_failures"]
    assert "sha256" not in cfg


def test_save_cfg_failure_keeps_stale_file_from_looking_successful(tmp_path):
    class _Raising:
        SaveToFailed = False

        def SaveTo(self, path):
            raise RuntimeError("SaveTo raised")

    target = tmp_path / "stale.cfg"
    target.write_text("! leftover from an earlier run\nX_CENTROID 1\n", encoding="utf-8")
    cfg = n1.save_cfg(_Raising(), target, lambda obj: obj)
    assert cfg["save_error"] == "RuntimeError('SaveTo raised')"
    assert cfg["written_by_this_call"] is False
    assert cfg["file_created"] is True and cfg["byte_count"] > 0  # the stale file is still reported
    assert cfg["saved"] is False


def test_each_probe_run_writes_its_own_cfg_names(tmp_path):
    first = n1.probe(tmp_path, _Session())
    second = n1.probe(tmp_path, _Session())
    first_paths = {Path(entry["cfg"]["path"]).name for entry in first["analyses"]}
    second_paths = {Path(entry["cfg"]["path"]).name for entry in second["analyses"]}
    assert first["run_stamp"] != second["run_stamp"]
    assert not (first_paths & second_paths)
    assert all(Path(entry["cfg"]["path"]).is_file() for entry in first["analyses"])


def test_n1_utf16_bom_cfg_is_decoded_and_confirmed(tmp_path):
    record = n1.probe(tmp_path, _Session(encoding="utf-16"))
    cfg = record["analyses"][0]["cfg"]
    assert cfg["encoding"] == "utf-16" and cfg["encoding_source"] == "bom"
    assert cfg["encoding_confirmed"] is True and cfg["text_trusted"] is True
    assert cfg["saved"] is True and "X_CENTROID" in cfg["text"]


def test_n1_legacy_codepage_decode_is_marked_assumed(tmp_path):
    record = n1.probe(tmp_path, _Session(payload="! 保存\nX_CENTROID 1\n".encode("cp936")))
    cfg = record["analyses"][0]["cfg"]
    assert cfg["decoded"] is True
    assert cfg["encoding"] == "cp936" and cfg["encoding_source"] == "assumed"
    assert cfg["encoding_confirmed"] is False
    assert cfg["saved"] is False  # an assumed code page is not a confirmed CFG


def test_n1_close_receipt_is_recorded(tmp_path):
    record = n1.probe(tmp_path, _Session())
    first = record["analyses"][0]
    assert first["closed"] is True
    assert first["close_receipt"] == {"closed": True, "reply": True}


def test_n1_close_failure_is_listed_separately(tmp_path):
    record = n1.probe(tmp_path, _Session(close_fail={"FiberCouplingSettings"}))
    by_kind = {entry["kind"]: entry for entry in record["analyses"]}
    assert by_kind["FiberCouplingSettings"]["closed"] is False
    assert record["close_failures"][0]["kind"] == "FiberCouplingSettings"


class _FakeBackend:
    """Minimal ``Backend.dispatch`` stand-in returning real receipts."""

    def __init__(self, connect_ok=True, open_ok=True, disconnect_ok_value=True):
        self.connect_ok = connect_ok
        self.open_ok = open_ok
        self.disconnect_ok_value = disconnect_ok_value
        self.calls = []

    def dispatch(self, tool, args):
        self.calls.append(tool)
        if tool == "connect":
            return {"ok": self.connect_ok, "data": {"connected": self.connect_ok}}
        if tool == "open_lens":
            return {"ok": self.open_ok, "data": {"path": args.get("path")}}
        if tool == "disconnect":
            reply = {"ok": True, "data": {"connected": not self.disconnect_ok_value}}
            return reply if self.disconnect_ok_value else {"ok": False, "error": {"code": "DISCONNECT_FAILED"}}
        raise AssertionError("unexpected tool " + tool)


def test_n1_cli_aborts_before_probe_when_connect_fails(tmp_path, monkeypatch):
    built = []
    monkeypatch.setattr(n1, "_real_session", lambda *a, **k: built.append(1) or _Session())
    backend = _FakeBackend(connect_ok=False)
    record = n1.run_cli(backend, tmp_path, "lens.zos")
    assert record["startup"] == {"connect_ok": False, "aborted": "connect_failed"}
    assert record["analyses"] == []
    assert built == []  # no session, so no empty-system read
    assert backend.calls == ["connect", "disconnect"]
    assert record["disconnect"]["ok"] is True


def test_n1_cli_aborts_when_open_lens_fails(tmp_path, monkeypatch):
    built = []
    monkeypatch.setattr(n1, "_real_session", lambda *a, **k: built.append(1) or _Session())
    backend = _FakeBackend(open_ok=False)
    record = n1.run_cli(backend, tmp_path, "lens.zos")
    assert record["startup"]["aborted"] == "open_lens_failed"
    assert record["analyses"] == [] and built == []
    assert backend.calls == ["connect", "open_lens", "disconnect"]
    assert record["disconnect_receipt"]["step"] == "disconnect"


def test_n1_cli_records_failed_disconnect_receipt(tmp_path, monkeypatch):
    monkeypatch.setattr(n1, "_real_session", lambda *a, **k: _Session())
    backend = _FakeBackend(disconnect_ok_value=False)
    record = n1.run_cli(backend, tmp_path, "lens.zos")
    assert [entry["kind"] for entry in record["analyses"]] == list(n1.KINDS)
    assert record["disconnect"]["ok"] is False
    assert record["disconnect"]["reply"]["error"]["code"] == "DISCONNECT_FAILED"
    assert (tmp_path / "n1-settings-surface.json").is_file()


# ------------------------------------------------------------------------- N2

BASELINE = {
    "polarization": {"unpolarized": False, "jx": 0.0, "jy": 1.0, "x_phase": 0.0, "y_phase": 0.0},
    "wavelengths": [{"number": 1, "wavelength_um": 0.55}],
    "field_type": "Angle",
}
FOLLOWED = {"jx": 1.0, "jy": 0.0, "x_phase_deg": 0.0, "y_phase_deg": 90.0}


class _FakeCall:
    def __init__(self, jones=None, task_state="succeeded", disconnect_fails=False,
                 ignore_restore=False, states=None):
        self.settings = copy.deepcopy(BASELINE)
        self.calls = []
        self.jones = jones or (lambda kind: dict(FOLLOWED))
        self.task_state = task_state
        self.disconnect_fails = disconnect_fails
        self.ignore_restore = ignore_restore
        self.updates = 0
        self.tasks = {}
        self.states = list(states or [])
        self.cancel_requests = []

    def __call__(self, tool, args=None):
        args = args or {}
        self.calls.append({"tool": tool, "arguments": args})
        if tool in ("connect", "open_lens"):
            return None
        if tool == "get_system_settings":
            return copy.deepcopy(self.settings)
        if tool == "update_system_settings":
            self.updates += 1
            if self.ignore_restore and self.updates > 1:
                return copy.deepcopy(self.settings)
            self.settings["polarization"].update(args["settings"]["polarization"])
            return copy.deepcopy(self.settings)
        if tool == "run_analysis":
            kind = args["request"]["kind"]
            self.tasks["task-" + kind] = kind
            return {"task_id": "task-" + kind, "state": "queued"}
        if tool == "get_task_status":
            state = self.states.pop(0) if self.states else self.task_state
            return {"task_id": args["task_id"], "state": state}
        if tool == "cancel_task":
            self.cancel_requests.append(args["task_id"])
            return {"task_id": args["task_id"], "state": "cancelled"}
        if tool == "get_task_result":
            kind = self.tasks[args["task_id"]]
            return {"rows": [], "next_start": None, "input_header": {"jones": self.jones(kind)}}
        if tool == "disconnect":
            if self.disconnect_fails:
                raise pc.ProbeFailure("disconnect", {"ok": False})
            return {"connected": False}
        raise AssertionError("unexpected tool " + tool)


def test_n2_headers_follow_system_polarization_and_restore(tmp_path):
    call = _FakeCall()
    record = n2.probe(tmp_path, call)
    assert [entry["kind"] for entry in record["analyses"]] == list(n2.KINDS)
    assert all(entry["follows_system"] for entry in record["analyses"])
    assert record["restored_equal"] is True
    assert record["restore_failures"] == []
    assert record["disconnect"]["ok"] is True
    assert record["disconnect"]["from_receipt"] is False
    assert record["disconnect"]["reply"] == {"connected": False}
    # the recorded requests are genuinely kind-only and validate against the real model
    for entry in call.calls:
        if entry["tool"] == "run_analysis":
            assert RunAnalysis(request=entry["arguments"]["request"]).request.kind in n2.KINDS
        if entry["tool"] == "update_system_settings":
            SystemPatch(**entry["arguments"]["settings"])  # real model accepts the patch


def test_n2_detects_header_that_does_not_follow_system(tmp_path):
    call = _FakeCall(jones=lambda kind: {"jx": 0.0, "jy": 1.0, "x_phase_deg": 0.0, "y_phase_deg": 0.0})
    record = n2.probe(tmp_path, call)
    assert all(entry["follows_system"] is False for entry in record["analyses"])
    assert record["restored_equal"] is True


def test_n2_failed_task_is_recorded_without_header(tmp_path):
    record = n2.probe(tmp_path, _FakeCall(task_state="failed"))
    assert all(entry["task_state"] == "failed" and "header" not in entry for entry in record["analyses"])
    assert record["restored_equal"] is True


def test_n2_disconnect_failure_listed_separately(tmp_path):
    record = n2.probe(tmp_path, _FakeCall(disconnect_fails=True))
    assert record["restored_equal"] is True
    assert any(item["step"] == "disconnect" for item in record["restore_failures"])


def test_n2_restore_mismatch_is_reported(tmp_path):
    record = n2.probe(tmp_path, _FakeCall(ignore_restore=True))
    assert record["restored_equal"] is False
    assert record["restore_failures"][0]["step"] == "restore"


def test_n2_restore_patch_uses_baseline_only():
    patch = n2.restore_patch(BASELINE)
    assert patch == {"settings": {"polarization": BASELINE["polarization"]}}
    assert n2.restore_patch({}) is None


# ------------------------------------------------------------------------- N3

PHASE_HEADER = (
    "偏振相位像差数据\n\n文件 : C:\\work\\lens.zos\n\n\n"
    "波长  :  0.5500\n视场Pos : 0.00 (度)\n"
    "Jx          :\t 0.0000\nJy          :\t 1.0000\n"
    "X-相位     :    0.00\nY-相位     :    0.00\n\n"
)
PHASE_COLUMNS = "                 弧矢                子午\n     P     X 相位      Y 相位     X 相位      Y 相位\n"


def phase_text(n=401, y_phase=lambda p: -0.01 * p * p):
    lines = []
    for i in range(n):
        p = -1.0 + 2.0 * i / (n - 1) if n > 1 else 0.0
        y = y_phase(p)
        lines.append(f"{p:.3f}\t{0.0:.9f}\t{y:.9f}\t{0.0:.9f}\t{y:.9f}")
    return PHASE_HEADER + PHASE_COLUMNS + "\n".join(lines) + "\n"


def trace_rows_for(points):
    rows = []
    for point in points:
        y = point["y_phase"]
        angle = 2 * math.pi * y
        rows.append({"electric_field": {"ex_real": 0.0, "ex_imag": 0.0,
                                        "ey_real": math.cos(angle), "ey_imag": math.sin(angle)}})
    return rows


def test_n3_reads_401_points_per_section_in_header_order():
    order, points = n3.native_points(parse_phase_aberration_text(phase_text()))
    assert order == ["sagittal", "tangential"]
    assert len(points) == 2 * n3.POINTS_PER_SECTION == 802
    assert sum(1 for p in points if p["section"] == "sagittal") == 401


def test_n3_rejects_wrong_point_count():
    with pytest.raises(pc.ProbeFailure) as caught:
        n3.native_points(parse_phase_aberration_text(phase_text(n=10)))
    assert caught.value.reply["point_count"] == 10
    assert caught.value.reply["expected"] == 401


def test_n3_batch_request_maps_pupil_directions():
    _, points = n3.native_points(parse_phase_aberration_text(phase_text()))
    request = n3.batch_request(points, wavelength_number=2)
    assert len(request["rays"]) == 802
    assert request["polarization"] == {"jx": 0.0, "jy": 1.0}
    sagittal = request["rays"][100]
    tangential = request["rays"][601]
    assert sagittal["py"] == 0.0 and sagittal["wavelength"] == 2
    assert tangential["px"] == 0.0


def test_n3_compare_marks_zero_amplitude_component_indeterminate():
    order, points = n3.native_points(parse_phase_aberration_text(phase_text()))
    comparisons = n3.compare(order, points, trace_rows_for(points))
    by_key = {(c["section"], c["component"]): c for c in comparisons}
    ey = by_key[("sagittal", "y")]
    assert ey["status"] == "compared" and ey["compared"] == 401 and ey["indeterminate"] == 0
    assert ey["maximum_errors"]["waves"] == pytest.approx(0.0, abs=1e-12)
    assert ey["unit_verdict"] == "waves" and ey["passes_waves"] is True and ey["passes_degrees"] is False
    ex = by_key[("sagittal", "x")]
    assert ex["status"] == "indeterminate" and ex["compared"] == 0 and ex["indeterminate"] == 401
    assert ex["indeterminate_points"][0]["reason"] == "zero_amplitude_component"


def test_n3_compare_waves_gate_rejects_large_error_and_accepts_tiny():
    order, points = n3.native_points(parse_phase_aberration_text(phase_text()))
    rows = trace_rows_for(points)
    index = 5
    base = 2 * math.pi * points[index]["y_phase"]
    rows[index] = {"electric_field": {"ex_real": 0.0, "ex_imag": 0.0,
                                      "ey_real": math.cos(base + 2 * math.pi * 1e-4),
                                      "ey_imag": math.sin(base + 2 * math.pi * 1e-4)}}
    ey = {(c["section"], c["component"]): c for c in n3.compare(order, points, rows)}[("sagittal", "y")]
    assert ey["maximum_errors"]["waves"] == pytest.approx(1e-4, rel=1e-6)
    assert ey["passes_waves"] is False and ey["unit_verdict"] == "none"
    assert ey["threshold_deg"] == 1e-6

    rows[index] = {"electric_field": {"ex_real": 0.0, "ex_imag": 0.0,
                                      "ey_real": math.cos(base + 2 * math.pi * 1e-10),
                                      "ey_imag": math.sin(base + 2 * math.pi * 1e-10)}}
    ey2 = {(c["section"], c["component"]): c for c in n3.compare(order, points, rows)}[("sagittal", "y")]
    assert ey2["passes_waves"] is True and ey2["unit_verdict"] == "waves"


def test_n3_compare_rejects_short_trace():
    order, points = n3.native_points(parse_phase_aberration_text(phase_text()))
    with pytest.raises(pc.ProbeFailure):
        n3.compare(order, points, trace_rows_for(points)[:10])


class _N3Call:
    def __init__(self, result, rows, task_state="succeeded"):
        self.result = result
        self.rows = rows
        self.task_state = task_state
        self.calls = []
        self.tasks = {"phase": result, "trace": {"rows": rows, "next_start": None}}

    def __call__(self, tool, args=None):
        args = args or {}
        self.calls.append({"tool": tool, "arguments": args})
        if tool in ("connect", "open_lens"):
            return None
        if tool == "get_system_settings":
            return {"wavelengths": [{"number": 2, "wavelength_um": 0.55}], "polarization": {}}
        if tool == "run_analysis":
            return {"task_id": "phase", "state": "queued"}
        if tool == "run_batch_ray_trace":
            return {"task_id": "trace", "state": "queued"}
        if tool == "get_task_status":
            return {"task_id": args["task_id"], "state": self.task_state}
        if tool == "get_task_result":
            payload = dict(self.tasks[args["task_id"]])
            payload["next_start"] = None
            return payload
        if tool == "disconnect":
            return {"connected": False}
        raise AssertionError("unexpected tool " + tool)


def test_n3_probe_end_to_end_offline(tmp_path):
    result = parse_phase_aberration_text(phase_text())
    _, points = n3.native_points(result)
    call = _N3Call(result, trace_rows_for(points))
    record = n3.probe(tmp_path, call)
    assert record["phase_task_state"] == "succeeded" and record["trace_task_state"] == "succeeded"
    assert record["wavelength_number"] == 2
    assert {(c["section"], c["component"]) for c in record["comparisons"]} == {
        ("sagittal", "x"), ("sagittal", "y"), ("tangential", "x"), ("tangential", "y")}
    assert record["disconnect"]["ok"] is True
    assert (tmp_path / "probe.json").is_file()
    assert RunAnalysis(request=[c for c in call.calls if c["tool"] == "run_analysis"][0]["arguments"]["request"]).request.kind == "phase_aberration"


def test_n3_failed_phase_task_stops_without_comparisons(tmp_path):
    result = parse_phase_aberration_text(phase_text())
    _, points = n3.native_points(result)
    record = n3.probe(tmp_path, _N3Call(result, trace_rows_for(points), task_state="failed"))
    assert record["phase_task_state"] == "failed"
    assert "comparisons" not in record
    assert record["disconnect"]["ok"] is True


# ------------------------------------------------------------ shared helpers


def test_poll_timeout_preserves_last_state_and_requests_cancel():
    ticks = iter(range(1000))

    def call(tool, args):
        assert tool in {"get_task_status", "cancel_task"}, tool
        return {"task_id": "t", "state": "running"}

    record = {}
    out = pc.poll_task(call, {"task_id": "t", "state": "running"}, record,
                       timeout_s=0.05, interval_s=0, cancel_timeout_s=0,
                       clock=lambda: next(ticks), sleep=lambda s: None)
    assert out["state"] == "running"
    assert out["poll_timed_out"] is True and out["terminated_after_cancel"] is False
    entry = record["poll_timeout"][0]
    assert entry["last_state"] == "running"
    assert entry["cancel"]["requested"] is True
    assert entry["cancel"]["terminal"] is False
    assert "poll_states" not in record


def test_poll_timeout_records_confirmed_terminal_after_cancel():
    ticks = iter(range(1000))
    states = iter(["running", "running", "cancelled"])

    def call(tool, args):
        if tool == "cancel_task":
            return {"task_id": "t", "state": "cancelled"}
        return {"task_id": "t", "state": next(states)}

    record = {}
    out = pc.poll_task(call, {"task_id": "t", "state": "running"}, record,
                       timeout_s=0, interval_s=0, clock=lambda: next(ticks), sleep=lambda s: None)
    assert out["poll_timed_out"] is True
    assert out["terminated_after_cancel"] is True
    assert record["poll_timeout"][0]["cancel"]["final_state"] == "cancelled"


def test_paged_result_walks_next_start():
    pages = {0: {"rows": [1, 2], "next_start": 2}, 2: {"rows": [3], "next_start": None}}

    def call(tool, args):
        return pages[args.get("start", 0)]

    record = {}
    merged = pc.paged_result(call, "t", record, chunk=2)
    assert merged["rows"] == [1, 2, 3]
    assert record["paging"]["t"] == {"pages": 2, "rows": 3}


def test_paged_result_rejects_repeated_cursor():
    def call(tool, args):
        return {"rows": [1], "next_start": 5}

    with pytest.raises(pc.ProbeFailure) as caught:
        pc.paged_result(call, "t", {})
    assert caught.value.reply["reason"] == "cursor_repeated"
    assert caught.value.reply["next_start"] == 5
    assert caught.value.reply["previous_start"] == 5


def test_paged_result_rejects_first_backward_cursor():
    calls = {"n": 0}

    def call(tool, args):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"rows": [1], "next_start": 100}
        return {"rows": [2], "next_start": 50}

    with pytest.raises(pc.ProbeFailure) as caught:
        pc.paged_result(call, "t", {})
    assert caught.value.reply["reason"] == "cursor_not_advancing"
    assert caught.value.reply["next_start"] == 50
    assert caught.value.reply["previous_start"] == 100


def test_paged_result_stops_at_page_limit():
    def call(tool, args):
        start = args.get("start") or 0
        return {"rows": [start], "next_start": start + 1}

    with pytest.raises(pc.ProbeFailure) as caught:
        pc.paged_result(call, "t", {}, max_pages=3)
    assert caught.value.reply["reason"] == "page_limit"


def test_paged_result_rejects_invalid_next_start():
    def call(tool, args):
        return {"rows": [1], "next_start": "2"}

    with pytest.raises(pc.ProbeFailure) as caught:
        pc.paged_result(call, "t", {})
    assert caught.value.reply["reason"] == "invalid_next_start"


# ------------------------------------------------------------------- N2 abort


def test_n2_timeout_without_terminal_cancel_stops_and_skips_restore(tmp_path):
    call = _FakeCall(task_state="running")
    record = n2.probe(tmp_path, call, timeout_s=0, cancel_timeout_s=0)
    assert call.cancel_requests == ["task-phase_aberration"]
    assert record["aborted_native_task"]["task_id"] == "task-phase_aberration"
    started = [entry for entry in record["analyses"] if "task_state" in entry]
    assert len(started) == 1  # no further analysis is started
    assert all("skipped" in entry for entry in record["analyses"][1:])
    assert record["restore_skipped"]["reason"].startswith("native task not confirmed terminal")
    assert "restored" not in record
    assert record["disconnect"]["ok"] is True


def test_n2_confirmed_cancel_allows_restore(tmp_path):
    call = _FakeCall(states=["cancelled"])
    record = n2.probe(tmp_path, call, timeout_s=0, cancel_timeout_s=0)
    assert record["analyses"][0]["terminated_after_cancel"] is True
    assert "aborted_native_task" not in record
    assert record["restored_equal"] is True
def test_n2_requests_preserve_native_kind_only_selection():
    for kind in n2.KINDS:
        assert n2.request(kind) == {'kind': kind}

