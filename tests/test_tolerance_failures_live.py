"""Actual untraceable trials, including finite 9e9 native criterion sentinels."""
import asyncio
import json
from pathlib import Path

import pytest
from support.native import execute


@pytest.mark.zemax
@pytest.mark.parametrize("amplitude,traceable",[(200.,3),(1000.,2)])
def test_failed_trial_statistics_native(amplitude,traceable):
    async def work(e):
        await e.call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
        await e.call("update_tolerances",dict(request=dict(mode="replace",operands=[
            dict(type="SEED",param1=42),dict(type="TTHI",param1=1,param2=2,minimum=-amplitude,maximum=amplitude)])))
        result=await e.finish(await e.call("run_tolerance_analysis",dict(request=dict(mode="monte_carlo",samples=8,save_samples=8,
            compensation="None",sampling=1,cycles=1,distribution="Uniform"))))
        e.check("native traceable trial count",result["summary"]["native_traceable_trials"],traceable)
        failed=[row for row in result["rows"]if row["state"]=="failed"]
        assert len(failed)==8-traceable
        assert all(row["values"][0]==9e9 for row in failed)
        statistics=await e.call("summarize_tolerance_results",dict(request=dict(task_id=result["task"]["task_id"],
            criterion_column=0,threshold=1e10,unit="native RMS spot criterion")))
        assert statistics["passed"]==traceable and statistics["finite_values"]==traceable
        assert statistics["failed_trial_numbers"]==[row["trial_number"]for row in failed]
        e.check("failed-trial yield denominator",statistics["pass_fraction_of_requested"],traceable/8)
        assert statistics["mean"]<10
        (e.folder/"trial_statistics_reference.json").write_text(json.dumps(dict(
            requested=8,seed=42,amplitude_mm=amplitude,traceable=traceable,
            native_failure_sentinel=9e9,threshold=1e10,expected_pass_fraction=traceable/8,
            reference="native Chinese per-trial IDs and printed criterion values align with the full structured rows; finite failed sentinels excluded",
            statistics=statistics),ensure_ascii=False,indent=2),encoding="utf-8")
    asyncio.run(execute("failed_trial_statistics_"+str(int(amplitude)),work))
