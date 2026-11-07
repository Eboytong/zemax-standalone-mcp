import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Inspect formal POWF/POWP argument identities and native control values."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(folder):
 folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
 b=Backend(Config(Config.from_env().install_dir,folder/'native'));r=dict(operands=[])
 def save():(folder/'probe.json').write_text(json.dumps(r,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
 def call(name,args=None):
  r['stage']=name;save();v=b.dispatch(name,args or {});assert v['ok'],v;return v['data']
 try:
  call('connect');call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
  r['before']=call('get_merit_function')
  for name in ['POWF','POWP']:
   code=b.native.enum(b.native.api.Editors.MFE.MeritOperandType,name);item=dict(name=name,headers=[],queries=[]);r['operands'].append(item)
   n=int(b.system.MFE.NumberOfOperands);operand=b.system.MFE.AddOperand()
   try:
    operand.ChangeType(code)
    for i in range(1,9):
     cell=operand.GetOperandCell(b.native.enum(b.native.api.Editors.MFE.MeritColumn,'Param'+str(i)))
     item['headers'].append(dict(number=i,header=str(cell.Header),type=str(cell.DataType),active=bool(cell.IsActive)))
   finally:b.system.MFE.RemoveOperandAt(n+1)
   save()
  r['after']=call('get_merit_function')
 except Exception as exc:r['error']=dict(type=type(exc).__name__,message=str(exc))
 finally:r['disconnect']=b.dispatch('disconnect',{});r['stage']='closed';save()
 print(json.dumps(r['operands'],ensure_ascii=False))
if __name__=='__main__':run(sys.argv[1])
