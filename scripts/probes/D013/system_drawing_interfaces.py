"""Inspect the installed formal drawing interfaces without creating an application."""
import json
from datetime import datetime,timezone
from pathlib import Path
from pythonnet import load

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
INSTALL=Path('C:/Program Files/ANSYS Inc/v242/Zemax OpticStudio')
load('netfx')
from System.Reflection import Assembly
from System.Diagnostics import FileVersionInfo

terms=('systemdrawing','unfold','exportaspng','exportaspdf','exportasemf')
assemblies=[]
for name in ['ZOSAPI_Interfaces.dll','ZOSAPI.dll']:
    path=INSTALL/name
    assembly=Assembly.LoadFrom(str(path))
    matches=[];types=assembly.GetTypes()
    for t in types:
        if any(term in str(t.FullName).lower() for term in terms):
            matches.append(dict(type=str(t.FullName),member=None))
        for member in t.GetMembers():
            if any(term in str(member.Name).lower() for term in terms):
                matches.append(dict(type=str(t.FullName),member=str(member)))
    assemblies.append(dict(path=str(path),identity=str(assembly.FullName),public_type_count=sum(bool(t.IsPublic) for t in types),matches=matches))
a=Assembly.LoadFrom(str(INSTALL/'ZOSAPI_Interfaces.dll'))
selected={}
for name in ['ZOSAPI.Analysis.I_Analyses','ZOSAPI.Analysis.Data.IAR_',
             'ZOSAPI.Tools.Layouts.ICrossSectionExport','ZOSAPI.Tools.Layouts.I3DViewerExport']:
    t=a.GetType(name)
    selected[name]=None if t is None else [str(m) for m in t.GetMembers()]
result=dict(checked_at=datetime.now(timezone.utc).isoformat(),installed_exe_version=FileVersionInfo.GetVersionInfo(str(INSTALL/'OpticStudio.exe')).FileVersion,
    computation='public .NET reflection; no optical application or license checkout',assemblies=assemblies,interfaces=selected,
    application_created=False,state='formal_members_missing' if not any(a['matches'] for a in assemblies) else 'members_require_review')
folder=ROOT/'.local/evidence/development/D013';folder.mkdir(parents=True,exist_ok=True)
path=folder/'interface-recheck.json';path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(state=result['state'],version=result['installed_exe_version'],matches=sum(len(a['matches']) for a in assemblies),evidence=str(path))))
