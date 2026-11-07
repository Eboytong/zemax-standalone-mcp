"""Prepared same-session stage handoffs; native acceptance requires startup recovery."""
import asyncio
import json
import math
import shutil
import uuid
from pathlib import Path
import pytest
from support.native import execute


async def cooke(e):
    return await e.call("open_lens", {"path": str(Path.home()/"Documents/Zemax/Samples/Sequential/Objectives/Cooke 40 degree field.zos")})


async def finished(e, started, timeout_seconds=90):
    result = await e.finish(started, timeout_seconds=timeout_seconds)
    state = await e.call("get_task_status", {"task_id":started["task_id"]})
    assert state["state"] == "succeeded" and not state.get("cleanup_warnings"), state
    if "close_attempted" in state:
        assert state["close_attempted"] is True, state
    status = await e.call("get_status")
    assert status["active_task"] is None and not status["running_tasks"], status
    return result


@pytest.mark.zemax
def test_optimized_model_to_full_field_evaluation():
    async def work(e):
        model = await cooke(e)
        surface = model["surface_count"]-2
        await e.call("update_merit_function", {"mode":"rms_spot_wizard","operands":[]})
        await e.call("set_variables", {"variables":[{"surface":surface,"cell":"thickness"}]})
        optimized = await finished(e, await e.call("run_local_optimization", {"cycles":"Fixed_1_Cycle"}))
        assert optimized["after"]["merit_function"] <= optimized["before"]["merit_function"]*1.001+1e-10
        baseline = await e.call("get_surfaces")
        settings = await e.call("get_system_settings")
        row = (await e.call("get_surfaces", {"start":surface,"count":1}))["surfaces"][0]
        q = {"surface":surface,"cell":"thickness","values":[row["cells"]["thickness"]["value"]],
             "replace_solve":True,"evaluation":{"spot":{"reference":"Centroid"},
             "mtf":{"sampling":"S_32x32"},"frequencies":[10,25],"merit":True}}
        evaluated = await finished(e, await e.call("run_parameter_scan", {"request":q}))
        assert evaluated["summary"]["succeeded"] == 1 and evaluated["restoration"]["restored"]
        direct = await finished(e, await e.call("run_spot_analysis", {"reference":"Centroid"}))
        e.check("optimized scan vs direct spot RMS", evaluated["rows"][0]["metrics"][0]["value"],
                direct["metrics"][0]["rms_radius"],atol=1e-8,rtol=1e-7)
        assert await e.call("get_surfaces") == baseline
        assert await e.call("get_system_settings") == settings
        ids = [r["task"]["task_id"] for r in [optimized,evaluated,direct]]
        report = await e.call("export_evaluation_report", {"task_ids":ids,"include_charts":True})
        assert report["artifacts"] and all(Path(a["path"]).is_file() for a in report["artifacts"])
        saved = e.folder/"optimized.zos"
        await e.call("save_lens_as", {"path":str(saved)})
        await e.call("open_lens", {"path":str(saved)})
        reloaded = await finished(e, await e.call("run_spot_analysis", {"reference":"Centroid"}))
        assert len(reloaded["metrics"]) == len(direct["metrics"])
        for a,b in zip(reloaded["metrics"],direct["metrics"]):
            e.check("saved optimized spot RMS",a["rms_radius"],b["rms_radius"],atol=1e-8,rtol=1e-7)
        (e.folder/"handoff.json").write_text(json.dumps({"stage_tasks":ids,"saved_model":str(saved),
            "sampling":"S_32x32","spot_tolerance":{"absolute":1e-8,"relative":1e-7}},indent=2),encoding="utf-8")
    asyncio.run(execute("release_optimized_evaluation",work))


@pytest.mark.zemax
def test_tolerance_to_same_model_manufacturing_delivery():
    async def work(e):
        await cooke(e)
        await e.call("update_tolerances", {"request":{"mode":"replace","operands":[
            {"type":"TTHI","param1":1,"param2":2,"minimum":-.01,"maximum":.01}]}})
        before = await e.call("get_surfaces")
        settings = await e.call("get_system_settings")
        tolerance = await finished(e, await e.call("run_tolerance_analysis", {"request":{
            "mode":"sensitivity","compensation":"None"}}),timeout_seconds=180)
        assert await e.call("get_surfaces") == before
        assert await e.call("get_system_settings") == settings
        cad = await finished(e, await e.call("run_cad_export", {"request":{
            "path":str(e.folder/"toleranced_design.step"),"end":2}}),timeout_seconds=180)
        visualization = await finished(e, await e.call("run_cad_export", {"request":{
            "path":str(e.folder/"toleranced_design.json"),"format":"VisualizationJSON","end":2}}),timeout_seconds=180)
        assert visualization["triangles"] > 0
        assert await e.call("get_surfaces") == before
        assert await e.call("get_system_settings") == settings
        ids = [r["task"]["task_id"] for r in [tolerance,cad,visualization]]
        report = await e.call("export_evaluation_report", {"task_ids":ids,"formats":["markdown","pdf"]})
        assert report["artifacts"] and all(Path(a["path"]).is_file() for a in report["artifacts"])
        await e.call("save_lens_as", {"path":str(e.folder/"toleranced_design.zos")})
        (e.folder/"handoff.json").write_text(json.dumps({"stage_tasks":ids,
            "model":"toleranced_design.zos","tolerance":"TTHI 1,2 +/-0.01 lens units",
            "manufacturing_extent":"surfaces through 2","numeric_scope":"existing tolerance reference tests remain separate"},indent=2),encoding="utf-8")
    asyncio.run(execute("release_tolerance_manufacturing",work))


