"""Native closed-interval selection and explicit fluorescence sub-bin evidence."""
import asyncio
import json
import math
from pathlib import Path

import pytest

from support.native import execute
from support.nsc import setup, update


@pytest.mark.zemax
def test_fixed_wavelength_filter_native():
    async def work(e):
        waves = [.4375, .5, .515625, .5625, .625, .6875, .75]
        sources = [1, 2, 4, 5, 6, 7, 8]
        await setup(e, 8)
        await e.call("update_system_settings", dict(settings=dict(wavelengths=[dict(wavelength_um=w) for w in waves],
            source_units="Watts", source_unit_prefix="None")))
        await update(e, [dict(object=s, object_type="SourceRay", x=i/10,
            data=dict(NumberOfAnalysisRays=1, Power=(i+1)/10, ZCosine=1, WaveNumber=i+1)) for i,s in enumerate(sources)] + [
            dict(object=3, object_type="DetectorRectangle", z=10, material="ABSORB",
                data=dict(XHalfWidth=2,YHalfWidth=2,NumberXPixels=1,NumberYPixels=1))])
        zrd = e.folder/"fixed_wavelengths.zrd"
        await e.call("save_lens_as",dict(path=str(e.folder/"fixed_wavelengths.zos")))
        await e.finish(await e.call("run_nsc_ray_trace",dict(request=dict(save_zrd=str(zrd),random_seed=42))))
        async def read(expression="", **page):
            return await e.finish(await e.call("read_zrd",dict(request=dict(path=str(zrd),filter=expression,**page))))
        unfiltered=await read()
        hits=[r for r in unfiltered["rows"]if r["HitObject"]==3]
        assert len(hits)==7
        for ray in hits:
            i=round(ray["X"]*10)
            e.check("unconverted ray-header wavelength um",ray["WlUM"],waves[i])
            e.check("known single-ray power W",ray["Intensity"],(i+1)/10)
        intervals=[(.4,.8),(.5,.525),(.525,.55),(.55,.575),(.5,.625),(.625,.75),(.5,.5),(.8,.9)]
        records=[]
        for lower,upper in intervals:
            expression=f"X_WAVERANGE(3,{lower:.17g},{upper:.17g})"
            result=await read(expression)
            selected=[r for r in result["rows"]if r["HitObject"]==3]
            expected=[r for r in hits if lower<=r["WlUM"]<=upper]
            actual_keys=sorted((r["RayNumber"],r["segment_index"])for r in selected)
            expected_keys=sorted((r["RayNumber"],r["segment_index"])for r in expected)
            records.append(dict(filter=expression,actual_keys=actual_keys,expected_keys=expected_keys,
                actual_W=sum(r["Intensity"]for r in selected),expected_W=sum(r["Intensity"]for r in expected),
                exact_membership=actual_keys==expected_keys,summary=result["summary"]))
        for expression,expected_keys in (
            ("X_WAVERANGE(3.0,0.5,0.525)",sorted((r["RayNumber"],r["segment_index"])for r in hits if .5<=r["WlUM"]<=.525)),
            ("X_WAVERANGE(3,5e-1,5.25e-1)",sorted((r["RayNumber"],r["segment_index"])for r in hits if .5<=r["WlUM"]<=.525)),
            ("X_WAVERANGE(1,0.5,0.75)",[])):
            result=await read(expression)
            keys=sorted((r["RayNumber"],r["segment_index"])for r in result["rows"]if r["HitObject"]==3)
            records.append(dict(filter=expression,actual_keys=keys,expected_keys=expected_keys,exact_membership=keys==expected_keys))
        # Resume indexes are relative to the same filtered native ray stream.
        expression="X_WAVERANGE(3,0.5,0.75)"
        full=await read(expression);page_args={};rows=[];pages=[]
        for _ in range(20):
            page=await read(expression,max_segments=3,**page_args)
            rows.extend(page["rows"]);pages.append(page["summary"])
            page_args=page["summary"]["next_read"]
            if not page_args:break
        else:raise AssertionError("pagination failed to advance")
        def keys(rows):return[(r["RayNumber"],r["segment_index"])for r in rows]
        assert keys(rows)==keys(full["rows"])
        record=dict(wavelengths_um=waves,source_objects=sources,reference="Seven exact binary wavelengths, one ray each, Power=(source ordinal+1)/10 W; native intervals include both endpoints",
            interval_records=records,pages=pages,pagination_keys=keys(rows),full_keys=keys(full["rows"]),
            numerical_status="passed"if all(r["exact_membership"]for r in records)else"failed")
        (e.folder/"filter-reference.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
        for r in records:
            assert r["exact_membership"],r
            if "actual_W"in r:e.check("closed interval power W",r["actual_W"],r["expected_W"])
    asyncio.run(execute("fixed_wavelength_filter",work))


@pytest.mark.zemax
@pytest.mark.parametrize("criterion",["native_consistency","numeric_membership"])
def test_fluorescence_wavelength_membership_native(criterion):
    spec=json.loads((Path(__file__).parent/"reference_data/wavelength-filter.json").read_text(encoding="utf-8"))
    fixture=Path(spec["fluorescence_fixture"]).resolve()
    direct_path=Path(spec["native_reference"])
    if not (fixture/"fluorescence.zrd").is_file():pytest.skip("explicit recorded fluorescence ZRD input missing")
    if not direct_path.is_file():pytest.skip("run the serial native diagnostic on the explicit recorded fluorescence input first")
    differences=[]
    async def work(e):
        await e.call("open_lens",dict(path=str(fixture/"dilute_fluorescence.zos")))
        direct=json.loads(direct_path.read_text(encoding="utf-8"))
        async def read(expression):
            data=await e.finish(await e.call("read_zrd",dict(request=dict(path=str(fixture/"fluorescence.zrd"),filter=expression,max_segments=10000))))
            assert not data["summary"]["truncated"]
            assert data["summary"]["actual_filter"]==expression
            return data
        broad=await read("X_WAVERANGE(3,0.499,0.751)")
        hits=[r for r in broad["rows"]if r["HitObject"]==3]
        assert len(hits)==len({r["RayNumber"]for r in hits})==402
        catalog=Path.home()/"Documents/Zemax/Glasscat/SCHOTT.AGF"
        selected=False;coefficients=None
        for line in catalog.read_text(encoding="utf-8-sig",errors="replace").splitlines():
            if line.startswith("NM "):selected=line.split()[1]=="N-BK7"
            if selected and line.startswith("CD "):coefficients=list(map(float,line.split()[1:7]));break
        assert coefficients
        references=[]
        for r in hits:
            assert r["InsideOf"]==1 and r["OpticalPathLU"]>0 and r["OpticalPathW"]>0
            wave=1000*r["OpticalPathLU"]/r["OpticalPathW"]
            l2=wave*wave
            index=math.sqrt(1+sum(coefficients[i]*l2/(l2-coefficients[i+1])for i in (0,2,4)))
            e.check("independent segment index",r["Index"],index,atol=spec["path_wavelength_index_atol"],rtol=0)
            references.append(dict(ray=r["RayNumber"],segment=r["segment_index"],wavelength_um=wave,power_W=r["Intensity"],native_index=r["Index"],reference_index=index))
        edges=[nm/1000 for nm in range(spec["lower_nm"],spec["upper_nm"]+1,spec["step_nm"])]
        distance=min(abs(r["wavelength_um"]-edge)for r in references for edge in edges)
        assert distance>1e-6,"recorded wavelengths too near a boundary for the fixed optical-path precision budget"
        records=[]
        def keys(rows):return sorted((r["RayNumber"],r["segment_index"])for r in rows if r["HitObject"]==3)
        for lower,upper in zip(edges,edges[1:]):
            expression=f"X_WAVERANGE(3,{lower:.3f},{upper:.3f})"
            data=await read(expression)
            actual=keys(data["rows"])
            reference=[r for r in references if lower<=r["wavelength_um"]<=upper]
            expected=sorted((r["ray"],r["segment"])for r in reference)
            native_routes=[]
            for route in ("properties","official"):
                other=next(r for r in direct["reads"]if r["route"]==route and r["filter"]==expression and "current_system_wave_um"not in r)
                assert not other.get("error"),other
                direct_keys=sorted((r["ray"],r["segment"])for r in other["hits"])
                assert direct_keys==actual,"MCP/native route mismatch"
                direct_W=sum(r["power"]for r in other["hits"])
                e.check("MCP power versus direct "+route,sum(r["Intensity"]for r in data["rows"]if r["HitObject"]==3),direct_W)
                native_routes.append(dict(route=route,keys=direct_keys,power_W=direct_W))
            item=dict(filter=expression,lower_um=lower,upper_um=upper,expected_keys=expected,actual_keys=actual,
                missing=sorted(set(expected)-set(actual)),unexpected=sorted(set(actual)-set(expected)),
                expected_W=sum(r["power_W"]for r in reference),actual_W=sum(r["Intensity"]for r in data["rows"]if r["HitObject"]==3),
                native_routes=native_routes,numeric_pass=actual==expected,summary=data["summary"])
            records.append(item)
            if not item["numeric_pass"]:differences.append(item)
        record=dict(fixture=spec,reference_formula="lambda_um = 1000*OpticalPathLU/OpticalPathW in uniform mm N-BK7; independently checked by Sellmeier index, never inferred from power or source WlUM",
            direct_reference=str(direct_path),catalog=str(catalog),coefficients=coefficients,
            ray_references=references,minimum_edge_distance_um=distance,bins=records,native_routes_agree=True,
            numeric_status="passed"if not differences else"failed",failed_bins=len(differences),
            limits="Specific saved dilute sample_3 ZRD; zero paths, GRIN, repeat conversion and other models are outside this reference")
        (e.folder/"membership-reference.json").write_text(json.dumps(record,indent=2),encoding="utf-8")
    asyncio.run(execute("fluorescence_filter_"+criterion,work))
    if criterion=="numeric_membership":
        assert not differences, "Native fine-band membership differs from independent segment wavelengths in "+str(len(differences))+" bins; see membership-reference.json"
