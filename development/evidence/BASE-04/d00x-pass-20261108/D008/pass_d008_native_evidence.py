"""Offline extraction of static reflection + raw native result evidence for the
five D008 drawing/viewer items (ISOElementDrawing, ZemaxElementDrawing,
PrescriptionGraphic, NSCObjectViewer, PartViewer).

Pure offline: reads stored JSON only; never launches OpticStudio.
Outputs .local/coordination/pass-d008-native-evidence.json
"""
import json
from pathlib import Path

R = Path(r"C:\Users\tonge\Desktop\Zemax_MCP")
OUT = Path(__file__).resolve().parent / "pass-d008-native-evidence.json"

OUTLET_KEYWORDS = ("image", "bitmap", "bmp", "png", "jpeg", "jpg", "emf",
                   "metafile", "clipboard", "screenshot", "export", "saveto", "saveimage")


def load(rel):
    p = R / rel
    return json.loads(p.read_text(encoding="utf-8")), str(p)


def items_by_enum(rel):
    d, src = load(rel)
    return {it.get("native_enum"): it for it in d.get("items", [])}, src


def outlets(names):
    hits = []
    for n in names:
        low = str(n).lower()
        if any(k in low for k in OUTLET_KEYWORDS):
            hits.append(n)
    return hits


def static_block(enum, rel):
    entries, src = items_by_enum(rel)
    it = entries.get(enum)
    if it is None:
        return {"source": src, "present": False}
    return {
        "source": src,
        "present": True,
        "runtime_settings_type": it.get("runtime_settings_type"),
        "interfaces": it.get("interfaces", []),
        "methods_count": len(it.get("methods", [])),
        "methods_sample": it.get("methods", [])[:8],
        "properties": [{"name": p.get("name"), "type": p.get("type")} for p in it.get("properties", [])],
        "cfg_export_returned": (it.get("cfg_export") or {}).get("returned"),
        "closed": it.get("closed"),
        "error": it.get("error"),
    }


def raw_block(rel, *, object_list=False):
    d, src = load(rel)
    result = d.get("result") or {}
    counts = result.get("counts") or {}
    member_names = list(d.get("result_members") or [])
    block = {
        "source": src,
        "analysis": d.get("analysis"),
        "input": (d.get("context") or {}).get("source_file") or d.get("input"),
        "session_id": (d.get("context") or {}).get("session_id"),
        "settings_values": d.get("settings"),
        "settings_type": d.get("settings_type"),
        "settings_members_count": (len(d["settings_members"]) if d.get("settings_members") else None),
        "result_type": d.get("result_type") or result.get("type"),
        "result_members_count": (len(d["result_members"]) if d.get("result_members") else None),
        "counts": counts,
        "counts_nonzero": {k: v for k, v in counts.items() if v},
        "messages_count": len(result.get("messages") or []) if isinstance(result.get("messages"), list) else None,
        "text_export": result.get("text_export"),
        "image_vector_outlet_members": outlets(member_names),
        "model_unchanged": d.get("model_unchanged"),
        "close": d.get("close"),
        "disconnect_ok": (d.get("disconnect") or {}).get("ok"),
        "error": d.get("error"),
    }
    if object_list:
        objs = d.get("objects") or {}
        rows = ((objs.get("data") or {}).get("rows") or []) if objs.get("ok") else []
        block["objects"] = {
            "ok": objs.get("ok"),
            "count": len(rows),
            "total": (objs.get("data") or {}).get("total"),
            "next_start": (objs.get("data") or {}).get("next_start"),
            "types": [r.get("type") for r in rows],
            "error": objs.get("error"),
        }
    return block


