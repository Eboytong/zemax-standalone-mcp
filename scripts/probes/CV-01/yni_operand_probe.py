"""Compare formal YNIP(Surf, Wave) with the native YNI report."""
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0] = [str(ROOT/'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config


def main():
    folder = ROOT/'.local/evidence/development/CV-01'/('yni-operand-'+uuid.uuid4().hex[:10])
    folder.mkdir(parents=True)
    b = Backend(Config(Config.from_env().install_dir, folder/'native'))
    record = {}
    def call(name, args=None):
        response = b.dispatch(name,args or {})
        record.setdefault('calls',[]).append(dict(tool=name,args=args,response=response))
        assert response['ok'],response
        return response['data']
    try:
        call('connect')
        call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        record['system_settings'] = call('get_system_settings')
        task = call('run_analysis',dict(request=dict(kind='yni_contributions')))
        deadline=time.monotonic()+60
        while task['state'] not in ('succeeded','failed','cancelled'):
            assert time.monotonic()<deadline
            b.tick()
            task=call('get_task_status',dict(task_id=task['task_id']))
        record['report']=b._full_result(task['task_id'])
        code=b.native.enum(b.native.api.Editors.MFE.MeritOperandType,'YNIP')
        record['operands']=[dict(surface=s,wavelength=w,value=float(b.system.MFE.GetOperandValue(code,s,w,0.,0.,0.,0.,0.,0.)))
            for w in range(1,b.system.SystemData.Wavelengths.NumberOfWavelengths+1)
            for s in range(1,b.system.LDE.NumberOfSurfaces-1)]
    finally:
        record['disconnect']=b.dispatch('disconnect',{})
        (folder/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        print(folder,flush=True)


if __name__=='__main__':
    main()
