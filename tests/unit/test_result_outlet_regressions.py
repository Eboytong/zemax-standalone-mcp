"""Native null-label and indexed-table shapes observed in outlets265."""
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from zemax_mcp.analyses import AnalysesMixin
from zemax_mcp.imaging import fft_spread_text_series
from zemax_mcp.errors import ZemaxError
from zemax_mcp.analysis_models import RunAnalysis


class Vector:
    Rank=1
    def __iter__(self):return iter([0.,1.])


class Matrix:
    Rank=2
    def GetLength(self,index):return [2,1][index]
    def __getitem__(self,index):return [.2,.4][index[0]]


def collect(tmp_path,labels):
    series=NS(XData=NS(Data=Vector()),YData=NS(Data=Matrix()),SeriesLabels=labels,Description='',XLabel='native position')
    def export(path):Path(path).write_text('native report',encoding='utf-16');return True
    result=NS(IsValid=True,HeaderData=NS(Lines=None),NumberOfMessages=0,GetTextFile=export,
        NumberOfDataSeries=1,GetDataSeries=lambda _:series,NumberOfDataGrids=0)
    return AnalysesMixin._collect_general_analysis(NS(directory=tmp_path),dict(task_id='native',native=NS(GetResults=lambda:result),
        settings=dict(kind='foucault',requested=RunAnalysis(request=dict(kind='foucault')).request.model_dump())))


def test_null_native_labels_preserve_values_and_column_identity(tmp_path):
    result=collect(tmp_path,None)
    assert result['native_header']==[]
    series=result['series'][0]
    assert series['labels']==['column_1'] and series['y']==[[.2],[.4]]
    assert series['labels_source'].startswith('generated column indices')


def test_native_label_dimension_conflict_is_reported(tmp_path):
    with pytest.raises(ZemaxError) as caught:collect(tmp_path,['a','b'])
    assert caught.value.code=='INVALID_RESULT_DATA'


@pytest.mark.parametrize('title',['FFT 线扩散函数列表','FFT 边扩散函数列表','FFT 边缘扩散函数列表','FFT Line Spread Function','FFT Edge Spread Function'])
def test_fft_spread_text_preserves_positions_and_native_normalization(title):
    r=fft_spread_text_series(title+'\n0 -1.2 .2\n1 0.0 1.0\n2 1.2 .2',dict(data_type='Y_Linear',spread='Edge'))
    assert r['x']==[-1.2,0,1.2] and r['y']==[[.2],[1.],[.2]]
    assert r['x_unit']=='micrometers' and r['value_units']==['relative intensity']
    assert r['orientation']=='Y' and r['labels']==['Y_Linear']


@pytest.mark.parametrize('text',['other report\n0 -1 .2\n1 0 1', 'FFT Line Spread\n0 -1 .2\n2 0 1','FFT Line Spread\n0 0 .2\n1 -1 1'])
def test_fft_spread_requires_title_contiguous_indices_and_monotonic_positions(text):
    assert fft_spread_text_series(text,{}) is None


@pytest.mark.parametrize('suffix,unit', [('Linear','relative intensity'),('Logarithmic','relative intensity'),
                                       ('Phase','degrees'),('RealPart','relative amplitude'),('ImaginaryPart','relative amplitude')])
def test_fft_spread_units_and_perpendicular_scan(suffix,unit):
    result=fft_spread_text_series('FFT 线扩散函数列表\n方位值在Y 方向.\n0 -1 .2\n1 0 1',
                                  dict(data_type='X_'+suffix))
    assert result['value_units']==[unit] and result['scan_axis']=='Y'
    assert result['scan_axis_source']=='native text'
    assert result['logarithmic_display']==(suffix=='Logarithmic')


def test_fft_spread_native_orientation_conflict_preserves_axis():
    with pytest.raises(ZemaxError) as error:
        fft_spread_text_series('FFT 边缘扩散函数列表\n方位值在X 方向.\n0 -1 .2\n1 0 1',dict(data_type='X_Linear'))
    assert error.value.code=='INVALID_RESULT_DATA' and error.value.details['native_scan_axis']=='X'


def test_geometric_spread_column_identity_comes_from_native_header():
    from zemax_mcp.imaging import describe_geometric_spread
    series=dict(labels=['None']*4,x=[0],y=[[1,.5,1,.5]])
    result=describe_geometric_spread(dict(series=[series]),'X-方向 Y-方向\n位置 LSF ERF LSF ERF',dict(data_type='Edge'))
    assert result['series'][0]['labels']==['X_LSF','X_ESF','Y_LSF','Y_ESF']
    assert series['native_labels']==['None']*4 and series['position_reference']=='chief ray'
    assert series['value_units']==['relative intensity','fraction','relative intensity','fraction']


@pytest.mark.parametrize('text,y',[('other header',[[1,2,3,4]]),('X Y\nLSF ERF LSF ERF',[[1,2]])])
def test_geometric_spread_unknown_columns_rejected(text,y):
    from zemax_mcp.imaging import describe_geometric_spread
    with pytest.raises(ZemaxError) as error:
        describe_geometric_spread(dict(series=[dict(labels=['None']*4,y=y)]),text,dict(data_type='Line'))
    assert error.value.code=='INVALID_RESULT_DATA'
