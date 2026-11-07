"""Parameter metadata from installed official POP DLLs, queried out of process."""
import ctypes
import json
from pathlib import Path
import subprocess
import sys

from .errors import ZemaxError


SUPPORTED_DLLS = ("beamsamp1.dll", "laguerre beam.dll", "ince-gaussian-64.dll")


def native_names(path):
    """Official UserParamNames ABI: one-based index in data[0], empty terminator."""
    library = ctypes.WinDLL(str(path))
    function = library.UserParamNames
    function.argtypes = [ctypes.POINTER(ctypes.c_char)]
    function.restype = ctypes.c_int
    names = []
    for index in range(1, 65):
        buffer = ctypes.create_string_buffer(4096)
        buffer[0] = bytes([index])
        if function(buffer) != 0:
            raise ValueError(f"UserParamNames rejected index {index}")
        name = buffer.value.decode("mbcs")
        if not name:
            return names
        names.append(name)
    raise ValueError("Parameter metadata exceeds the supported 64-entry bound")


def installed_names(data_dir, filename):
    if not filename or Path(filename).name != filename or filename.lower() not in SUPPORTED_DLLS:
        raise ZemaxError("POP_PARAMETER_QUERY_FAILED", "此 DLL 不在已适配的本机 POP 参数查询列表中。", filename=filename)
    if not data_dir:
        raise ZemaxError("INVALID_RESOURCE", "本机 Zemax 数据目录不可用。")
    root = (Path(data_dir) / "DLL" / "PhysicalOptics").resolve()
    if not root.is_dir():
        raise ZemaxError("INVALID_RESOURCE", "本机 POP DLL 目录不存在。", directory=str(root))
    matches = [p for p in root.iterdir() if p.name.lower() == filename.lower() and p.is_file()]
    if len(matches) != 1 or matches[0].resolve().parent != root:
        raise ZemaxError("INVALID_RESOURCE", "找不到本机 POP DLL。", filename=filename, directory=str(root))
    try:
        result = subprocess.run([sys.executable, "-B", "-m", "zemax_mcp.pop_dll", str(matches[0])],
                                capture_output=True, text=True, encoding="utf-8", timeout=10,
                                stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise ValueError(f"isolated query exited {result.returncode}: {result.stderr[-1000:]}")
        names = json.loads(result.stdout)
        if not isinstance(names, list) or not 1 <= len(names) <= 64 or any(type(n) is not str or not n.strip() or len(n) > 256 for n in names):
            raise ValueError("Invalid isolated DLL parameter metadata")
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        raise ZemaxError("POP_PARAMETER_QUERY_FAILED", "隔离进程未取得有效的 DLL 参数。", filename=filename, reason=str(exc)) from exc
    return names


def parameter_names(settings, role, mode, data_dir, filename):
    count_property = "NumberOfParameters" if role == "beam" else "NumberOfFiberParameters"
    get_name = settings.GetParameterName if role == "beam" else settings.GetFiberParameterName
    try:
        count = int(getattr(settings, count_property))
        if not 0 <= count <= 1001:
            raise ValueError("Native parameter count is outside 0..1001")
        return [str(get_name(i)) for i in range(count)], dict(source="ZOS-API", role=role)
    except Exception as exc:
        if mode != "DLL":
            raise ZemaxError("POP_PARAMETER_QUERY_FAILED", "本机原生参数查询失败。", role=role, reason=str(exc)) from exc
        names = installed_names(data_dir, filename)
        return names, dict(source="isolated installed DLL UserParamNames", role=role, filename=filename,
                           api_metadata_error=str(exc), numbering="zero-based public parameter index; native DLL data[0] is one-based")


if __name__ == "__main__":
    try:
        print(json.dumps(native_names(Path(sys.argv[1])), ensure_ascii=True))
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
