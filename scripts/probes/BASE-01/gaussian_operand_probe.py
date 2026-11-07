import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Formal Gaussian MFE query parameters, independent of AS_Default dialogs."""
import json
import sys
from pathlib import Path

ROOT=PROJECT_ROOT;sys.path.insert(0,str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));record=dict(operands=[])
    def save():(folder/'probe.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def call(name,args=None):
        r=b.dispatch(name,args or {});assert r['ok'],r;return r['data']
    try:
        record['connect']=call('connect');call('new_system')
        call('update_system_settings',dict(aperture_value=10,wavelengths=[dict(wavelength_um=.55)],fields=[dict(x=0,y=0)]))
        call('update_surfaces',dict(changes=[dict(surface=1,thickness=100,semi_diameter=5,replace_solves=True)]))
        names=set(b.native.enum_names(b.native.api.Editors.MFE.MeritOperandType))
        record['merit_before']=call('get_merit_function')
        for name in ['GBPD','GBPP','GBPR','GBPS','GBPW','GBPZ','GBSD','GBSP','GBSR','GBSS','GBSW']:
            item=dict(name=name,available=name in names);record['operands'].append(item)
            if name not in names:continue
            enum=b.native.enum(b.native.api.Editors.MFE.MeritOperandType,name)
            count=int(b.system.MFE.NumberOfOperands);operand=b.system.MFE.AddOperand()
            try:
                operand.ChangeType(enum);headers=[]
                for number in range(1,9):
                    column=b.native.enum(b.native.api.Editors.MFE.MeritColumn,'Param'+str(number))
                    cell=operand.GetOperandCell(column)
                    headers.append(dict(number=number,header=str(cell.Header),type=str(cell.DataType),active=bool(cell.IsActive)))
                item['headers']=headers
            finally:b.system.MFE.RemoveOperandAt(count+1)
            parameters=[2,1,1.,.05,0.,1.,0.,0.] if name.startswith('GBP') else [1,2,1.,1.,0.,.05,0.,0.]
            item['parameters']=parameters
            try:item['value']=float(b.system.MFE.GetOperandValue(enum,*parameters))
            except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
            save()
        record['merit_after']=call('get_merit_function')
    finally:record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps(dict(operands=record['operands'],closed=record['disconnect']['ok']),ensure_ascii=False))


if __name__=='__main__':run(sys.argv[1])
