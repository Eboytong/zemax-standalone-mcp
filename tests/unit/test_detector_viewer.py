from enum import IntEnum
from types import SimpleNamespace as NS

import pytest
from pydantic import ValidationError

from zemax_mcp.analysis_models import RunAnalysis
from zemax_mcp.detector_viewer import DetectorViewer, run_detector_viewer
from zemax_mcp.errors import ZemaxError


@pytest.mark.parametrize('patch', [dict(source='zrd'), dict(path='input.zrd'), dict(filter='H2'),
    dict(smoothing=11),dict(smoothing=-1),dict(smoothing=True),dict(scale='Log'),dict(detector=0),dict(row_col=-1)])
def test_invalid_viewer_contract(patch):
    with pytest.raises(ValidationError):
        RunAnalysis(request=dict(kind='detector_viewer',detector=2)|patch)


def fake_backend(monkeypatch, *, valid=True, ignored=None):
    class Scale(IntEnum):
        Linear=0
        Normalized=1
        Log_Minus_5=1
    class Data(IntEnum):
        IncoherentIrradiance=0
    class Show(IntEnum):
        FalseColor=2
    class Settings:
        def __init__(self):
            self.Scale=Scale.Linear; self.DataType=Data.IncoherentIrradiance;self.ShowAs=Show.FalseColor
            self.RayDatabaseFilename='OLD.ZRD';self.Filter='OLD';self.Smoothing=0;self.RowCol=0
            self.number=0
            self.Detector=NS(SetDetectorNumber=lambda i:setattr(self,'number',i),GetDetectorNumber=lambda:self.number)
        def __setattr__(self,key,value):
            if key != ignored or key not in self.__dict__:object.__setattr__(self,key,value)
        def GetType(self):return NS(GetProperty=lambda key:NS(PropertyType={'Scale':Scale,'DataType':Data,'ShowAs':Show}[key]))
        def IsValidDetector(self,i):return valid
    settings=Settings();closed=[];started=[]
    native=NS(api=NS(Analysis=NS(AnalysisIDM=NS(DetectorViewer='viewer'))))
    native.enum=lambda kind,value:kind[value]
    native.set_enum=lambda obj,key,value:setattr(obj,key,native.enum(obj.GetType().GetProperty(key).PropertyType,value))
    tool=NS(GetSettings=lambda:settings)
    b=NS(_require_nsc=lambda:None,_object=lambda i:None,native=native,
         system=NS(Analyses=NS(New_Analysis=lambda _:tool)),_release_owned=lambda _:closed.append(True),
         _collect_general_analysis=lambda task, **kwargs:dict(grids=[dict(nx=2,ny=2,values=[[0,1],[2,3]])],native_preamble=[]))
    def start(kind,tool,actual,**kwargs):
        started.append(actual)
        return kwargs['collector'](dict(settings=actual))
    b._start_task=start
    monkeypatch.setattr('zemax_mcp.analyses.scalar_settings',lambda _:dict(Scale=str(settings.Scale)))
    return b,settings,closed,started


def test_current_viewer_clears_zrd_filter_and_checks_enum_alias(monkeypatch):
    b,s,closed,started=fake_backend(monkeypatch)
    result=run_detector_viewer(b,DetectorViewer(kind='detector_viewer',detector=2,scale='Log_Minus_5',smoothing=2))
    assert s.Filter == '' and s.RayDatabaseFilename == '' and s.Smoothing == 2
    assert result['detector_viewer']['source'] == 'current_detector'
    assert result['grids'][0]['array_order'].startswith('values[y][x]')
    assert len(started)==1 and not closed


@pytest.mark.parametrize('ignored', ['Filter','RayDatabaseFilename','Smoothing','Scale'])
def test_rejected_viewer_setting_closes_before_start(monkeypatch,ignored):
    b,s,closed,started=fake_backend(monkeypatch,ignored=ignored)
    with pytest.raises(ZemaxError) as error:
        run_detector_viewer(b,DetectorViewer(kind='detector_viewer',detector=2,smoothing=2,scale='Log_Minus_5'))
    assert error.value.code=='SETTING_REJECTED' and closed==[True] and not started


def test_non_detector_rejected_and_closed(monkeypatch):
    b,s,closed,started=fake_backend(monkeypatch,valid=False)
    with pytest.raises(ZemaxError) as error:
        run_detector_viewer(b,DetectorViewer(kind='detector_viewer',detector=1))
    assert error.value.code=='INVALID_DETECTOR' and closed==[True] and not started


def test_native_empty_result_keeps_export_error_and_messages():
    from zemax_mcp.detector_viewer import collect_detector_result
    def export(task, **kwargs):
        assert kwargs == dict(optional_native_text=True)
        return dict(grids=[],series=[],structured_data_available=False,
                    native_export_error='native text missing')
    result=collect_detector_result(NS(_collect_general_analysis=export),{})
    assert result['empty_result'] and 'native text missing' in result['native_export_error']


def test_native_calculation_error_preserved():
    from zemax_mcp.detector_viewer import collect_detector_result
    def export(task, **kwargs):raise ZemaxError('ANALYSIS_FAILED','native failure')
    with pytest.raises(ZemaxError,match='native failure'):
        collect_detector_result(NS(_collect_general_analysis=export),{})


def test_missing_text_keeps_native_grid_and_default_export_error(tmp_path,monkeypatch):
    monkeypatch.setattr("zemax_mcp.analyses.dotnet_array",lambda value:value)
    from zemax_mcp.analyses import AnalysesMixin
    grid=NS(Values=[[0.,0.]],Nx=2,Ny=1,Dx=1.,Dy=1.,MinX=-1.,MinY=-.5,
            Description='detector',XLabel='X',YLabel='Y',ValueLabel='Irradiance')
    result=NS(IsValid=True,HeaderData=None,NumberOfMessages=0,NumberOfDataSeries=0,
              NumberOfDataGrids=1,GetDataGrid=lambda _:grid,GetTextFile=lambda _:True)
    b=NS(directory=tmp_path)
    task=dict(task_id='empty',native=NS(GetResults=lambda:result))
    with pytest.raises(FileNotFoundError):
        AnalysesMixin._collect_general_analysis(b,task)
    data=AnalysesMixin._collect_general_analysis(b,task,optional_native_text=True)
    assert data['grids'][0]['values']==[[0.,0.]] and not data['native_text_exported']
    assert not data['artifacts']
