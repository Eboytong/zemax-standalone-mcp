"""Inspect the formal MFE UDOC row contract without triggering the external host."""
import json
from pathlib import Path
import pytest
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_udoc_operand_row_contract():
    from zemax_mcp.config import Config
    from zemax_mcp.native import NativeSession

    folder = run_dir("udoc_operand_contract")
    session = NativeSession()
    record = {"application_closed": False}
    try:
        app = session.connect(Config.from_env().install_dir)
        record["version"] = str(app.OpticStudioVersion)
        system = app.PrimarySystem
        sample = Path.home() / "Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"
        record["sample_loaded"] = bool(system.LoadFile(str(sample), False))
        mfe = system.MFE
        row = mfe.AddOperand()
        changed = row.ChangeType(session.api.Editors.MFE.MeritOperandType.UDOC)
        record["change_type_return"] = str(changed)
        record["row_type"] = str(row.Type)
        record["active_cells"] = []
        record["cells"] = []
        for column in range(2, 10):
            cell = row.GetCellAt(column)
            item = {"column": column, "header": str(cell.Header), "active": bool(cell.IsActive),
                    "read_only": bool(cell.IsReadOnly), "data_type": str(cell.DataType)}
            record["cells"].append(item)
            if cell.IsActive:
                record["active_cells"].append(item)
        record["operand_results_api"] = [
            str(method) for method in app.GetType().GetMethods()
            if "Operand" in str(method.Name) or "Operand" in str(method)
        ]
    except Exception as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        try:
            session.disconnect()
            record["application_closed"] = True
        except Exception as exc:
            record["close_error"] = {"type": type(exc).__name__, "message": str(exc)}
        (folder / "udoc-row.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if "close_error" in record:
            raise AssertionError(record)
