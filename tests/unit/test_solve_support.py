"""Capabilities distinguish native enumeration from scoped optical evidence."""
import json
from zemax_mcp.solve_support import solve_validation_summary

def test_solve_support_scope_is_compact():
    r=solve_validation_summary()
    assert r["status"]=="recorded"
    assert not r["native_enumeration_is_numeric_validation"]
    assert r["focused_cases"]==dict(total=59,numeric_passed=46,native_rejected=13,numeric_reference_pending=0)
    assert r["matrix"]["total"]==936
    assert sum(r["matrix"]["status_counts"].values())==936
    assert "cases"not in r
    assert r["persistence_limits"]==[dict(surface_type="Hologram2",cell="parameter_13",mode="Variable",
        required_value=1,rejected_value=0,reference="docs/topics/analysis/solve-support.md#hologram2-模式持久化")]

def test_missing_solve_evidence_is_explicit(tmp_path,monkeypatch):
    import zemax_mcp.solve_support as module
    monkeypatch.setattr(module,"__file__",str(tmp_path/"a/b/module.py"))
    assert module.solve_validation_summary()["status"]=="evidence_unavailable"

def test_invalid_solve_evidence_is_explicit(tmp_path,monkeypatch):
    import zemax_mcp.solve_support as module
    (tmp_path/"docs/reference").mkdir(parents=True)
    (tmp_path/"docs/reference/solve-support.json").write_text("{}",encoding="utf-8")
    monkeypatch.setattr(module,"__file__",str(tmp_path/"a/b/module.py"))
    r=module.solve_validation_summary()
    assert r["status"]=="evidence_unavailable"and r["reason"]

