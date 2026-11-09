"""Read public spot/ray sampling contracts without creating an application."""
import json,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.config import Config
from pythonnet import load
load('netfx')
import clr
from System.Reflection import Assembly

def run(folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    path=Config.from_env().install_dir/'ZOSAPI_Interfaces.dll'
    clr.AddReference(str(path));assembly=Assembly.LoadFrom(str(path))
    result=dict(application_created=False,assembly=str(assembly.FullName),contracts=[])
    for typ in assembly.GetExportedTypes():
        name=str(typ.FullName)
        if typ.IsInterface and any(token in name.casefold() for token in ('spot','raytrace','raydata','normunpol','normpol')):
            result['contracts'].append(dict(type=name,properties=[str(p) for p in typ.GetProperties()],
                methods=[str(m) for m in typ.GetMethods() if not m.IsSpecialName],parents=[str(p.FullName) for p in typ.GetInterfaces()]))
    (folder/'contracts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':run(sys.argv[1])
