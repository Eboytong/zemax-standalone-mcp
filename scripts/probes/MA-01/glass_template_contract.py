"""Search public native contracts for glass-map filtering and substitution selectors."""
import json
import sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.config import Config
from pythonnet import load
load('netfx')
import clr
from System.Reflection import Assembly

def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    result=dict(application_created=False,assemblies=[],matches=[])
    for name in ('ZOSAPI_Interfaces.dll','ZOSAPI.dll'):
        path=Config.from_env().install_dir/name
        clr.AddReference(str(path));assembly=Assembly.LoadFrom(str(path))
        result['assemblies'].append(dict(path=str(path),identity=str(assembly.FullName)))
        for native in assembly.GetExportedTypes():
            members=[str(member) for member in native.GetMembers()]
            selected=[m for m in members if any(word in m.casefold() for word in ('substitut','glassmap','glass_map','athermal','referenceglass'))]
            if selected:result['matches'].append(dict(type=str(native.FullName),members=selected))
    (output/'contracts.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':run(sys.argv[1])
