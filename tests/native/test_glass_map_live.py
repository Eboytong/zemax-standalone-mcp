"""Native glass-map result checked against the installed SCHOTT catalog."""
import asyncio
import json
from pathlib import Path
import pytest
from tests.support.material_catalog_reference import match_rows, read_catalog
from tests.support.native import execute


@pytest.mark.zemax
def test_glass_map_native_catalog_points_and_lifecycle():
    async def work(e):
        await e.model()
        baseline=await e.call("get_system_settings")
        result=await e.finish(await e.call("run_analysis",dict(request={"kind":"glass_map"})))
        assert result["analysis_kind"]=="glass_map",result
        assert result["task"]["state"]=="succeeded"
        assert result["task"]["settings"]["native"]["IsValid"] is True
        assert result["native_report_count"]==result["sample_count"]==346
        assert "SCHOTT" in result["system_settings"]["material_catalogs"]
        row=next(item for item in result["rows"] if item["material"]=="N-BK7")
        agf=Path.home()/"Documents"/"Zemax"/"Glasscat"/"SCHOTT.AGF"
        catalog_row=next(line.split() for line in agf.read_text(encoding="utf-8-sig").splitlines()
                         if line.split()[:2]==["NM","N-BK7"])
        e.check("N-BK7 catalog Nd",row["refractive_index_nd"],float(catalog_row[4]),atol=5e-6,rtol=0)
        e.check("N-BK7 catalog Vd",row["abbe_vd"],float(catalog_row[5]),atol=.005,rtol=0)
        scatter=result["scatter"][0]
        assert scatter["x_axis_direction"]=="decreasing_left_to_right"
        assert len(scatter["points"])==346
        page=await e.call("get_task_result",dict(task_id=result["task"]["task_id"],start=0,count=3))
        assert len(page["rows"])==3 and page["total"]==346
        image=await e.call("export_analysis_image",dict(request=dict(task_id=result["task"]["task_id"],path=str(e.folder/"glass-map.png"))))
        assert Path(image["artifacts"][0]["path"]).is_file()
        assert await e.call("get_system_settings")==baseline
    asyncio.run(execute("glass_map_native",work))


@pytest.mark.zemax
def test_glass_map_selected_catalog_identity():
    """Each selected catalog must match the reported rows under name normalisation.

    Names are compared case-insensitively through
    ``tests.support.material_catalog_reference`` (the report prints upper case,
    the catalog keeps mixed case, e.g. ``F2HTI`` vs ``F2HTi``). A genuinely
    missing material or an Nd/Vd value outside the display tolerance stays an
    explicit assertion failure with the row recorded, never an xfail reason.
    """
    observations = []
    async def work(e):
        try:
            await e.model()
            for catalog in ("SCHOTT", "OHARA"):
                agf = Path.home()/"Documents/Zemax/Glasscat"/(catalog+".AGF")
                identity, entries = read_catalog(agf)
                await e.call("update_system_settings", dict(settings=dict(material_catalogs=[catalog])))
                baseline = await e.call("get_system_settings")
                assert baseline["material_catalogs"] == [catalog]
                result = await e.finish(await e.call("run_analysis", dict(request={"kind":"glass_map"})))
                terminal = await e.call("get_task_status", dict(task_id=result["task"]["task_id"]))
                rows = [dict(material=row["material"],
                             refractive_index_nd=row["refractive_index_nd"],
                             abbe_vd=row["abbe_vd"]) for row in result["rows"]]
                match = match_rows(rows, entries)
                case_variants = sorted(
                    (dict(report_name=record["report_name"], catalog_name=record["catalog_name"])
                     for record in match["matched"]
                     if record["report_name"] != record["catalog_name"]),
                    key=lambda record: record["report_name"])
                observations.append(dict(requested_catalog=catalog,
                    actual_catalogs=baseline["material_catalogs"],
                    catalog_path=identity["path"],
                    catalog_header=identity["header"],
                    catalog_material_count=identity["material_count"],
                    count=len(result["rows"]),
                    matched_count=len(match["matched"]),
                    num_mismatched=len(match["mismatched"]),
                    num_missing=len(match["missing"]),
                    numeric_mismatches=[dict(report_name=record["report_name"],
                                             catalog_name=record["catalog_name"],
                                             nd_error=str(record["nd_error"]),
                                             vd_error=str(record["vd_error"]))
                                        for record in match["mismatched"]],
                    missing_materials=[record["report_name"] for record in match["missing"]],
                    case_variant_count=len(case_variants),
                    case_variants=case_variants,
                    task_state=result["task"]["state"],
                    close_attempted=terminal["close_attempted"],
                    model_preserved=await e.call("get_system_settings")==baseline))
                # Real gaps fail loudly with the offending rows preserved.
                assert not match["mismatched"], observations[-1]
                assert not match["missing"], observations[-1]
            assert all(o["count"]>0 and o["model_preserved"] and o["close_attempted"]
                       for o in observations), observations
            assert observations[0]['count'] != observations[1]['count'], observations
            assert all(o["matched_count"]==o["count"] for o in observations), observations
            # Every case-only difference must still resolve, and only by case.
            assert observations[0]["case_variant_count"] >= 7, observations
            assert observations[1]["case_variant_count"] == 0, observations
            assert all(variant["catalog_name"].upper()==variant["report_name"]
                       for o in observations for variant in o["case_variants"]), observations
        finally:
            (e.folder/"catalog-identity.json").write_text(json.dumps(observations,indent=2),encoding="utf-8")
            await e.call("disconnect")
    asyncio.run(execute("glass_map_catalog_identity",work))
