"""Finite official-file fixtures: parameter values, solve adoption, persistence.

These checks distinguish numeric parameter transfer from a surface's optical model.
They do not classify enumeration discovery as sag/ray numerical validation.
"""
import asyncio
import json
import math
from pathlib import Path
import pytest
from tests.support.native import execute

CASES=json.loads((Path(__file__).parent/"reference_data/official-surfaces.json").read_text(encoding="utf-8"))


@pytest.mark.zemax
@pytest.mark.parametrize("case",CASES,ids=lambda c:c["native_type"])
def test_official_sample_surface_cells_native(case):
    async def work(e):
        path=Path(case["file"])
        if not path.is_file():pytest.skip("official fixture input missing: "+str(path))
        await e.call("open_lens",dict(path=str(path)))
        surface=case["surface"]
        snapshot=(await e.call("get_surfaces",dict(start=surface,count=1)))["surfaces"][0]
        record=dict(fixture=case,actual_surface_type=snapshot["surface_type"],baseline=snapshot,combinations=[],
            optical_status="pending_surface_specific_sag_or_ray_reference")
        baseline=e.folder/"baseline.zos"
        await e.call("save_lens_as",dict(path=str(baseline)))
        try:
            raw=case["raw"]
            for name,key in (("conic","CONI"),("thickness","DISZ")):
                if key in raw and type(snapshot["cells"].get(name,{}).get("value"))in(int,float):
                    expected=float(raw[key][0])
                    if math.isfinite(expected):e.check("official file numeric "+name,snapshot["cells"][name]["value"],expected)
            for parameter,value in raw["parameters"].items():
                cell=snapshot["cells"].get("parameter_"+parameter)
                if cell and type(cell.get("value"))in(int,float):e.check("official parameter "+parameter,cell["value"],float(value))
            # Restore the same saved baseline for every independent mode request.
            for name,cell in snapshot["cells"].items():
                if not cell["writable"] or type(cell.get("value"))not in(int,float) or not math.isfinite(cell["value"]):continue
                for mode,native in (("fixed","Fixed"),("variable","Variable")):
                    if native not in cell["available_solves"]:continue
                    await e.call("open_lens",dict(path=str(baseline)))
                    result=await e.call("update_surfaces",dict(changes=[dict(surface=surface,replace_solves=True,solves={name:dict(mode=mode)})]),okay=False)
                    item=dict(cell=name,mode=mode)
                    if isinstance(result,dict)and result.get("ok")is False:
                        item.update(status="native_rejected",error=result["error"])
                        if snapshot["surface_type"]=="Hologram2" and name=="parameter_13" and mode=="variable" and cell["value"]==0:
                            assert result["error"]["code"]=="UNSUPPORTED_SOLVE",result
                            assert not result["error"]["details"]["partial_changes_possible"],result
                            item["status"]="persistence_guard_rejected"
                    else:
                        after=(await e.call("get_surfaces",dict(start=surface,count=1)))["surfaces"][0]["cells"][name]
                        assert after["solve"]["type"]==native
                        saved=e.folder/f"{name}_{mode}.zos"
                        await e.call("save_lens_as",dict(path=str(saved)));await e.call("open_lens",dict(path=str(saved)))
                        reloaded=(await e.call("get_surfaces",dict(start=surface,count=1)))["surfaces"][0]["cells"][name]
                        persisted=reloaded["solve"]["type"]==native
                        item.update(status="mode_and_reload_pass"if persisted else"native_not_persistent",
                            requested_native_mode=native,reloaded_native_mode=reloaded["solve"]["type"],
                            value=reloaded["value"],optical_status="no_new_solve_target_reference")
                    record["combinations"].append(item)
                    if item["status"]=="native_not_persistent":
                        raise AssertionError("Unexpected solve persistence loss: "+str(item))
        finally:
            (e.folder/"official-surface-reference.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    asyncio.run(execute("official_surface_"+case["native_type"],work))
