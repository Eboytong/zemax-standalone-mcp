"""Load the installed Windows ZOS-API, and own only the instance we create."""

from pathlib import Path
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from .errors import ZemaxError


def restore_user_environment():
    """Complete the local Windows logon environment; explicit client values win."""
    import win32api
    import win32con
    import win32profile
    import win32security
    token = win32security.OpenProcessToken(
        win32api.GetCurrentProcess(), win32con.TOKEN_QUERY | win32con.TOKEN_DUPLICATE,
    )
    try:
        defaults = win32profile.CreateEnvironmentBlock(token, False)
    finally:
        token.Close()
    for name, value in defaults.items():
        os.environ.setdefault(name, value)


class NativeSession:
    def __init__(self, stage_observer=None):
        self.api = None
        self.application = None
        self.connection = None
        self.loaded_dir = None
        self._connection_ready = False
        self.stage_observer = stage_observer
        self.stage_events = []
        self.observer_warnings = []
        self._trace_start = time.monotonic()
        self._failed_stage = None

    @staticmethod
    def _error_record(exc):
        record = dict(type=type(exc).__name__, message=str(exc))
        if isinstance(exc, ZemaxError):
            record.update(code=exc.code, details=dict(exc.details))
        return record

    def _emit_stage(self, stage, event, **details):
        record = dict(stage=stage, event=event,
                      timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                      elapsed_seconds=time.monotonic()-self._trace_start, **details)
        self.stage_events.append(record)
        if self.stage_observer is not None:
            try:
                self.stage_observer(dict(record))
            except Exception as exc:
                self.observer_warnings.append(self._error_record(exc))

    @contextmanager
    def _stage(self, name):
        start = time.monotonic()
        self._emit_stage(name, "started")
        try:
            yield
        except Exception as exc:
            self._failed_stage = name
            self._emit_stage(name, "failed", duration_seconds=time.monotonic()-start,
                             error=self._error_record(exc))
            raise
        else:
            self._emit_stage(name, "completed", duration_seconds=time.monotonic()-start)

    def connect(self, install_dir: Path):
        if self.application is not None:
            if not self._connection_ready:
                raise ZemaxError("RECONNECT_REQUIRED", "原生应用仍待确认关闭，请先断开。")
            return self.application
        self.stage_events = []
        self.observer_warnings = []
        self._trace_start = time.monotonic()
        self._failed_stage = None
        try:
            with self._stage("install_check"):
                install_dir = install_dir.resolve()
                if self.loaded_dir is not None and self.loaded_dir != install_dir:
                    raise ZemaxError("RESTART_REQUIRED", "更换 API 安装目录前请重启服务。")
                for name in ("ZOSAPI_NetHelper.dll", "ZOSAPI_Interfaces.dll", "ZOSAPI.dll"):
                    if not (install_dir / name).is_file():
                        raise ZemaxError("INSTALL_NOT_FOUND", "找不到安装目录中的 API DLL。", path=str(install_dir / name))
            with self._stage("environment"):
                restore_user_environment()
            with self._stage("clr_load"):
                from pythonnet import load
                load("netfx")
                from System import Console
                Console.SetOut(Console.Error)
                import clr
            with self._stage("nethelper_assembly"):
                clr.AddReference(str(install_dir / "ZOSAPI_NetHelper.dll"))
                # The first installed assembly already binds this process to its directory.
                self.loaded_dir = install_dir
                import ZOSAPI_NetHelper
            with self._stage("zos_initialize"):
                if not ZOSAPI_NetHelper.ZOSAPI_Initializer.Initialize(str(install_dir)):
                    raise ZemaxError("INITIALIZATION_FAILED", "ZOS-API 初始化失败。")
            with self._stage("api_assemblies"):
                clr.AddReference(str(install_dir / "ZOSAPI_Interfaces.dll"))
                clr.AddReference(str(install_dir / "ZOSAPI.dll"))
                import ZOSAPI
                self.api = ZOSAPI
            with self._stage("connection_create"):
                self.connection = ZOSAPI.ZOSAPI_Connection()
            with self._stage("application_create"):
                self.application = self.connection.CreateNewApplication()
                if self.application is None:
                    raise ZemaxError("CONNECTION_FAILED", "未能创建 Standalone 后台实例。")
            with self._stage("license_check"):
                if not self.application.IsValidLicenseForAPI:
                    raise ZemaxError("INVALID_LICENSE", "当前许可不能使用 ZOS-API。")
            with self._stage("primary_system"):
                if self.application.PrimarySystem is None:
                    raise ZemaxError("SYSTEM_NOT_AVAILABLE", "后台实例没有主光学系统。")
        except Exception as original:
            stage = self._failed_stage
            cleanup = None
            try:
                self.disconnect()
            except Exception as exc:
                cleanup = self._error_record(exc)
            failure = original if isinstance(original, ZemaxError) else ZemaxError(
                "NATIVE_ERROR", str(original), type=type(original).__name__)
            failure.details.update(startup_stage=stage, startup_events=list(self.stage_events))
            if cleanup is not None:
                failure.details["cleanup_error"] = cleanup
            if failure is original:
                raise
            raise failure from original
        self._connection_ready = True
        return self.application

    @property
    def connection_ready(self):
        return self.application is not None and self._connection_ready

    @property
    def startup_diagnostics(self):
        return dict(events=list(self.stage_events), observer_warnings=list(self.observer_warnings))

    @property
    def system(self):
        if self.application is None or not self._connection_ready:
            raise ZemaxError("NOT_CONNECTED", "请先调用 connect。")
        return self.application.PrimarySystem

    def disconnect(self):
        self._connection_ready = False
        if self.application is not None:
            with self._stage("application_close"):
                outcome = self.application.CloseApplication()
                if outcome is False:
                    raise ZemaxError("CLEANUP_FAILED", "原生应用关闭返回失败。")
        self.application = None
        self.connection = None

    @staticmethod
    def enum(enum_type, name: str):
        from System import Enum
        try:
            # Enum.Parse alone also accepts numeric strings; expose names only.
            names = list(Enum.GetNames(enum_type))
            if name not in names:
                raise ValueError(name)
            return Enum.Parse(enum_type, name)
        except Exception:
            raise ZemaxError("INVALID_ENUM", f"无效枚举值：{name}", allowed=list(Enum.GetNames(enum_type))) from None

    @staticmethod
    def enum_names(enum_type):
        from System import Enum
        return list(Enum.GetNames(enum_type))

    def set_enum(self, obj, name, value):
        enum_type = obj.GetType().GetProperty(name).PropertyType
        setattr(obj, name, self.enum(enum_type, value))

    def property_enum_names(self, obj, name):
        return self.enum_names(obj.GetType().GetProperty(name).PropertyType)
