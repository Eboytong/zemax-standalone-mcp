"""Inspect formal DSAG/DSLP operand cells on an owned model copy."""
import json,sys
from pathlib import Path
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(output):
    folder=Path(output).resolve();folder.mkdir(parents=True,exist_ok=False)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    record={};copy=None
    def save():(folder/'metadata.json').write_text(json.dumps(record,indent=2,default=str)+'\n',encoding='utf-8')
    try:
        record['connect']=b.dispatch('connect',{});assert record['connect']['ok']
        record['new']=b.dispatch('new_system',{});assert record['new']['ok']
        copy=b.system.CopySystem()
        for name in ['DSAG','DSLP']:
            row=copy.MFE.AddOperand();row.ChangeType(b.native.enum(b.native.api.Editors.MFE.MeritOperandType,name))
            record[name]=[dict(column=i,header=str(row.GetCellAt(i).Header),active=bool(row.GetCellAt(i).IsActive),data_type=str(row.GetCellAt(i).DataType))for i in range(2,10)]
            save()
    finally:
        if copy is not None:copy.Close(False);record['copy_closed']=True
        record['disconnect']=b.dispatch('disconnect',{});save()
    print(json.dumps({k:record[k]for k in ['DSAG','DSLP','copy_closed']}))

if __name__=='__main__':run(sys.argv[1])
