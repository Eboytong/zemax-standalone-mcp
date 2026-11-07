import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Separate formal ReferenceToPrimary from the current-wave OPD reference."""
import json
import sys
from pathlib import Path

import numpy as np
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap, dotnet_array
from zemax_mcp.imaging import new_analysis
from zemax_mcp.analyses import scalar_settings


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    backend=Backend(Config(Config.from_env().install_dir,folder/'native'))
    output=dict(hypothesis='QuickYield non-primary mismatch comes from primary-wavelength reference sphere',
        records=[],tolerance='1e-5waves+1%reference; unchanged',native_quick_yield_standard=.24512342752844274,
        native_quick_yield_very_high=.24567772661945006)
    def call(name,args=None):
        result=backend.dispatch(name,args or {})
        output.setdefault('calls',[]).append(dict(tool=name,args=args,response=result))
        assert result['ok'],result
        return result['data']
    try:
        call('connect');call('open_lens',dict(path=str(Path.home()/'Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos')))
        baseline=call('get_surfaces');settings=call('get_system_settings')
        output['conditions']=dict(system_settings=settings,field=1,wavelength=1,sampling='S_256x256',
            coordinates='strict circle on entrance guard nodes (i-128)/127',reference='population RMS after removing piston')
        for primary in [False,True]:
            tool=new_analysis(backend,'WavefrontMap');record=dict(reference_to_primary=primary);output['records'].append(record)
            try:
                s=unwrap(tool.GetSettings());s.Field.SetFieldNumber(1);s.Wavelength.SetWavelengthNumber(1)
                backend.native.set_enum(s,'Sampling','S_256x256')
                s.UseExitPupil=False;s.RemoveTilt=False;s.ReferenceToPrimary=primary
                record['actual_settings']=scalar_settings(s)
                assert bool(s.ReferenceToPrimary)==primary
                tool.ApplyAndWaitForCompletion();result=unwrap(tool.GetResults())
                record['result_valid']=bool(result.IsValid)
                record['native_messages']=[str(result.GetMessageAt(i).Text)for i in range(result.NumberOfMessages)]
                assert result.IsValid and result.NumberOfDataGrids==1
                grid=result.GetDataGrid(0);values=np.asarray(dotnet_array(grid.Values),dtype=float)
                ny,nx=values.shape;x=(np.arange(nx)-nx//2)/(nx//2-1);y=(np.arange(ny)-ny//2)/(ny//2-1)
                pupil=values[(x[None,:]**2+y[:,None]**2)<1]
                assert len(pupil)>0 and np.all(np.isfinite(pupil))
                record.update(values=values.tolist(),sample_count=len(pupil),mean_waves=float(pupil.mean()),
                    rms_waves=float(pupil.std()),standard_difference=abs(float(pupil.std())-output['native_quick_yield_standard']))
                record['text_exported']=bool(result.GetTextFile(str(folder/('primary'+str(primary)+'.txt'))))
            finally:
                owner=dict(native=tool);record['closed']=backend._close_task_native(owner);record['cleanup_warnings']=owner.get('cleanup_warnings')
        output['surfaces_preserved']=call('get_surfaces')==baseline
        output['settings_preserved']=call('get_system_settings')==settings
    finally:
        output['disconnect']=backend.dispatch('disconnect',{})
        (folder/'probe.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(records=[{k:r.get(k)for k in ['reference_to_primary','rms_waves','standard_difference','closed']}for r in output['records']],disconnect=output['disconnect']['ok'])))


if __name__=='__main__':run(sys.argv[1])
