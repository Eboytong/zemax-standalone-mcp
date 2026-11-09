"""Inspect the installed UserDefinedCOM analysis factory and close its tool."""
import json
import pytest
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_userdefinedcom_factory_runtime_contract():
    from zemax_mcp.config import Config
    from zemax_mcp.native import NativeSession

    folder = run_dir("userdefinedcom_factory")
    session = NativeSession()
    analysis = None
    record = {"analysis_closed": False, "application_closed": False}
    try:
        app = session.connect(Config.from_env().install_dir)
        record["version"] = str(app.OpticStudioVersion)
        analysis_id = session.api.Analysis.AnalysisIDM.UserDefinedCOM
        record["analysis_id"] = int(analysis_id)
        analysis = app.PrimarySystem.Analyses.New_Analysis(analysis_id)
        record["analysis_created"] = analysis is not None
        if analysis is not None:
            settings = analysis.GetSettings()
            record["settings_type"] = str(settings.GetType().FullName)
            record["settings_methods"] = sorted(
                str(method.Name) for method in settings.GetType().GetMethods()
            )
            record["analysis_valid"] = bool(analysis.IsValid)
            record["result_type"] = str(analysis.GetResults().GetType().FullName) if analysis.GetResults() is not None else None
    except Exception as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        if analysis is not None:
            try:
                analysis.Close()
                record["analysis_closed"] = True
            except Exception as exc:
                record["analysis_close_error"] = {"type": type(exc).__name__, "message": str(exc)}
        try:
            session.disconnect()
            record["application_closed"] = True
        except Exception as exc:
            record["application_close_error"] = {"type": type(exc).__name__, "message": str(exc)}
        (folder / "factory.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if "analysis_close_error" in record or "application_close_error" in record:
            raise AssertionError(record)
