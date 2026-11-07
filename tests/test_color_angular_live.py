import asyncio,math
import pytest
from support.native import execute
from support.nsc import setup,update,trace,detector


@pytest.mark.zemax
def test_color_angular_projection_native():
    async def work(e):
        await setup(e,2)
        angle=math.radians(30)
        await update(e,[dict(object=1,object_type="SourceRay",data=dict(NumberOfAnalysisRays=1,Power=1,XCosine=math.sin(angle),ZCosine=math.cos(angle))),
            dict(object=2,object_type="DetectorColor",z=10,material="ABSORB",data=dict(XHalfWidth=20,YHalfWidth=20,NumberXPixels=3,NumberYPixels=5,
                XAngleMin=-45,XAngleMax=45,YAngleMin=-50,YAngleMax=50),type_settings=dict(UsePixelInterpolation=False))])
        await trace(e,"angular_color")
        flux=await detector(e,2,angle_space=True,width=3,height=5)
        assert flux["x_axis"]["centers"]==[-30,0,30]and flux["y_axis"]["centers"]==[-40,-20,0,20,40]
        e.check("Color angular 30deg pixel W",flux["values"][2][2],1)
        intensity=await detector(e,2,kind="intensity",width=3,height=5)
        assert intensity["values"][2][2]>0 and intensity["value_unit"]=="Watts/sr"
        await e.call("save_lens_as",dict(path=str(e.folder/"angular_color.zos")))
    asyncio.run(execute("color_angular",work))
