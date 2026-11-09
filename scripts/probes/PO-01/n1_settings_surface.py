"""N1 - reflect the official settings surface of the four topic analyses and
read a saved CFG file.

Bounded probe: it only creates each analysis, reflects public members/enums of
its settings object, calls ``SaveTo`` to write a CFG and reads that text back.
It never calls ``ModifySettings`` and never invents CFG keys.  The session object
is injected so the same code runs against the real API and an offline fake.

``SaveTo`` may be void or may return a boolean, so its raw return value and type
are kept as evidence and success is decided by ``SaveToFailed`` (read **after**
the call) plus whether a non-empty file actually appeared.  The CFG is decoded
strictly; the saved file itself stays on disk as the evidence and the record
keeps only its path, byte count, encoding identity and a short byte prefix.  A
file that cannot be decoded is reported as undecoded rather than quoted as
valid text.
"""
from __future__ import annotations

import secrets
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
_ROOT = next(p for p in _HERE.parents if (p / "pyproject.toml").is_file())
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from probe_common import disconnect_ok, dispatch_checked, last_receipt, write_json  # noqa: E402

KINDS = ("PhaseAberration", "PolarizationRayTrace", "Transmission", "FiberCouplingSettings")


def decode_cfg(blob):
    """Decode strictly, guided by the BOM; never repair damaged bytes silently.

    Returns ``(text, encoding, source, failures)`` where ``source`` is ``bom`` for
    a byte-order mark, ``strict`` for a clean UTF-8 decode, and ``assumed`` when a
    legacy code page happened to decode (which is *not* proof of a valid CFG).
    """
    if blob[:2] in (b"\xff\xfe", b"\xfe\xff"):
        candidates = [("utf-16", "bom")]
    elif blob[:3] == b"\xef\xbb\xbf":
        candidates = [("utf-8-sig", "bom")]
    else:
        candidates = [("utf-8", "strict"), ("cp936", "assumed")]
    failures = []
    for encoding, source in candidates:
        try:
            return blob.decode(encoding), encoding, source, failures
        except UnicodeDecodeError as exc:
            failures.append({"encoding": encoding, "error": str(exc)})
    return None, None, None, failures


def describe(settings, unwrap):
    """Reflect the public surface of the settings object (no mutation)."""
    raw = unwrap(settings)
    settings_type = raw.GetType()
    members = []
    for group in ("GetProperties", "GetFields", "GetMethods"):
        getter = getattr(settings_type, group, None)
        if not callable(getter):
            continue
        for item in getter():
            members.append({"group": group[3:].lower(), "name": str(item.Name)})
    enums = {}
    is_enum = getattr(settings_type, "IsEnum", False)
    enum_names = getattr(settings_type, "GetEnumNames", None)
    if is_enum and callable(enum_names):
        enums[str(settings_type.FullName)] = [str(name) for name in enum_names()]
    if is_enum:
        enums.setdefault(str(settings_type.FullName), [str(n) for n in settings_type.GetEnumValues()])
    return {"type": str(settings_type.FullName), "is_enum": bool(is_enum), "members": members, "enums": enums}


def save_cfg(settings, path, unwrap):
    """``SaveTo`` a CFG (not ``ModifySettings``) and read the stored bytes back.

    The raw file stays on disk as the evidence; the record keeps only its path,
    byte count, decoding identity and a short hex prefix.  ``saved`` requires that
    *this* call did not raise, produced a non-empty file, and that the bytes are
    trustworthily decoded - a file left over from an earlier run cannot make a
    failing call look successful.
    """
    raw = unwrap(settings)
    target = Path(path)
    result = {
        "path": str(target),
        "return_type": None,
        "return_value": None,
        "save_error": None,
        "written_by_this_call": False,
        "save_failed_flag": None,
        "save_failed_flag_read_after_save": True,
        "file_created": False,
        "byte_count": 0,
        "bytes_hex_prefix": None,
        "encoding": None,
        "encoding_source": None,
        "encoding_confirmed": False,
        "text_trusted": False,
        "decoded": False,
        "text": None,
        "lines": None,
        "decode_failures": [],
    }
    try:
        returned = raw.SaveTo(str(target))
    except Exception as exc:
        result["save_error"] = repr(exc)
    else:
        result["written_by_this_call"] = True
        result["return_type"] = type(returned).__name__
        result["return_value"] = returned if isinstance(returned, (bool, int, float, str, type(None))) else repr(returned)
    try:
        flag = getattr(raw, "SaveToFailed", None)
        result["save_failed_flag"] = None if flag is None else bool(flag)
    except Exception as exc:
        result["save_failed_flag_error"] = repr(exc)

    result["file_created"] = target.is_file()
    if result["file_created"]:
        blob = target.read_bytes()
        result["byte_count"] = len(blob)
        result["bytes_hex_prefix"] = blob[:32].hex()
        text, encoding, source, failures = decode_cfg(blob)
        result["decode_failures"] = failures
        if text is not None:
            result.update({"encoding": encoding, "encoding_source": source,
                           "encoding_confirmed": source == "bom",
                           "text_trusted": source in ("bom", "strict"),
                           "decoded": True, "text": text, "lines": len(text.splitlines())})
    result["saved"] = bool(result["written_by_this_call"] and result["file_created"]
                           and result["byte_count"] > 0 and result["decoded"]
                           and result["text_trusted"] and not result["save_failed_flag"])
    return result


