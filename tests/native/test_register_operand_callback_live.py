"""Probe formal NET operand registration and application-scoped cleanup."""
import json
import pytest
from tests.support.net_callback_fixture import TYPE_NAME, build
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_register_controlled_net_operand_callback():
    from zemax_mcp.config import Config
    from zemax_mcp.native import NativeSession

    folder = run_dir("register_net_operand_callback")
    library = build(folder)
    session = NativeSession()
    record = {"callback_type": TYPE_NAME, "application_closed": False}
    try:
        app = session.connect(Config.from_env().install_dir)
        record["version"] = str(app.OpticStudioVersion)
        settings = app.CreateSettings()
        settings.SetDoubleValue("input", 1.5)
        message = app.RegisterNETOperandCallback(str(library), TYPE_NAME, settings)
        record["message_is_null"] = message is None
        if message is not None:
            record["message_type"] = str(message.GetType().FullName)
            record["message_text"] = str(message)
            record["message_members"] = []
            for prop in message.GetType().GetProperties():
                try:
                    value = prop.GetValue(message, None)
                    if value is None or isinstance(value, (bool, int, float, str)):
                        record["message_members"].append({"name": prop.Name, "value": value})
                except Exception as exc:
                    record["message_members"].append({"name": prop.Name, "error": str(exc)})
            assert record["message_type"] == "ZOSAPI.Analysis.Message"
            assert any(
                member.get("name") == "Text" and member.get("value") == "This is not a UDOC!"
                for member in record["message_members"]
            ), record
    except Exception as exc:
        record["error"] = {"type": type(exc).__name__, "message": str(exc)}
        raise
    finally:
        try:
            session.disconnect()
            record["application_closed"] = True
        except Exception as exc:
            record["close_error"] = {"type": type(exc).__name__, "message": str(exc)}
        (folder / "registration.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if "close_error" in record:
            raise AssertionError(record["close_error"])
