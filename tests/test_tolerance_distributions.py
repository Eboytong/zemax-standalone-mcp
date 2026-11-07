import pytest
from zemax_mcp.tolerance_distributions import describe_distribution
from zemax_mcp.errors import ZemaxError


def test_histogram_outside_counts_and_units():
    d=dict(series=[dict(y=[[1],[2]])])
    r=describe_distribution(d,'tolerance_histogram','样本尺寸： 8\n下溢计数： 2\n溢出计数： 3\n')
    assert r['distribution']['in_range_count']==3
    assert r['distribution']['overflow']==3
    assert r['series'][0]['y_unit']=='count'


@pytest.mark.parametrize('text',['','样本尺寸：8\n下溢计数：0\n溢出计数：0\n'])
def test_missing_or_inconsistent_counts(text):
    with pytest.raises(ZemaxError)as e:describe_distribution(dict(series=[dict(y=[[1]])]),'tolerance_histogram',text)
    assert e.value.code=='INVALID_RESULT_DATA'


def test_yield_keeps_raw_distribution_semantics():
    r=describe_distribution(dict(series=[dict(y=[[50]])]),'tolerance_yield','样本尺寸： 8\n')
    assert r['distribution']['sample_count']==8
    assert r['series'][0]['y_unit']=='percent'
