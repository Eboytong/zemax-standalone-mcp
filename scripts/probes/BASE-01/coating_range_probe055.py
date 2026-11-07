import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
from zemax_mcp.config import PROJECT_ROOT
"""Compare formal RTA wavelength settings and actual executed scan extents."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(PROJECT_ROOT/'src'))
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.data import unwrap,dotnet_array
from zemax_mcp.coatings import configure
from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.imaging import new_analysis
from zemax_mcp.analyses import scalar_settings


def run(folder):
    folder=Path(folder).resolve();folder.mkdir(exist_ok=False,parents=True)
    b=Backend(Config(Config.from_env().install_dir,folder/'native'));report=dict(calls=[],cases=[])
    def save():(folder/'probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    def call(name,**arguments):
        r=b.dispatch(name,arguments);report['calls'].append(dict(name=name,arguments=arguments,response=r));save();assert r['ok'],r
    try:
        call('connect');call('new_system');call('insert_surfaces',at=1)
        for waves in [[.55],[.45,.55,.7]]:
            call('update_system_settings',wavelengths=[dict(wavelength_um=w)for w in waves])
            for kind,ident in [('reflection_vs_wavelength','ReflectionvsWavelength'),('phase_vs_wavelength','PhasevsWavelength')]:
                tool=new_analysis(b,ident);case=dict(wavelengths=waves,kind=kind);report['cases'].append(case)
                try:
                    settings=unwrap(tool.GetSettings());case['runtime_type']=str(settings.GetType().FullName)
                    q=RunAnalysis(request=dict(kind=kind,surface=1,minimum_wavelength_um=.45,maximum_wavelength_um=.7)).request
                    case['before']=configure(b,settings,q)
                    tool.ApplyAndWaitForCompletion()
                    case['after']=scalar_settings(unwrap(tool.GetSettings()))
                    results=unwrap(tool.GetResults());curve=results.GetDataSeries(0);x=dotnet_array(curve.XData.Data)
                    case['actual_scan']=[min(x),max(x)];case['native_text']=bool(results.GetTextFile(str(folder/(kind+str(len(waves))+'.txt'))))
                    case['configured_again']=configure(b,unwrap(tool.GetSettings()),q)
                    tool.ApplyAndWaitForCompletion()
                    case['after_second']=scalar_settings(unwrap(tool.GetSettings()))
                    x=dotnet_array(unwrap(tool.GetResults()).GetDataSeries(0).XData.Data)
                    case['second_scan']=[min(x),max(x)]
                finally:case['closed']=b._close_task_native(dict(native=tool));save()
    finally:report['disconnect']=b.dispatch('disconnect',{});save()

if __name__=='__main__':run(sys.argv[1])
