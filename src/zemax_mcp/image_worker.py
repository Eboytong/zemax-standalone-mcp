"""Offline image renderer; no Zemax application or DLL is loaded."""
import json,sys,ctypes
ctypes.windll.kernel32.SetDllDirectoryW(None)
from pathlib import Path
from .export_models import AnalysisImage
from .plotting import export_image

def main():
    print("image_worker: reading saved input",flush=True)
    payload=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    request=AnalysisImage.model_validate(payload["request"])
    print("image_worker: rendering",flush=True)
    result=export_image(payload["result"],request,Path(request.path))
    Path(sys.argv[2]).write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding="utf-8")
    print("image_worker: complete",flush=True)

if __name__=="__main__":main()