@pytest.mark.zemax
def test_aspheric_decenter_to_geometry_ray_and_reload():
    from support.surface_reference import sag
    async def work(e):
        await e.model()
        await e.call("insert_surfaces", {"at":2})
        await e.call("update_surfaces", {"changes":[
            {"surface":1,"thickness":10,"semi_diameter":5,"replace_solves":True},
            {"surface":2,"surface_type":"EvenAspheric","radius":50,"conic":-.3,
             "parameters":{"1":1e-4,"2":-1e-7},"thickness":5,"semi_diameter":5,
             "tilt_decenter":{"before_order":"Decenter_Tilt","before_decenter_x":.2,"before_tilt_y":1},
             "replace_solves":True}]})
        points=[{"x":x,"y":y} for x,y in [(0,0),(.6,0),(0,.4),(.5,.3)]]
        async def inspect(label):
            geometry=await e.call("get_surface_geometry", {"request":{"surface":2,"points":points}})
            for point,row in zip(points,geometry["rows"],strict=True):
                expected=sag("EvenAspheric",point["x"],point["y"],50,-.3,{1:1e-4,2:-1e-7})
                e.check(label+" aspheric sag",row["sag"],expected,atol=1e-8,rtol=1e-7)
            frame=await e.call("get_surface_geometry", {"request":{"surface":1,"points":[]}})
            e.check(label+" before-surface rotation cos",frame["global_transform"]["rotation"][0][0],math.cos(math.radians(1)))
            rays=await finished(e, await e.call("run_batch_ray_trace", {"request":{
                "rays":[{"px":0,"py":0},{"px":.1,"py":.1}],"target_surface":3}}))
            assert len(rays["rows"])==2 and all(row["error_code"]==0 and not row["vignette_code"] for row in rays["rows"])
            return rays
        before=await inspect("memory")
        saved=e.folder/"aspheric_decenter.zos"
        await e.call("save_lens_as", {"path":str(saved)})
        await e.call("open_lens", {"path":str(saved)})
        after=await inspect("reloaded")
        for left,right in zip(before["rows"],after["rows"],strict=True):
            for field in ["position","direction"]:
                for component,(actual,expected) in enumerate(zip(right[field],left[field],strict=True)):
                    e.check("reloaded ray "+field+str(component),actual,expected,atol=1e-8,rtol=1e-7)
        await e.call("export_evaluation_report", {"task_ids":[before["task"]["task_id"],after["task"]["task_id"]]})
    asyncio.run(execute("release_aspheric_decenter",work))


