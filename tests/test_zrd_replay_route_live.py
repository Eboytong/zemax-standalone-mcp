"""Independent native Detector Viewer path on the recorded fluorescence fixture."""
import asyncio
import json
from pathlib import Path

import pytest
from support.native import execute


@pytest.mark.zemax
def test_recorded_polar_replay_execution_native():
    async def work(e):
        spec=json.loads((Path(__file__).parent/"reference_data/wavelength-filter.json").read_text(encoding="utf-8"))
        fixture=Path(spec["fluorescence_fixture"]).resolve()
        await e.call("open_lens",dict(path=str(fixture/"dilute_fluorescence.zos")))
        records=[]
        for expression in ("", "X_WAVERANGE(3,0.499,0.751)", "X_WAVERANGE(3,0.500,0.525)",
                           "X_WAVERANGE(3,0.650,0.675)", "X_WAVERANGE(3,0.800,0.900)"):
            result=await e.finish(await e.call("run_zrd_replay",dict(request=dict(path=str(fixture/"fluorescence.zrd"),
                detector=3,filter=expression,data_type="RadiantIntensity"))))
            assert result["native_replay_summary"]["extraction_status"]=="available"
            assert result["native_replay_summary"]["total_power"]["unit"]=="Watts"
            records.append(dict(filter=expression,header=result["native_header"],preamble=result["native_preamble"],
                messages=result["native_messages"],grids=[{k:v for k,v in g.items()if k!="values"}for g in result["grids"]],
                artifacts=result["artifacts"],native_replay_summary=result["native_replay_summary"],
                verification_scope="native execution and explicit watt-text extraction; fine-band numerical status is separate"))
            print(expression,result["native_preamble"][:20],flush=True)
        (e.folder/"replay-route.json").write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding="utf-8")
    asyncio.run(execute("polar_replay_route",work))
