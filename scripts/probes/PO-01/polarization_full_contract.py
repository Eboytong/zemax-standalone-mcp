"""Inspect named public polarization outputs without starting OpticStudio."""
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'pyproject.toml').is_file())
sys.path.insert(0, str(ROOT / 'src'))


def run(folder):
    from pythonnet import load
    load('netfx')
    import clr
    from System.Reflection import Assembly
    from zemax_mcp.config import Config

    path = Config.from_env().install_dir / 'ZOSAPI_Interfaces.dll'
    clr.AddReference(str(path))
    assembly = Assembly.LoadFrom(str(path))
    result = dict(application_created=False, assembly=str(assembly.FullName), contracts=[])
    for typ in assembly.GetExportedTypes():
        name = str(typ.FullName)
        selected = any(s in name for s in (
            'RayTrace.IRayTraceNormPolData', 'RayTrace.IRayTraceDirectPolData',
            'RayTrace.IBatchRayTrace', 'IAS_PolarizationRayTrace',
            'ILensDataEditor', 'ILDECoating', 'IAR_RayTrace',
            'Polarization', 'IAS_SingleRayTrace', 'IAR_SingleRayTrace',
        )) or any(str(p.Name) in ('GlobalCoordinates', 'PropagationPhase', 'InternalAbsorption')
                  for p in typ.GetProperties())
        if not selected:
            continue
        methods = []
        for method in typ.GetMethods():
            if method.IsSpecialName:
                continue
            methods.append(dict(name=str(method.Name), returns=str(method.ReturnType),
                parameters=[dict(name=str(p.Name), type=str(p.ParameterType),
                                 is_out=bool(p.IsOut), is_in=bool(p.IsIn))
                            for p in method.GetParameters()]))
        result['contracts'].append(dict(type=name,
            properties=[dict(name=str(p.Name), type=str(p.PropertyType), writable=bool(p.CanWrite))
                        for p in typ.GetProperties()], methods=methods,
            parents=[str(p.FullName) for p in typ.GetInterfaces()]))
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / 'contracts.json'
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(output=str(output), types=[c['type'] for c in result['contracts']],
                         application_created=False), ensure_ascii=False))


if __name__ == '__main__':
    run(sys.argv[1])
