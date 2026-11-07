"""Only complete, numerically aligned native trial tables may classify finite sentinels."""
from copy import deepcopy
from pathlib import Path
import pytest

from zemax_mcp.backend import Backend
from zemax_mcp.config import Config
from zemax_mcp.models import COMMAND_MODELS
from zemax_mcp.tolerancing import verified_trial_table
from zemax_mcp.errors import ZemaxError

TEXT="""蒙特卡罗分析:
测试数: 3
初始统计: 均匀分布
  测试      标准        改变
 1 不能追迹透镜，公差可能太宽松!
 2 2.63714902 2.62553931
 3 4.74805448 4.73644477
可追迹的蒙特卡罗文件产生数: 2
"""
ROWS=[dict(index=i,values=[value])for i,value in enumerate((9e9,2.6371490233098847,4.748054479306063))]
COLUMNS=[dict(column=0,is_operand=False)]


def test_verified_trial_table_uses_ids_counts_and_displayed_precision():
    parsed=verified_trial_table(TEXT,3,ROWS,COLUMNS,0)
    assert [t["state"]for t in parsed["trials"]]==["untraceable","traceable","traceable"]
    assert parsed["trials"][0]["trial"]==1


@pytest.mark.parametrize("change",["missing","duplicate","wrong_count","unknown_failure","wrong_value","wrong_index","wrong_column","unknown_header"])
def test_uncertain_trial_mapping_is_unavailable(change):
    text=TEXT;rows=deepcopy(ROWS);column=0
    if change=="missing":rows.pop()
    elif change=="duplicate":text=text.replace(" 3 4.74805448"," 2 4.74805448")
    elif change=="wrong_count":text=text.replace("产生数: 2","产生数: 3")
    elif change=="unknown_failure":text=text.replace("不能追迹透镜，公差可能太宽松!","unknown failure")
    elif change=="wrong_value":rows[1]["values"][0]+=1e-5
    elif change=="wrong_index":rows[1]["index"]=7
    elif change=="wrong_column":column=1
    else:text=text.replace("蒙特卡罗分析:","Unknown format:")
    assert verified_trial_table(text,3,rows,COLUMNS,column)is None


def test_failed_finite_sentinel_never_passes_threshold_or_enters_mean(tmp_path):
    b=Backend(Config(Path("unused"),tmp_path))
    result=dict(task=dict(kind="tolerance_analysis"),rows=ROWS,
        summary=dict(requested_samples=3,native_traceable_trials=2,columns=COLUMNS,summary_text=TEXT))
    b._full_result=lambda _:result
    q=COMMAND_MODELS["summarize_tolerance_results"](task_id="mc",criterion_column=0,threshold=1e10,unit="mm")
    statistics=b.summarize_tolerance_results(q)
    assert statistics["passed"]==2 and statistics["pass_fraction_of_requested"]==pytest.approx(2/3)
    assert statistics["failed_trial_numbers"]==[1]and statistics["native_untraceable_trials"]==1
    assert statistics["mean"]==pytest.approx((ROWS[1]["values"][0]+ROWS[2]["values"][0])/2)
    assert statistics["pass_fraction_scope"]=="requested_sample_set_untraceable_counted_as_failed"
    result["summary"]["native_traceable_trials"]=3
    with pytest.raises(ZemaxError):b.summarize_tolerance_results(q)
    result["summary"]["native_traceable_trials"]=2
    result["summary"]["summary_text"]="unknown format"
    with pytest.raises(ZemaxError)as error:b.summarize_tolerance_results(q)
    assert error.value.code=="SAMPLE_STATUS_UNAVAILABLE"