@pytest.mark.zemax
def test_coating_layer_polarization_to_image_and_reload():
    async def work(e):
        await cooke(e)
        resources=await e.call("get_system_resources", {"request":{"kind":"coatings","surface":1}})
        selected=None
        for name in resources["items"]:
            await e.call("update_surfaces", {"changes":[{"surface":1,"coating":name}]})
            layers=await e.call("get_coating_layers", {"request":{"surface":1,"count":1}})
            if layers["total"]:
                selected=name
                break
        if selected is None:
            (e.folder/"resource-condition.json").write_text(json.dumps({"status":"blocked",
                "observed_coatings":resources["items"],"release_condition":"Supply a native editable multilayer coating fixture."}),encoding="utf-8")
            await e.call("disconnect")
            pytest.skip("No editable multilayer fixture in the native coating list")
        await e.call("update_coating_layers", {"request":{"surface":1,"use_layer_multiplier_and_offsets":True,
            "layers":[{"layer":1,"thickness_multiplier":.9}]}})
        await e.call("update_system_settings", {"settings":{"polarization":{"unpolarized":False,"jx":1,"jy":0}}})
        images=await e.call("get_system_resources", {"request":{"kind":"image_simulation_files"}})
        target=Path(images["directory"])/("release_"+uuid.uuid4().hex+".IMA")
        shutil.copy2(Path(__file__).parent/"resources/imaging023/point.IMA",target)
        try:
            baseline=await e.call("get_surfaces")
            settings=await e.call("get_system_settings")
            coating=await finished(e, await e.call("run_analysis", {"request":{
                "kind":"transmission_vs_angle","surface":1,"wavelength":1,"minimum_angle":0,"maximum_angle":60}}))
            assert coating["series"]
            results=[coating]
            for label in ["memory","reloaded"]:
                if label=="reloaded":
                    saved=e.folder/"coated_image.zos"
                    await e.call("save_lens_as", {"path":str(saved)})
                    await e.call("open_lens", {"path":str(saved)})
                actual=await e.call("get_coating_layers", {"request":{"surface":1,"count":1}})
                assert actual["coating"]==selected and actual["use_layer_multiplier_and_offsets"]
                e.check(label+" adopted layer thickness multiplier",actual["rows"][0]["thickness_multiplier"],.9,atol=1e-12,rtol=1e-12)
                image=await finished(e, await e.call("run_analysis", {"request":{
                    "kind":"image_simulation","input_file":target.name,"wavelength":1,
                    "use_polarization":True,"psf_x_points":3,"psf_y_points":3,"x_pixels":33,"y_pixels":33}}),timeout_seconds=180)
                assert image["structured_data_available"] and image["task"]["settings"]["native"]["UsePolarization"] is True
                await e.call("get_task_result", {"task_id":image["task"]["task_id"],"grid":0,"width":7,"height":5})
                await e.call("export_analysis_image", {"request":{"task_id":image["task"]["task_id"],"path":str(e.folder/(label+".png"))}})
                results.append(image)
            assert await e.call("get_surfaces")==baseline
            assert await e.call("get_system_settings")==settings
            await e.call("export_evaluation_report", {"task_ids":[r["task"]["task_id"] for r in results],"include_charts":True})
        finally:
            target.unlink(missing_ok=True)
    asyncio.run(execute("release_coated_image",work))


@pytest.mark.zemax
def test_nsc_trace_to_detector_path_and_report():
    from support.nsc import detector,trace
    from test_nsc_path_live import detector_model
    async def work(e):
        await detector_model(e)
        baseline=await e.call("get_nsc_objects", {"request":{}})
        traced,segments=await trace(e,"release_path")
        assert segments
        measured=await detector(e,2)
        e.check("detector input W",measured["total_flux"],1,atol=1e-8,rtol=1e-7)
        path=await finished(e, await e.call("run_analysis", {"request":{
            "kind":"path_analysis","path":str(e.folder/"release_path.zrd")}}))
        e.check("path vs detector W",sum(row["flux_out_w"] for row in path["rows"]),measured["total_flux"],atol=1e-8,rtol=1e-7)
        await e.call("get_task_result", {"task_id":path["task"]["task_id"],"count":1})
        assert await e.call("get_nsc_objects", {"request":{}})==baseline
        await e.call("export_evaluation_report", {"task_ids":[traced["task"]["task_id"],path["task"]["task_id"]]})
    asyncio.run(execute("release_nsc_path_detector",work))


@pytest.mark.zemax
def test_pop_beam_to_file_receiver_and_report():
    async def work(e):
        await e.model()
        baseline=await e.call("get_surfaces")
        settings={"end_surface":2,"beam_parameters":{"0":.1,"1":.1},
            "x_sampling":"S_256x256","y_sampling":"S_256x256","x_width":2,"y_width":2}
        first=await finished(e, await e.call("run_pop", {"request":settings}))
        beam=next(a["path"] for a in first["artifacts"] if a["kind"]=="beam")
        samples=await e.call("get_beam_file", {"request":{"path":beam,"count":3,"include_coordinates":True}})
        assert samples["rows"]
        second=await finished(e, await e.call("run_pop", {"request":{**settings,"fiber_type":"File","fiber_file":beam,"fiber_parameters":{}}}))
        e.check("same propagated field receiver overlap",second["metrics"]["receiver_efficiency"],1,atol=5e-4,rtol=0)
        e.check("same field power",second["metrics"]["integrated_power"],first["metrics"]["integrated_power"],atol=5e-4,rtol=0)
        await e.call("get_task_result", {"task_id":second["task"]["task_id"],"grid":0,"width":7,"height":5})
        await e.call("export_analysis_image", {"request":{"task_id":second["task"]["task_id"],"path":str(e.folder/"coupled.png")}})
        assert await e.call("get_surfaces")==baseline
        await e.call("export_evaluation_report", {"task_ids":[first["task"]["task_id"],second["task"]["task_id"]]})
    asyncio.run(execute("release_pop_file_coupling",work))
