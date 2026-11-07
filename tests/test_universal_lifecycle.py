"""Exercise Universal adapters through the real task state machine with fault injection."""
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import TaskResult
from zemax_mcp.errors import ZemaxError
from zemax_mcp import universal,universal_grid


def harness(tmp_path,monkeypatch,dimensions):
    counts=dict(close=0,copy_close=0,wait=0)
    header=('Independent Variable X: Thickness mm Surface 1\nDependent Variable Y: TTHI, Surf1=1, Surf2=2\nX Y\n2 6\n3 7\n4 8\n')
    if dimensions==2:
        header=('Independent Variable X: Thickness mm Surface 1\nIndependent Variable Y: Thickness mm Surface 2\nDependent Variable Z: TTHI, Surf1=1, Surf2=2\nX - Range: 2 - 4\nX - Sampling: 3\nY - Range: 3 - 5\nY - Sampling: 2\n')
    class Tool:
        running=False;report=header;reject=False;close_fail=False;apply_fail=False
        def GetSettings(self):return NS(SaveTo=lambda p:True,ModifySettings=lambda *a:not self.reject,LoadFrom=lambda p:True)
        def Apply(self):
            if self.apply_fail:raise RuntimeError('injected Apply failure')
            self.running=True
        def IsRunning(self):return self.running
        def WaitForCompletion(self):
            assert not self.running
            counts['wait']+=1
        def Terminate(self):self.running=False
        def Close(self):
            assert not self.running
            counts['close']+=1
            return not self.close_fail
        def GetResults(self):
            def export(path):Path(path).write_text(self.report,encoding='utf-16');return True
            grid=NS(Nx=3,Ny=2,MinX=2,MinY=3,Dx=1,Dy=2,Values=[[5,6,7],[7,8,9]])
            return NS(IsValid=True,GetTextFile=export,NumberOfDataGrids=1,GetDataGrid=lambda i:grid)
    tool=Tool()
    def close_copy(save):counts['copy_close']+=1;return True
    source=NS(Mode='Sequential',SystemID=17,MCE=NS(CurrentConfiguration=1),SystemData=NS(Units=NS(LensUnits='Millimeters')),CopySystem=lambda:NS(SystemID=18,Close=close_copy))
    b=Backend(Config(tmp_path,tmp_path),native=NS(system=source));b.directory=tmp_path
    b._row=lambda i:None;b.context=lambda:dict(checkpoint=None,model_revision=b.revision)
    b.get_system_settings=lambda req:{};b._record_task_history=lambda task:None
    module=universal if dimensions==1 else universal_grid
    monkeypatch.setattr(module,'new_analysis',lambda *a:tool)
    if dimensions==2:monkeypatch.setattr(module,'dotnet_array',lambda array:array)
    q=(universal.UniversalPlot1D(kind='universal_plot_1d',surface=1,start=2,stop=4,samples=3,first_surface=1,last_surface=2)if dimensions==1 else universal_grid.UniversalPlot2D(kind='universal_plot_2d',x=dict(surface=1,start=2,stop=4,samples=3),y=dict(surface=2,start=3,stop=5,samples=2),first_surface=1,last_surface=2))
    return b,tool,counts,module,q


@pytest.mark.parametrize('dimensions',[1,2])
@pytest.mark.parametrize('failure',['cancel','native_report','parse','close','apply','settings'])
def test_terminal_outcomes_release_owned_resources(tmp_path,monkeypatch,dimensions,failure):
    b,tool,counts,module,q=harness(tmp_path,monkeypatch,dimensions)
    if failure=='settings':
        tool.reject=True
        with pytest.raises(ZemaxError)as error:module.run(b,q)
        assert error.value.code=='SETTING_REJECTED'and b.active is None
    elif failure=='apply':
        tool.apply_fail=True
        with pytest.raises(ZemaxError)as error:module.run(b,q)
        assert error.value.code=='TASK_START_FAILED'and b.active is None
    else:
        state=module.run(b,q);task=b.tasks[state['task_id']]
        if failure=='cancel':b.cancel_task(TaskResult(task_id=state['task_id']))
        else:
            if failure=='native_report':tool.report='某些操作数不能计算!'
            if failure=='parse':tool.report=tool.report.replace('Surface 1','Surface 9')
            if failure=='close':tool.close_fail=True
            tool.running=False;b.tick()
        expected='cancelled'if failure=='cancel'else'failed'
        assert task['state']==expected and task['close_attempted']and b.active is None
        if failure!='cancel':
            assert task['error']['code']=={'native_report':'ANALYSIS_FAILED','parse':'SETTING_REJECTED','close':'CLEANUP_FAILED'}[failure]
    assert counts['close']==1
    assert counts['copy_close']==(1 if dimensions==1 else 0)
    assert b.requires_reconnect==(failure=='close')and b.revision==0


@pytest.mark.parametrize('dimensions',[1,2])
def test_calculation_failure_allows_following_analysis(tmp_path,monkeypatch,dimensions):
    b,tool,counts,module,q=harness(tmp_path,monkeypatch,dimensions)
    original=tool.report;tool.report='某些操作数不能计算!'
    state=module.run(b,q);tool.running=False;b.tick()
    assert b.tasks[state['task_id']]['state']=='failed'and not b.requires_reconnect
    tool.report=original
    state=module.run(b,q);tool.running=False;b.tick()
    assert b.tasks[state['task_id']]['state']=='succeeded'and b.active is None
    assert counts['close']==2 and b.revision==0
