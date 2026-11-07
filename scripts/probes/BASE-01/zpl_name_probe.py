import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Native macro-name boundary probe with a working EvenAspheric control cell."""
import json
import sys
import uuid
from pathlib import Path

ROOT=PROJECT_ROOT;sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(items=[]);owned=[]
    def save():(folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});assert r['ok'],r;return r['data']
    try:
        record['connect']=call('connect');call('new_system')
        call('update_surfaces',dict(changes=[dict(surface=1,surface_type='EvenAspheric',replace_solves=True)]))
        directory=Path(call('get_system_resources',dict(kind='extension_files',extension_role='zpl'))['directory'])
        names=['M'+uuid.uuid4().hex[:12]+'X'*(n-13) for n in [16,20,24,28,30,31,32,33,38]]
        names+=['宏'+uuid.uuid4().hex[:6],'宏'*25+uuid.uuid4().hex[:6],'宏'*26+uuid.uuid4().hex[:6]]
        for name in names:
            path=directory/(name+'.ZPL');path.write_text('SOLVERETURN .125\n',encoding='ascii');owned.append(path)
        cell=b._cell(b._row(1),'parameter_1');mode=b.native.api.Editors.SolveType.ZPLMacro
        for name in names:
            cell.MakeSolveFixed();cell.DoubleValue=0
            solve=cell.CreateSolveType(mode);available=[str(v) for v in solve._S_ZPLMacro.GetAvailableMacros()]
            solve._S_ZPLMacro.Macro=name
            item=dict(name=name,characters=len(name),utf16_units=len(name.encode('utf-16-le'))//2,
                      cp936_bytes=len(name.encode('gbk')),listed=name in available,
                      requested_readback=str(solve._S_ZPLMacro.Macro),solve_valid=bool(solve.IsValid))
            record['items'].append(item)
            try:
                item['native_return']=str(cell.SetSolveData(solve));item['actual_solve']=str(cell.Solve)
                item['actual_value']=b._cell_value(cell)
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            save()
        cell.MakeSolveFixed()
    finally:
        record['disconnect']=b.dispatch('disconnect',{});save()
        for path in owned:path.unlink(missing_ok=True)
    print(json.dumps(record['items'],ensure_ascii=False))


if __name__=='__main__':run(sys.argv[1])
