"""Record public native contracts including inherited interface members.

This probe loads assemblies only. It does not initialize ZOS or create an app.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from zemax_mcp.config import Config


def run(output):
    from pythonnet import load
    load('netfx')
    import clr
    from System.Reflection import Assembly

    install = Config.from_env().install_dir
    contracts = {}
    assemblies = []
    for name in ('ZOSAPI_Interfaces.dll', 'ZOSAPI.dll'):
        path = install / name
        clr.AddReference(str(path))
        assembly = Assembly.LoadFrom(str(path))
        exported = list(assembly.GetExportedTypes())
        assemblies.append(dict(path=str(path),identity=str(assembly.FullName),exported_types=len(exported)))
        for native_type in exported:
            if not native_type.IsInterface:
                continue
            inherited = list(native_type.GetInterfaces())
            declared = {str(m) for m in native_type.GetMethods() if not m.IsSpecialName}
            declared_properties = {str(p) for p in native_type.GetProperties()}
            inherited_properties = []
            inherited_methods = []
            for parent in inherited:
                for prop in parent.GetProperties():
                    inherited_properties.append(dict(interface=str(parent.FullName),signature=str(prop),can_read=bool(prop.CanRead),can_write=bool(prop.CanWrite)))
                for member in parent.GetMethods():
                    if not member.IsSpecialName:
                        inherited_methods.append(dict(interface=str(parent.FullName),signature=str(member)))
            contracts[str(native_type.FullName)] = dict(
                inherited_interfaces=sorted(str(t.FullName) for t in inherited),
                declared_methods=sorted(declared),
                declared_properties=sorted(declared_properties),
                inherited_properties=sorted(inherited_properties,key=lambda p:(p['interface'],p['signature'])),
                additional_properties=sorted({p['signature'] for p in inherited_properties}-declared_properties),
                inherited_methods=sorted(inherited_methods,key=lambda m:(m['interface'],m['signature'])),
                additional_methods=sorted({m['signature'] for m in inherited_methods}-declared),
            )
    report = dict(source='installed public assemblies; inherited interfaces included',
                  native_application_created=False,assemblies=assemblies,interfaces=contracts,
                  interfaces_with_additional_methods=[n for n,c in contracts.items() if c['additional_methods']])
    output = Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(interfaces=len(contracts),interfaces_with_additional_methods=len(report['interfaces_with_additional_methods']),output=str(output)),ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    run(parser.parse_args().output)
