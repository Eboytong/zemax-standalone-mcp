"""Detector x conversion matrix: independent membership and native replay totals."""
import asyncio
import json
import math

import pytest
from support.native import execute
from support.nsc import detector
from support.wavelength_pairs import TYPES,coefficients,model,hits,reference


@pytest.mark.zemax
@pytest.mark.parametrize("kind",TYPES)
@pytest.mark.parametrize("converted",[False,True],ids=["fixed","fluorescence"])
def test_detector_wavelength_pair_native(kind,converted):
    numerical_failures=[];reference_failures=[]
    async def work(e):
        catalog,coeff=coefficients()
        zrd,baseline,reused=await model(e,kind,converted)
        objects=(await e.call("get_nsc_objects",dict(request=dict(start=1,count=10))))["rows"]
        before=await detector(e,3,width=91 if kind=="DetectorPolar"else 1,height=36 if kind=="DetectorPolar"else 1)
        rows,pages=await hits(e,zrd,"")
        refs,invalid,max_error=reference(rows,converted,coeff)
        reference_failures.extend(invalid)
        if converted and not any(.499<r["wavelength_um"]<.751 for r in refs):
            reference_failures.append(dict(reason="no converted detector hits; emission bins cannot be validated vacuously"))
        if len({(r["ray"],r["segment"])for r in refs})!=len(refs):reference_failures.append(dict(reason="duplicate hit identity"))
        intervals=[("unfiltered",None,None),("complete",.4,.8),("emission",.499,.751)]
        intervals += [("bin",nm/1000,(nm+25)/1000)for nm in range(500,750,25)]
        intervals += [("exact",.5,.5),("shared_left",.5,.625),("shared_right",.625,.75),("empty",.8,.9)]
        records=[]
        for name,lower,upper in intervals:
            expression=""if lower is None else f"X_WAVERANGE(3,{lower:.17g},{upper:.17g})"
            expected=refs if lower is None else [r for r in refs if lower<=r["wavelength_um"]<=upper]
            ambiguous=[] if lower is None or not converted else [r for r in refs if .499<r["wavelength_um"]<.751 and min(abs(r["wavelength_um"]-lower),abs(r["wavelength_um"]-upper))<=1e-6]
            if name=="unfiltered":actual=rows
            else:actual,_=await hits(e,zrd,expression)
            keys=lambda rs:sorted((r["ray"],r["segment"])for r in rs)
            expected_keys=keys(expected);actual_keys=keys(actual)
            expected_W=sum(r["power_W"]for r in expected);actual_W=sum(r["power_W"]for r in actual)
            item=dict(name=name,filter=expression,lower_um=lower,upper_um=upper,
                expected_keys=expected_keys,actual_keys=actual_keys,missing=sorted(set(expected_keys)-set(actual_keys)),
                unexpected=sorted(set(actual_keys)-set(expected_keys)),expected_W=expected_W,reader_W=actual_W,
                reference_ambiguous=[(r["ray"],r["segment"])for r in ambiguous],
                reader_pass=not invalid and not ambiguous and expected_keys==actual_keys and math.isclose(actual_W,expected_W,rel_tol=1e-7,abs_tol=1e-8))
            try:
                result=await e.finish(await e.call("run_zrd_replay",dict(request=dict(path=str(zrd),detector=3,filter=expression,
                    data_type="RadiantIntensity"if kind=="DetectorPolar"else"IncidentFlux"))))
                summary=result["native_replay_summary"]
                item["replay"]=summary
                power=summary["total_power"]
                item["replay_pass"]=bool(power is not None and not invalid and not ambiguous and
                    abs(power["value"]-expected_W)<=power["display_rounding_W"]+1e-8+1e-7*abs(expected_W))
                if summary["hit_count"]is not None:item["replay_pass"]=item["replay_pass"]and summary["hit_count"]==len(expected)
                item["replay_artifacts"]=result["artifacts"]
            except Exception as exc:
                item.update(replay_pass=False,replay_error=str(exc))
            if ambiguous:
                item["reference_status"]="boundary_ambiguous"
                reference_failures.append(dict(filter=expression,reason="reference wavelength too near boundary",rays=item["reference_ambiguous"]))
            elif invalid:item["reference_status"]="unavailable"
            else:
                item["reference_status"]="available"
                if not item["reader_pass"] or not item["replay_pass"]:numerical_failures.append(item)
            records.append(item)
        after=await detector(e,3,width=91 if kind=="DetectorPolar"else 1,height=36 if kind=="DetectorPolar"else 1)
        e.check("replay preserves current detector state",after["total_flux"],before["total_flux"])
        record=dict(detector_type=kind,converted=converted,baseline=baseline,zrd=str(zrd),reused=reused,
            settings=objects,catalog=str(catalog),coefficients=coeff,reference_formula="Known fixed source wavelengths, or lambda_um=1000*OpticalPathLU/OpticalPathW in uniform N-BK7; independent Sellmeier index check",
            reference_tolerance=dict(index_atol=2e-7,wavelength_boundary_guard_um=1e-6,rtol=1e-7,atol_W=1e-8,native_text_precision="half last displayed digit, zero has no large decimal tolerance"),
            reference_rays=refs,reference_invalid=reference_failures,reference_max_index_error=max_error,pages=pages,
            queries=records,reader_pass=not reference_failures and all(r["reader_pass"]for r in records),replay_pass=not reference_failures and all(r["replay_pass"]for r in records),
            before_detector_W=before["total_flux"],after_detector_W=after["total_flux"],
            conclusion="reference_unavailable"if reference_failures else("numeric_pass"if not numerical_failures else"numeric_failure"))
        (e.folder/"detector-pair-reference.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
    asyncio.run(execute("wavelength_pair_"+kind+("_PL"if converted else"_fixed"),work))
    assert not reference_failures,"Independent wavelength reference not established; see detector-pair-reference.json"
    assert not numerical_failures,f"{kind} converted={converted}: {len(numerical_failures)} query conditions fail numerical membership/replay; see detector-pair-reference.json"
