"""Native source units versus radiometric Polar Power (no concurrent native instances)."""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from zemax_mcp.config import PROJECT_ROOT
from tests.support.native import execute
from tests.support.paths import run_dir


@pytest.mark.zemax
def test_nsc_units_native():
    inputs=run_dir("nsc_unit_inputs")
    process=subprocess.run([sys.executable,"-B",str(Path(__file__).parent/"support/nsc_unit_fixtures.py"),str(inputs)],
        cwd=PROJECT_ROOT,env={**os.environ,"PYTHONUTF8":"1"},capture_output=True,text=True,encoding="utf-8",timeout=120)
    (inputs/"stdout.log").write_text(process.stdout,encoding="utf-8")
    (inputs/"stderr.log").write_text(process.stderr,encoding="utf-8")
    assert process.returncode==0,process.stderr
    cases=json.loads((inputs/"reference.json").read_text(encoding="utf-8"))
    async def work(e):
        for case in cases:
            await e.call("open_lens",dict(path=case["path"]))
            result=await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(random_seed=42,use_polarization=True))))
            polar=await e.call("get_detector_data",dict(request=dict(detector=2)))
            intensity=await e.call("get_detector_data",dict(request=dict(detector=2,kind="intensity",width=1,height=1)))
            rectangle=await e.call("get_detector_data",dict(request=dict(detector=3)))
            coherent=await e.call("get_detector_data",dict(request=dict(detector=3,kind="coherent",coherent_type="Power")))
            label=case["units"]+" "+case["prefix"]
            e.check(label+" Polar radiometric power",polar["total_flux"],case["polar_power"])
            e.check(label+" rectangle source-unit flux",rectangle["total_flux"],case["rectangle_flux"])
            e.check(label+" coherent source-unit power",sum(sum(row)for row in coherent["values"]),case["rectangle_coherent"])
            e.check(label+" Polar solid angle",intensity["values"][0][0],
                    polar["total_flux"]/(36*polar["pixel_solid_angle_sr"][0]))
            assert polar["value_unit"]==case["polar_value_unit"]
            assert intensity["value_unit"]==case["polar_value_unit"]+"/sr"
            assert rectangle["value_unit"]==coherent["value_unit"]==case["units"]
            assert polar["value_unit_prefix"]==rectangle["value_unit_prefix"]==case["prefix"]
            for row in result["rows"]:
                expected=case["polar_value_unit"]if row["detector"]==2 else case["units"]
                assert row["value_unit"]==expected
                assert row["metrics"][0]["unit"]==((case["prefix"]+" ")if case["prefix"]!="None"else"")+expected
        (e.folder/"unit_references.json").write_text(json.dumps(dict(inputs=str(inputs),cases=cases),indent=2),encoding="utf-8")
    asyncio.run(execute("nsc_units",work))

