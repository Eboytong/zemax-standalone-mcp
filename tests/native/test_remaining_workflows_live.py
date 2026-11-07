"""Controlled native references for additional detector and beam workflows."""
import asyncio,json,math,struct
from pathlib import Path
import pytest
from tests.support.native import execute
from tests.support.nsc import setup,update,detector,trace


@pytest.mark.zemax
def test_triangular_detector_native():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type="SourceRay",x=.5,y=1.5,data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type="DetectorSurface",z=10,material="ABSORB",data=dict(Radius=0,MaxAperture=3,MinAperture=0,NumberAZones=8,NumberRZones=4),type_settings=dict(FastRayTrace=False))])
        result,_=await trace(e,"triangles")
        flux=await detector(e,2,count=10)
        assert flux["total"]==56 and flux["next_start"]==10
        e.check("triangular detector total W",flux["total_flux"],1)
        irradiance=await detector(e,2,kind="irradiance",count=100)
        assert any(r["value"]>0 for r in irradiance["rows"])
        image=await e.call("export_analysis_image",dict(request=dict(task_id=result["task"]["task_id"],path=str(e.folder/"flux.png"))))
        assert image["image_source"]=="data_plot"
    asyncio.run(execute("triangular_detector",work))


@pytest.mark.zemax
def test_color_and_spectral_bin_native():
    async def work(e):
        await setup(e,2)
        await update(e,[dict(object=1,object_type="SourceRay",x=.5,y=1.5,data=dict(NumberOfAnalysisRays=1,Power=1,ZCosine=1)),
            dict(object=2,object_type="DetectorColor",z=10,material="ABSORB",
                data=dict(XHalfWidth=2,YHalfWidth=3,NumberXPixels=3,NumberYPixels=5),
                type_settings=dict(UsePixelInterpolation=False,RecordSpectralData=True,RecordPixelSpectralData=True,
                    NumberOfSpectralData=3,SpectralDataMinWave=.45,SpectralDataMaxWave=.65))])
        await trace(e,"color")
        values={}
        for channel in ("radiometric_flux","radiometric_density","photometric_flux","photometric_density","chromaticity_x","chromaticity_y","u_prime","v_prime","tristimulus_x","tristimulus_y","tristimulus_z"):
            data=await detector(e,2,color_channel=channel,width=3,height=5)
            values[channel]=data["values"][3][1]
        e.check("off-axis Color pixel x-fast W",values["radiometric_flux"],1)
        denominator=sum(values["tristimulus_"+axis]for axis in "xyz")
        x,y=values["chromaticity_x"],values["chromaticity_y"]
        e.check("CIE x normalized XYZ",x,values["tristimulus_x"]/denominator)
        e.check("CIE y normalized XYZ",y,values["tristimulus_y"]/denominator)
        e.check("CIE u prime",values["u_prime"],4*x/(-2*x+12*y+3))
        e.check("CIE v prime",values["v_prime"],9*y/(-2*x+12*y+3))
        e.check("photometric Y density",values["tristimulus_y"],values["photometric_density"])
        bins=await detector(e,2,kind="spectral",spectral_wavelengths_um=[.55])
        (e.folder/"color_reference.json").write_text(json.dumps(dict(channels=values,spectral=bins),ensure_ascii=False,indent=2),encoding="utf-8")
        e.check("spectral-bin pixel centroid X mm",bins["rows"][0]["centroid_x"],0)
        e.check("spectral-bin pixel centroid Y mm",bins["rows"][0]["centroid_y"],1.2)
        await e.call("save_lens_as",dict(path=str(e.folder/"color.zos")))
    asyncio.run(execute("color_spectral",work))


