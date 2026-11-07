"""Saved trial models independently expose STAT distributions and COMP limits."""
import asyncio
import json
import math
from pathlib import Path
import pytest
from support.native import execute


@pytest.mark.zemax
def test_stat_mixture_saved_model_distribution_native():
    async def work(e):
        lens=Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos"
        await e.call("open_lens",dict(path=str(lens)))
        baseline=(await e.call("get_surfaces",dict(start=1,count=6)))["surfaces"]
        nominal={r["surface"]:r["cells"]["thickness"]["value"]for r in baseline}
        amplitude=.01;n=128
        operands=[dict(type="SEED",param1=42)]
        for kind,surface in ((1,1),(0,3),(2,5)):
            operands.extend([dict(type="STAT",param1=kind,**(dict(param2=2)if kind==0 else{})),
                dict(type="TTHI",param1=surface,param2=0,minimum=-amplitude,maximum=amplitude)])
        await e.call("update_tolerances",dict(request=dict(mode="replace",operands=operands)))
        result=await e.finish(await e.call("run_tolerance_analysis",dict(request=dict(mode="monte_carlo",samples=n,save_samples=n,
            compensation="None",sampling=1,cycles=1,distribution="Uniform"))))
        scopes=result["summary"]["distribution_by_operand"]
        assert [r["distribution"]["type"]for r in scopes]==["Uniform","Normal","Parabolic"]
        paths=result["summary"]["saved_samples"];assert len(paths)==n
        columns={i:[]for i in (1,3,5)};samples=[]
        for path in paths:
            await e.call("open_lens",dict(path=path))
            rows=(await e.call("get_surfaces",dict(start=1,count=6)))["surfaces"]
            values={r["surface"]:r["cells"]["thickness"]["value"]for r in rows}
            samples.append(dict(path=path,thicknesses=values))
            for i in columns:columns[i].append((values[i]-nominal[i])/amplitude)
        z=math.erf(2/math.sqrt(2));phi=math.exp(-2)/math.sqrt(2*math.pi)
        moments=[(1,1/3,1/5),(3,(1-4*phi/z)/4,(3-40*phi/z)/16),(5,3/5,3/7)]
        checks=[]
        for surface,second,fourth in moments:
            values=columns[surface]
            assert max(abs(v)for v in values)<=1+1e-7
            observed=sum(v*v for v in values)/n
            tolerance=6*math.sqrt((fourth-second*second)/n)
            checks.append(dict(surface=surface,expected_second_moment=second,actual=observed,atol=tolerance))
            e.check(f"STAT surface{surface} second moment",observed,second,atol=tolerance,rtol=0)
            e.check(f"STAT surface{surface} zero mean",sum(values)/n,0,atol=6*math.sqrt(second/n),rtol=0)
        (e.folder/"mixture-reference.json").write_text(json.dumps(dict(seed=42,samples=n,half_range_mm=amplitude,
            scopes=scopes,checks=checks,models=samples,reference="manual7.6.9: Uniform; Normal truncated at2sigma; Parabolic density proportional to x^2",
            sample_unit="individual thickness read from each saved Monte Carlo model; no adjuster"),indent=2),encoding="utf-8")
    asyncio.run(execute("stat_mixture",work))


@pytest.mark.zemax
def test_compensator_bounds_saved_model_native():
    async def work(e):
        await e.call("open_lens",dict(path=str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")))
        center=(await e.call("get_surfaces",dict(start=6,count=1)))["surfaces"][0]["cells"]["thickness"]["value"]
        lo,hi=center-.0001,center+.0001
        await e.call("update_tolerances",dict(request=dict(mode="replace",operands=[dict(type="SEED",param1=42),
            dict(type="TTHI",param1=1,param2=0,minimum=-.1,maximum=.1),dict(type="COMP",param1=6,param2=0,minimum=-.0001,maximum=.0001)])))
        result=await e.finish(await e.call("run_tolerance_analysis",dict(request=dict(mode="monte_carlo",samples=8,save_samples=8,
            compensation="OptimizeAll_DLS",sampling=1,cycles=5,distribution="Uniform"))))
        records=[];boundary_operands=[]
        for path in result["summary"]["saved_samples"]:
            await e.call("open_lens",dict(path=path))
            value=(await e.call("get_surfaces",dict(start=6,count=1)))["surfaces"][0]["cells"]["thickness"]["value"]
            records.append(dict(path=path,thickness_mm=value,distance_to_bound_mm=min(abs(value-lo),abs(value-hi)),outside_mm=max(lo-value,value-hi,0)))
            if not boundary_operands:
                merit=await e.call("get_merit_function",dict(start=1,count=500))
                boundary_operands=merit["operands"]
        report=dict(lower_mm=lo,upper_mm=hi,cycles=5,algorithm="OptimizeAll_DLS",criterion="RMSSpotRadius",samples=records,
            boundary_operands=boundary_operands,trigger_window_mm=1e-5,
            source="manual lines28409-28411: COMP min/max are offsets; resulting optimization constraints are soft and may be violated")
        (e.folder/"compensator-reference.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
        assert len(records)==8
        # Verify the generated constraint targets, and retain every soft violation.
        targets=[row["target"]for row in boundary_operands]
        assert any(abs(value-lo)<1e-7 for value in targets),"lower COMP absolute target missing"
        assert any(abs(value-hi)<1e-7 for value in targets),"upper COMP absolute target missing"
        assert all(math.isfinite(row["thickness_mm"])for row in records)
        assert any(row["distance_to_bound_mm"]<1e-5 for row in records),"no compensator boundary sample observed"
    asyncio.run(execute("compensator_bounds",work))
