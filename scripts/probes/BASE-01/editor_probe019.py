import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Reflect installed editor interfaces without creating an OpticStudio instance."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(PROJECT_ROOT/'src'))
from zemax_mcp.config import Config

def run(folder,all_interfaces=False):
    from pythonnet import load
    load('netfx')
    import clr
    from System.Reflection import Assembly
    install=Config.from_env().install_dir
    clr.AddReference(str(install/'ZOSAPI_Interfaces.dll'))
    assembly=Assembly.LoadFrom(str(install/'ZOSAPI_Interfaces.dll'))
    result=dict(assembly=str(assembly.FullName),install_dir=str(install),source='installed public DLL reflection; no native application',interfaces={})
    for t in assembly.GetTypes():
        if not str(t.FullName).startswith('ZOSAPI.' if all_interfaces else 'ZOSAPI.Editors.'):
            continue
        if t.IsInterface:
            result['interfaces'][str(t.FullName)]={'properties':[dict(name=str(p.Name),type=str(p.PropertyType),can_read=bool(p.CanRead),can_write=bool(p.CanWrite)) for p in t.GetProperties()], 'methods':[str(m) for m in t.GetMethods() if not m.IsSpecialName]}
        elif t.IsEnum:
            from System import Enum
            result.setdefault('enums',{})[str(t.FullName)]={str(n):int(Enum.Parse(t,n)) for n in Enum.GetNames(t)}
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    (folder/('api-interfaces.json' if all_interfaces else 'editor-interfaces.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Reflected',len(result['interfaces']),'interfaces and',len(result.get('enums',{})),'enums')
if __name__=='__main__':run(sys.argv[1],'--all'in sys.argv)