@pytest.mark.zemax
@pytest.mark.parametrize("text",[False,True])
@pytest.mark.parametrize("polarized",[False,True])
def test_file_beam_and_single_image_native(text,polarized):
    async def work(e):
        await e.model()
        await e.call("update_system_settings",dict(settings=dict(polarization=dict(unpolarized=False,jx=1,jy=0)if polarized else dict(unpolarized=True))))
        nx,ny=64,32;dx,dy=.01,.02;wx,wy=.1,.15
        header=[1,nx,ny,1,0,0,0,0,0]
        metadata=[dx,dy,0,math.pi*wx*wx/.00055,wx,0,math.pi*wy*wy/.00055,wy,.00055,1,0,0]+[0.]*8
        values=[]
        for component in range(2):
            for iy in range(ny):
                for ix in range(nx):
                    x=(ix-nx/2)*dx;y=(iy-ny/2)*dy
                    amplitude=math.exp(-(x/wx)**2-(y/wy)**2)/math.sqrt(2)
                    phase=.2*x+.1*y
                    values.extend([amplitude*math.cos(phase+component*math.pi/2),amplitude*math.sin(phase+component*math.pi/2)])
        path=e.folder/("text.zbf"if text else"binary.zbf")
        if text:path.write_text("A\n"+"\n".join(map(str,header+metadata+values)),encoding="ascii")
        else:path.write_bytes(struct.pack("<9i20d",*header,*metadata)+struct.pack("<"+str(len(values))+"d",*values))
        page=await e.call("get_beam_file",dict(request=dict(path=str(path),start=17,count=7,include_coordinates=True)))
        assert page["polarized"]and page["next_start"]==24
        e.check("sample X coordinate mm",page["rows"][0]["x"],-.15)
        e.check("sample Y coordinate mm",page["rows"][0]["y"],-.32)
        r=await e.finish(await e.call("run_pop",dict(request=dict(beam_type="File",beam_file=str(path),
            beam_parameters={},x_sampling="S_64x64",y_sampling="S_32x32",x_width=.64,y_width=.64,use_polarization=True))))
        e.check("file-beam normalized W",r["metrics"]["integrated_power"],1,atol=5e-4)
        from zemax_mcp.beam_files import read_beam
        output=next(a["path"]for a in r["artifacts"]if a["kind"]=="beam")
        center_index=nx*(ny//2)+nx//2
        origin=read_beam(output,center_index,1)["rows"][0]
        offset=read_beam(output,center_index+3*nx+7,1)["rows"][0]
        def fields(row):return complex(row["ex_real"],row["ex_imag"]),complex(row["ey_real"],row["ey_imag"])
        ex,ey=fields(origin);off_ex,_=fields(offset)
        stokes=2*(ex.conjugate()*ey).imag/(abs(ex)**2+abs(ey)**2)
        e.check("file circular Jones Stokes V",stokes,1 if polarized else 0)
        relative=off_ex/ex
        amplitude=math.exp(-(.07/wx)**2-(.06/wy)**2)
        phase=.2*.07+.1*.06 if polarized else 0
        e.check("file complex relative real",relative.real,amplitude*math.cos(phase))
        e.check("file complex relative imaginary",relative.imag,amplitude*math.sin(phase))
        (e.folder/"complex_file_reference.json").write_text(json.dumps(dict(system_unpolarized=not polarized,
            input_phase_formula="0.2*x+0.1*y radians",stokes_v=stokes,
            relative_field=dict(real=relative.real,imaginary=relative.imag),output_beam=output),indent=2),encoding="utf-8")
        image=await e.call("export_analysis_image",dict(request=dict(task_id=r["task"]["task_id"],path=str(e.folder/"irradiance.png"),width=640,height=480)))
        assert image["image_source"]=="data_plot"
        unavailable=await e.call("export_analysis_image",dict(request=dict(task_id=r["task"]["task_id"],path=str(e.folder/"native.png"),source="native")),okay=False)
        assert not unavailable["ok"]and unavailable["error"]["code"]=="UNSUPPORTED_NATIVE_IMAGE"
        await e.finish(await e.call("export_evaluation_report",dict(task_ids=[r["task"]["task_id"]],include_charts=True,background=True)))
    asyncio.run(execute(("file_beam_text"if text else"file_beam_binary")+("_polarized"if polarized else"_unpolarized"),work))
