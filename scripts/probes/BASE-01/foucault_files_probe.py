import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Serial formal Source/SaveBMP path probe, isolated from public requests."""
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = PROJECT_ROOT
sys.path.insert(0, str(ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap, dotnet_array


def run(folder):
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=False)
    image = Image.new('RGB', (64, 64), 'black')
    for y in range(64):
        for x in range(64):
            image.putpixel((x, y), (255, 255, 255) if x >= 32 else (0, 0, 0))
    source = folder/'half-plane.bmp'
    image.save(source)
    backend = Backend(Config(Config.from_env().install_dir, folder/'native'))
    record = dict(source=str(source), items=[])
    def save():
        (folder/'probe.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    try:
        record['connect'] = backend.dispatch('connect', {})
        assert record['connect']['ok'], record['connect']
        for name, args in [('new_system', {}), ('update_system_settings', dict(aperture_value=10,
                wavelengths=[dict(wavelength_um=.55)], fields=[dict(x=0,y=0)])),
                ('update_surfaces', dict(changes=[dict(surface=1,radius=-200,conic=-1,
                material='MIRROR',thickness=-100,semi_diameter=5,is_stop=True,replace_solves=True)]))]:
            response=backend.dispatch(name,args)
            assert response['ok'],response
        for data in ['Computed', 'Reference', 'Difference']:
            tool = None
            item = dict(data=data)
            record['items'].append(item)
            try:
                enum=backend.native.enum(backend.native.api.Analysis.AnalysisIDM,'Foucault')
                tool=backend.system.Analyses.New_Analysis_SettingsFirst(enum)
                settings=unwrap(tool.GetSettings())
                settings.Source=str(source)
                output=folder/(data+'.bmp')
                settings.SaveBMP=str(output)
                settings.Data=backend.native.enum(settings.Data.GetType(),data)
                item['before']=dict(Source=str(settings.Source),SaveBMP=str(settings.SaveBMP),Data=str(settings.Data))
                save()
                tool.ApplyAndWaitForCompletion()
                result=tool.GetResults()
                item['after']=dict(Source=str(settings.Source),SaveBMP=str(settings.SaveBMP),Data=str(settings.Data))
                item['messages']=[str(result.GetMessageAt(i).Text) for i in range(result.NumberOfMessages)]
                item['grids']=[dict(nx=int(result.GetDataGrid(i).Nx),ny=int(result.GetDataGrid(i).Ny),
                    values=dotnet_array(result.GetDataGrid(i).Values)) for i in range(result.NumberOfDataGrids)]
                item['output_exists']=output.is_file()
                if output.is_file():
                    with Image.open(output) as bitmap:
                        item['bitmap']=dict(size=list(bitmap.size),mode=bitmap.mode)
            except Exception as exc:
                item['error']=dict(type=type(exc).__name__,message=str(exc))
            finally:
                if tool is not None:
                    owner=dict(native=tool)
                    item['closed']=backend._close_task_native(owner)
                save()
    finally:
        record['disconnect']=backend.dispatch('disconnect',{})
        save()
    print(json.dumps(dict(path=str(folder/'probe.json'),items=[{k:v for k,v in i.items() if k!='grids'} for i in record['items']]),ensure_ascii=False))


if __name__=='__main__':
    run(sys.argv[1])