def probe_block(rel):
    d, src = load(rel)
    it = d["items"][0]
    counts = it.get("counts") or {}
    result_methods = it.get("result_methods") or []
    result_properties = it.get("result_properties") or []
    return {
        "source": src,
        "analysis": it.get("native_id"),
        "input": (d.get("connect") or {}).get("data", {}).get("last_session", {}).get("source_file"),
        "session_id": (d.get("connect") or {}).get("data", {}).get("last_session", {}).get("session_id"),
        "settings_type": it.get("settings_type"),
        "settings_properties": [p.get("name") for p in it.get("properties", [])],
        "settings_methods_count": len(it.get("methods", [])),
        "cfg_saved": it.get("cfg_saved"),
        "counts": counts,
        "counts_nonzero": {k: v for k, v in counts.items() if v},
        "messages": it.get("messages"),
        "text_export": it.get("text_exported"),
        "result_methods_count": len(result_methods),
        "result_properties_count": len(result_properties),
        "image_vector_outlet_members": outlets(result_methods + [p.get("name") for p in result_properties]),
        "closed": it.get("closed"),
        "disconnect_ok": (d.get("disconnect") or {}).get("ok"),
    }


report = {"note": "pure offline extraction from stored JSON; historical native runs, not this-pass executions",
          "items": {}}

report["items"]["CV-01.ISOElementDrawing"] = {
    "static": static_block("ISOElementDrawing", "development/evidence/CV-01/runtime071/settings.json"),
    "raw": raw_block(".local/evidence/development/CV-01/iso-element-drawing-20261108/summary.json"),
}

report["items"]["MF-01.ZemaxElementDrawing"] = {
    "static": static_block("ZemaxElementDrawing", "development/evidence/MF-01/runtime078/settings.json"),
    "raw": probe_block(".local/evidence/development/MF-01/zemax-element-drawing-repeat-20261108/probe.json"),
}

# PrescriptionGraphic: static from sequential settings if available, else runtime066 (NSC attempt error)
pg_static_seq = Path(r"C:\Users\tonge\Desktop\Zemax_MCP\verification\development\NS-04\runtime068-sequential\settings.json")
pg_static = (static_block("PrescriptionGraphic", str(pg_static_seq.relative_to(R)).replace("\\", "/"))
             if pg_static_seq.is_file() else static_block("PrescriptionGraphic", "development/evidence/NS-04/runtime066/settings.json"))
report["items"]["NS-04.PrescriptionGraphic"] = {
    "static": pg_static,
    "raw_sequential": raw_block(".local/evidence/development/NS-03/prescription-graphic-sequential-20261108/summary.json", object_list=True),
    "raw_nsc": raw_block(".local/evidence/development/NS-03/prescription-graphic-nsc-20261108/summary.json", object_list=True),
}

report["items"]["NS-04.NSCObjectViewer"] = {
    "static": static_block("NSCObjectViewer", "development/evidence/NS-04/runtime066/settings.json"),
    "raw": raw_block(".local/evidence/development/NS-03/nsc-object-viewer-repeat-20261108/summary.json", object_list=True),
}

report["items"]["NS-04.PartViewer"] = {
    "static": static_block("PartViewer", "development/evidence/NS-04/runtime066/settings.json"),
    "raw_colorimetry": raw_block(".local/evidence/development/NS-03/part-viewer-repeat-20261108/summary.json", object_list=True),
    "raw_lens_mount": raw_block(".local/evidence/development/NS-03/part-viewer-lens-mount-20261108/summary.json", object_list=True),
}

OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", OUT, OUT.stat().st_size, "bytes")

# ASCII summary to stdout
for name, blk in report["items"].items():
    print("\n==", name)
    st = blk["static"]
    print("  static type:", st.get("runtime_settings_type"), "closed:", st.get("closed"),
          "props:", [p["name"] for p in (st.get("properties") or [])], "err:", bool(st.get("error")))
    for key in ("raw", "raw_sequential", "raw_nsc", "raw_colorimetry", "raw_lens_mount"):
        if key not in blk:
            continue
        r = blk[key]
        print("  ", key, "result_type:", r.get("result_type") or (blk.get("raw") or {}).get("result_type"),
              "| counts:", r.get("counts"), "| text_export:", r.get("text_export"),
              "| outlet_members:", r.get("image_vector_outlet_members"),
              "| close:", r.get("close", r.get("closed")), "| disconnect_ok:", r.get("disconnect_ok"))
        if "objects" in r:
            print("     objects:", r["objects"]["count"], r["objects"]["types"], "ok", r["objects"]["ok"])
        if r.get("error"):
            print("     error:", r["error"])
