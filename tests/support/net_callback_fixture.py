from zemax_mcp.config import PROJECT_ROOT
"""Build the controlled callback against the installed 2024 R2 public assemblies."""
import json
from pathlib import Path
import subprocess
from zemax_mcp.config import Config

TYPE_NAME='ZemaxMcp.Fixtures.ScalarCallback'


def build(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    compiler=Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
    install=Config.from_env().install_dir
    source=PROJECT_ROOT/'fixtures/net_callback/ScalarCallback.cs'
    output=folder/'net-callback.dll'
    command=[str(compiler),'/nologo','/target:library','/platform:x64','/out:'+str(output.resolve()),
        '/reference:'+str(install/'ZOSAPI_Interfaces.dll'),'/reference:'+str(install/'ZOSAPI.dll'),str(source)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=25,creationflags=subprocess.CREATE_NO_WINDOW)
    record=dict(command=command,returncode=result.returncode,stdout=result.stdout,stderr=result.stderr,callback_type=TYPE_NAME)
    (folder/'callback-build.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if result.returncode:raise RuntimeError(record)
    return output.resolve()
