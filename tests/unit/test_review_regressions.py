"""Archive provenance, native insertion failures and visible PDF result previews."""
import csv
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import COMMAND_MODELS
from zemax_mcp.reports import export_saved_report


def make_backend(tmp_path, system):
    b = Backend(Config(Path("unused"), tmp_path), NS(system=system))
    b.directory = tmp_path
    b.work_path = tmp_path / "old.zos"
    b._checkpoint = lambda _: "before.zos"
    return b


@pytest.mark.parametrize("outcome", ["success", "null", "no_increment", "partial", "null_after_insert", "exception", "exception_after_insert"])
def test_nsc_insert_counts_confirmed_native_rows(tmp_path, outcome):
    editor = NS(NumberOfObjects=2)
    attempts = []

    def insert(at):
        attempts.append(at)
        if outcome == "null" or outcome == "partial" and len(attempts) == 2:
            return None
        if outcome == "exception":
            raise RuntimeError("native insertion failed")
        if outcome != "no_increment":
            editor.NumberOfObjects += 1
        if outcome == "exception_after_insert":
            raise RuntimeError("native insertion failed after change")
        return None if outcome == "null_after_insert" else NS()

    editor.InsertNewObjectAt = insert
    b = make_backend(tmp_path, NS(Mode="NonSequential", NCE=editor))
    r = b.dispatch("insert_nsc_objects", dict(at=1, count=2))
    if outcome == "success":
        assert r["ok"] and r["data"] == dict(total=4, inserted=2, start=1)
        return
    assert not r["ok"]
    details = r["error"]["details"]
    assert details["requested"] == 2
    assert details["inserted"] == (1 if outcome == "partial" else 0)
    assert details["total"] == editor.NumberOfObjects
    assert details["observed_change"] == editor.NumberOfObjects - 2
    assert details["failed_at"] == attempts[-1]
    assert len(attempts) == (2 if outcome == "partial" else 1)
    assert r["error"]["code"] == ("PARTIAL_UPDATE" if editor.NumberOfObjects != 2 else "OBJECT_INSERT_FAILED")
    assert r["error"]["details"]["partial_changes_possible"]


class DetectorArray:
    Rank = 2

    def GetLength(self, _):
        return 1

    def __getitem__(self, _):
        return .25


@pytest.mark.parametrize("outcome", ["success", "run_failure", "collect_failure", "close_failure", "cancel", "configuration_failure"])
def test_archive_does_not_reuse_previous_model_detector_history(tmp_path, outcome):
    archive = tmp_path / "model.zar"
    archive.touch()
    restored = tmp_path / "restored"
    system = NS(Mode="NonSequential", SystemFile="old.zos", Save=lambda: None)
    tool = NS(SetFileName=lambda _: "BadArchive" if outcome == "configuration_failure" else "Okay",
              SetOutputFolder=lambda _: True, SetFilesNoOverwrite=lambda: None,
              NumberOfFilesInArchive=1, GetFileNameInArchive=lambda _: "loaded.zos",
              CanCancel=True, IsRunning=outcome == "cancel", Progress=0, Status="Restoring",
              Succeeded=outcome != "collect_failure", ErrorMessage="restore failed",
              WaitForCompletion=lambda: None, Close=lambda: outcome != "close_failure")
    system.Tools = NS(OpenRestoreZAR=lambda: tool)
    system.NCE = NS(NumberOfObjects=1, GetObjectAt=lambda _: NS(Type="DetectorRectangle"),
                    GetAllDetectorDataSafe=lambda *_: DetectorArray())
    system.SystemData = NS(Units=NS(AnalysisUnits="WattsPerSquareCentimeter", SourceUnits="Watts",
                                  SourceUnitPrefix="None", AnalysisUnitPrefix="None"))
    b = make_backend(tmp_path, system)
    b.detector_history = ["old_trace"]
    b.detector_history_known = True
    b.tasks["old_trace"] = dict(state="succeeded")
    b.get_system_settings = lambda _: {}
    b.get_system_summary = lambda _: {}

    def run():
        assert b.detector_history == [] and not b.detector_history_known
        system.SystemFile = str(restored / "loaded.zos")
        return outcome != "run_failure"

    tool.Run = run
    response = b.dispatch("load_archive", dict(path=str(archive), output_directory=str(restored)))
    if outcome == "configuration_failure":
        assert not response["ok"]
        assert b.detector_history == ["old_trace"] and b.detector_history_known
        return
    assert b.detector_history == [] and not b.detector_history_known
    if outcome == "cancel":
        b.active["cancel_requested"] = True
        tool.IsRunning = False
        b.tick()
        assert list(b.tasks.values())[-1]["state"] == "cancelled"
    elif outcome == "run_failure":
        assert not response["ok"] and response["error"]["code"] == "TASK_START_FAILED"
    else:
        assert response["ok"]
        assert response["data"]["state"] == ("succeeded" if outcome == "success" else "failed")
    data = b.get_detector_data(COMMAND_MODELS["get_detector_data"](detector=1))
    assert data["trace_history"] == [] and not data["history_known"] and not data["complete"]


@pytest.mark.parametrize("count", [0, 1, 200, 201])
def test_pdf_rows_expose_values_and_truncation(tmp_path, count):
    import pypdfium2
    rows = [dict(index=i, values=[.271828 + i, None], sample_token=f"sample_{i:04d}",
                 custom_condition=dict(compensation="None")) for i in range(count)]
    result = export_saved_report(tmp_path, [dict(task_id="monte_carlo", result=dict(rows=rows,
        summary=dict(columns=[dict(name="criterion", is_operand=False, unit="mm")])) )],
        "公差结果预览", False, ["markdown", "pdf"])
    artifact = next(a for a in result["artifacts"] if a["kind"] == "pdf")
    preview = artifact["row_previews"][0]
    assert preview["total_rows"] == count and preview["shown_rows"] == min(count, 200)
    assert preview["omitted_rows"] == max(0, count - 200) and preview["truncated"] == (count > 200)
    document = pypdfium2.PdfDocument(artifact["path"])
    text = "".join(document[i].get_textpage().get_text_range() for i in range(len(document)))
    document.close()
    text = "".join(text.split())
    if count:
        assert '"values":[0.271828,null]' in text and "sample_0000" in text
        assert '"custom_condition"' in text and "criterion" in text
        assert "monte_carlo_rows.csv" in text
    assert ("PDF预览已截断，省略1行" in text) == (count > 200)
    if count == 201:
        assert "sample_0199" in text and "sample_0200" not in text
        full = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
        assert full[0]["result"]["rows"][200]["values"][0] == pytest.approx(200.271828)
        with (tmp_path / "monte_carlo_rows.csv").open(encoding="utf-8-sig", newline="") as stream:
            saved = list(csv.DictReader(stream))
        assert len(saved) == 201 and json.loads(saved[200]["values"])[0] == pytest.approx(200.271828)
