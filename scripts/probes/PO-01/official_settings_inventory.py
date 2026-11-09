"""Enumerate exported installed API contracts without creating an application."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path.insert(0, str(ROOT/'src'))


def run(output, tokens=None):
    from zemax_mcp.config import Config
    from pythonnet import load
    load('netfx')
    import clr
    from System.Reflection import Assembly
    install = Config.from_env().install_dir
    dll = install/'ZOSAPI_Interfaces.dll'
    clr.AddReference(str(dll))
    assembly = Assembly.LoadFrom(str(dll))
    types = list(assembly.GetExportedTypes())
    matched = []
    settings = []
    tokens = tokens or ('phaseaberration', 'fibercoupling', 'transmission', 'polarizationraytrace',
              'glassmap', 'athermal', 'dispersion', 'gradium', 'grinprofile')
    for t in types:
        name = str(t.FullName)
        if '.Analysis.Settings' in name:
            settings.append(name)
        if not any(token in name.lower() for token in tokens):
            continue
        entry = dict(name=name, is_enum=bool(t.IsEnum))
        if t.IsEnum:
            entry['names'] = [str(x) for x in t.GetEnumNames()]
        else:
            entry['properties'] = [dict(name=str(x.Name), type=str(x.PropertyType.FullName),
                                         can_read=bool(x.CanRead), can_write=bool(x.CanWrite))
                                   for x in t.GetProperties()]
            entry['methods'] = [str(x) for x in t.GetMethods()
                                if not str(x.Name).startswith(('get_', 'set_'))]
        matched.append(entry)
    result = dict(checked_at=datetime.now(timezone.utc).isoformat(), assembly_path=str(dll),
                  assembly_identity=str(assembly.FullName), source_root=str(ROOT),
                  application_created=False, exported_type_count=len(types),
                  settings_types=settings, token_matches=matched,
                  interpretation='Exported interface-name matches only; combine with runtime settings and official help. Absence of a named interface does not enumerate every possible official route.')
    target=Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(output=str(target), exported_types=len(types), settings_types=len(settings),
                          matched_types=[x['name'] for x in matched]),ensure_ascii=False))


if __name__ == '__main__':
    run(sys.argv[1], tuple(token.lower() for token in sys.argv[2:]) or None)
