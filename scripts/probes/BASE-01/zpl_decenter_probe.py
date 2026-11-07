import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Formal native setter controls for parameter-nine/ten macro adoption."""
import json
import sys
import uuid
from pathlib import Path

ROOT=PROJECT_ROOT
sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record=dict(items=[]);macro=None
    def save():
        (folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        response=backend.dispatch(name,args or {})
        assert response['ok'],response
        return response['data']
    try:
        record['connect']=call('connect')
        directory=call('get_system_resources',dict(kind='extension_files',extension_role='zpl'))['directory']
        macro=Path(directory)/('M'+uuid.uuid4().hex[:12]+'.ZPL');macro.write_text('SOLVERETURN .125\n',encoding='ascii')
        grid=folder/'grid.dat';grid.write_text('5 5 1 1 0\n'+('0 0 0 0\n'*25),encoding='ascii')
        for surface_type,cells in [('EvenAspheric',[1]),('GridSag',[1,9,10]),('ZernikeStandardSag',[9,10])]:
            item=dict(surface_type=surface_type,cells=[]);record['items'].append(item)
            try:
                call('new_system')
                call('update_surfaces',dict(changes=[dict(surface=1,surface_type=surface_type,replace_solves=True)]))
                if surface_type=='GridSag':call('update_surfaces',dict(changes=[dict(surface=1,import_file=str(grid),replace_solves=True)]))
                if surface_type!='EvenAspheric':
                    call('update_surfaces',dict(changes=[dict(surface=1,parameters={'13':4},replace_solves=True)]))
                    call('update_surfaces',dict(changes=[dict(surface=1,parameters={'14':10,'15':.1,'16':.01},replace_solves=True)]))
                for number in cells:
                    cell=backend._cell(backend._row(1),'parameter_'+str(number))
                    mode=backend.native.api.Editors.SolveType.ZPLMacro
                    data=cell.CreateSolveType(mode);data._S_ZPLMacro.Macro=macro.stem
                    row=dict(parameter=number,header=str(cell.Header),active=bool(cell.IsActive),
                             read_only=bool(cell.IsReadOnly),supported=bool(cell.IsSolveTypeSupported(mode)),
                             available=[str(v) for v in cell.GetAvailableSolveTypes()],
                             request_macro=str(data._S_ZPLMacro.Macro),solve_valid=bool(data.IsValid))
                    item['cells'].append(row)
                    row['variable_return']=bool(cell.MakeSolveVariable());row['variable_actual']=str(cell.Solve)
                    cell.MakeSolveFixed()
                    status=cell.SetSolveData(data)
                    row.update(macro_return=str(status),macro_actual=str(cell.Solve),value=backend._cell_value(cell))
                    actual=cell.GetSolveData()
                    row['returned_solve_type']=str(actual.Type) if hasattr(actual,'Type') else str(cell.Solve)
                    if str(cell.Solve)=='ZPLMacro':row['returned_macro']=str(actual._S_ZPLMacro.Macro)
                    cell.MakeSolveFixed()
                    cell.DoubleValue=.25
                    row['fixed_value']=backend._cell_value(cell)
                    save()
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            save()
    finally:
        record['disconnect']=backend.dispatch('disconnect',{});save()
        if macro is not None:macro.unlink(missing_ok=True)
    print(json.dumps(dict(items=record['items'],disconnect=record['disconnect']['ok']),ensure_ascii=False))


if __name__=='__main__':run(sys.argv[1])