def _close_entry(entry, session, analysis, kind, record):
    try:
        receipt = session.close(analysis)
    except Exception as exc:
        entry["closed"] = False
        entry["close_error"] = repr(exc)
        record["close_failures"].append({"kind": kind, "error": repr(exc)})
        return
    if isinstance(receipt, dict):
        entry["close_receipt"] = receipt
        entry["closed"] = bool(receipt.get("closed"))
    else:
        entry["closed"] = bool(receipt)


def probe(folder, session):
    """Run N1 against an injected session.

    ``session`` supplies ``new_analysis(name)``, ``unwrap(obj)`` and
    ``close(analysis)`` (bool or a receipt dict); the real CLI binds these to the
    ZOS-API.
    """
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    run_stamp = f"{secrets.token_hex(4)}"
    record = {"probe": "N1", "purpose": "official settings surface reflection and saved-CFG read",
              "policy": "no ModifySettings; no CFG key guessing", "run_stamp": run_stamp,
              "analyses": [], "close_failures": []}
    for kind in KINDS:
        entry = {"kind": kind}
        analysis = None
        try:
            analysis = session.new_analysis(kind)
            settings = analysis.GetSettings()
            entry["settings"] = describe(settings, session.unwrap)
            entry["cfg"] = save_cfg(settings, folder / f"{kind}-{run_stamp}.cfg", session.unwrap)
        except Exception as exc:  # keep the probe alive for the remaining kinds
            entry["error"] = repr(exc)
        finally:
            if analysis is not None:
                _close_entry(entry, session, analysis, kind, record)
        record["analyses"].append(entry)
    write_json(folder / "n1-settings-surface.json", record)
    return record


def _real_session(backend, folder):
    from zemax_mcp.data import unwrap

    class Session:
        def new_analysis(self, name):
            ident = getattr(backend.native.api.Analysis.AnalysisIDM, name)
            return backend.system.Analyses.New_Analysis_SettingsFirst(ident)

        def unwrap(self, obj):
            return unwrap(obj)

        def close(self, analysis):
            closed = backend._close_task_native(dict(native=analysis))
            return {"closed": bool(closed), "reply": closed}

    return Session()


def run_cli(backend, folder, model):
    """CLI entry: checked startup receipts, then the probe, then cleanup receipts.

    A failed ``connect`` or ``open_lens`` aborts before the session is built, so
    the probe never reads an empty system; the disconnect receipt is recorded in
    ``finally`` regardless of what happened.
    """
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    receipts = []
    record = {"probe": "N1", "purpose": "official settings surface reflection and saved-CFG read",
              "policy": "no ModifySettings; no CFG key guessing", "analyses": [],
              "close_failures": [], "startup": {}, "receipts": receipts}
    try:
        connect = dispatch_checked(backend, receipts, "connect", {})
        record["startup"]["connect_ok"] = connect["ok"]
        if not connect["ok"]:
            record["startup"]["aborted"] = "connect_failed"
            return record
        opened = dispatch_checked(backend, receipts, "open_lens", {"path": str(model)})
        record["startup"]["open_lens_ok"] = opened["ok"]
        if not opened["ok"]:
            record["startup"]["aborted"] = "open_lens_failed"
            return record
        try:
            session = _real_session(backend, folder)
        except Exception as exc:
            record["startup"]["aborted"] = "session_failed"
            record["startup"]["session_error"] = repr(exc)
            return record
        record.update(probe(folder, session))
    finally:
        disconnect = dispatch_checked(backend, receipts, "disconnect", {})
        record["disconnect"] = {"ok": disconnect_ok(disconnect["reply"]),
                                "reply": disconnect["reply"]}
        record["disconnect_receipt"] = last_receipt(receipts, "disconnect")
        write_json(folder / "n1-settings-surface.json", record)
    return record


if __name__ == "__main__":
    import json

    from zemax_mcp.backend import Backend
    from zemax_mcp.config import Config

    out = Path(sys.argv[1]).resolve()
    model = sys.argv[2] if len(sys.argv) > 2 else str(
        Path.home() / "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")
    backend = Backend(Config(Config.from_env().install_dir, out / "native"))
    result = run_cli(backend, out, model)
    print(json.dumps({"folder": str(out), "startup": result.get("startup"),
                      "disconnect": result.get("disconnect", {}).get("ok"),
                      "analyses": [
                          {"kind": a["kind"], "type": a.get("settings", {}).get("type"),
                           "members": len(a.get("settings", {}).get("members", [])),
                           "cfg_saved": a.get("cfg", {}).get("saved"),
                           "cfg_bytes": a.get("cfg", {}).get("byte_count"),
                           "cfg_encoding": a.get("cfg", {}).get("encoding"),
                           "closed": a.get("closed")}
                          for a in result.get("analyses", [])]}, ensure_ascii=False))
