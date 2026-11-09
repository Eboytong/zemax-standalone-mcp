"""Formal pupil apodization return-value probe; owns its model and state."""
import json,os,sys
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import clean
folder=Path(sys.argv[1]).resolve();folder.mkdir(parents=True,exist_ok=False)
os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
b=Backend(Config(Config.from_env().install_dir,folder/'native'))
r=dict(calls=[],values=[],error=None)
def call(name,args=None):
 result=b.dispatch(name,args or {});r['calls'].append(dict(tool=name,arguments=args,response=result))
 if not result['ok']:raise RuntimeError(result)
 return result['data']
try:
 call('connect');call('new_system')
 for factor in [0,1,2]:
  call('update_system_settings',dict(aperture_options=dict(apodization_type='Gaussian',apodization_factor=factor)))
  r['values'].append(dict(factor=factor,samples=[dict(px=x,py=y,value=float(b.system.LDE.GetApodization(x,y))) for x,y in [(0,0),(.5,0),(1,0),(.6,.8)]]))
except Exception as e:r['error']=repr(e)
finally:
 b.shutdown();receipt=folder/'state/close_receipt.json';r['close_receipt']=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
 (folder/'probe.json').write_text(json.dumps(clean(r),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(values=r['values'],error=r['error'],close=r['close_receipt']),ensure_ascii=False))
