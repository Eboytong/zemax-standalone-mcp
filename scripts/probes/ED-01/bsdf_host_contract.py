"""Compare formal LDE/NCE BSDF selectors after application-level file refresh."""
import json
import os
from pathlib import Path
import sys
ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pyproject.toml').is_file())
sys.path[:0]=[str(ROOT/'src')]
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config

def run(destination):
    folder=Path(destination).resolve();folder.mkdir(parents=True,exist_ok=False)
    os.environ['ZEMAX_STATE_DIR']=str(folder/'state')
    b=Backend(Config(Config.from_env().install_dir,folder/'native'))
    d=dict(trials=[],hypothesis='Application-level resource refresh or NCE face selector may expose files unavailable to the sequential selector')
    def call(name,args=None):
        value=b.dispatch(name,args or {})
        if not value['ok']:raise RuntimeError(value)
        return value['data']
    try:
        call('connect');d['context']=b.context()
        app=b.native.application
        d['directories']={key:str(getattr(app,key)) for key in ('ZemaxDataDir','ScatterDir','LensDir')}
        root=Path(d['directories']['ScatterDir'])
        files=sorted(root.glob('*.bsdf'))
        d['existing_bsdf']=[str(p) for p in files]
        source=next((p for p in files if p.name.casefold()=='brownvinyl.bsdf'),None)
        if source is None:raise FileNotFoundError('BrownVinyl.bsdf not in actual ScatterDir')
        d['resource']=dict(path=str(source),header=source.read_text(encoding='utf-8-sig',errors='replace').splitlines()[:12])
        for mode in ('Sequential','NonSequential'):
            call('new_system',dict(mode=mode));b.system.SaveAs(str(folder/(mode+'.zos')))
            app.UpdateFileLists();b.system.UpdateFileLists()
            if mode=='Sequential':
                row=b.system.LDE.GetSurfaceAt(1);row.Material='MIRROR'
                host=row.ScatteringData;kind=b.native.enum(b.native.api.Editors.LDE.SurfaceScatteringTypes,'BSDF')
                create=lambda:host.CreateScatteringTypeSettings(kind)
                commit=lambda setting:host.ChangeScatteringTypeSettings(setting)
                current=lambda:host.CurrentTypeSettings._S_BSDF
                fields=('FileName',)
            else:
                call('update_nsc_objects',dict(changes=[dict(object=1,object_type='RectangularVolume',material='MIRROR')]))
                row=b.system.NCE.GetObjectAt(1)
                d['face_count']=int(row.CoatScatterData.NumberOfFaces)
                host=row.CoatScatterData.GetFaceData(0)
                d['custom_settings']=bool(host.UseCustomSettings())
                kind=b.native.enum(b.native.api.Editors.NCE.ObjectScatteringTypes,'BSDF')
                create=lambda:host.CreateScatterModelSettings(kind)
                commit=lambda setting:host.ChangeScatterModelSettings(setting)
                current=lambda:host.CurrentScatterModelSettings._S_BSDF
                fields=('ReflectFile','TransmitFile')
            for route,value in [('concrete',source.name),('formal_interface',source.name)]:
                item=dict(mode=mode,requested=value,route=route);d['trials'].append(item)
                try:
                    setting=create();s=setting._S_BSDF
                    interface=(b.native.api.Editors.LDE.ISurfaceScatteringBSDF if mode=='Sequential' else b.native.api.Editors.NCE.IOSS_BSDF)
                    if route=='formal_interface':s=interface(s)
                    item['available']=[str(x) for x in s.GetAvailableFileNames()]
                    for field in fields:setattr(s,field,value)
                    item['setter_readback']={field:str(getattr(s,field)) for field in fields}
                    item['commit']=bool(commit(setting))
                    active=current()
                    if route=='formal_interface':active=interface(active)
                    item['active']={field:str(getattr(active,field)) for field in fields}
                    item['active_files']=[str(x) for x in active.GetAvailableFileNames()]
                except Exception as exc:item['error']=dict(type=type(exc).__name__,message=str(exc))
    except Exception as exc:d['error']=dict(type=type(exc).__name__,message=str(exc))
    finally:
        b.shutdown();receipt=folder/'state/close_receipt.json'
        d['close_receipt']=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else None
        (folder/'probe.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(d,ensure_ascii=False))
    return d

if __name__=='__main__':
    result=run(sys.argv[1])
    if result.get('error'):sys.exit(1)
