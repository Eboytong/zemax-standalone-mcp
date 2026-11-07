"""Exact sphere intersections/reflection provide a nonzero aberration reference."""
import asyncio,math,json
import pytest
from tests.support.native import execute


@pytest.mark.zemax
def test_aberrated_spherical_mirror_rays_native():
    async def work(e):
        await e.model();await e.call("insert_surfaces",dict(at=2))
        await e.call("update_surfaces",dict(changes=[dict(surface=1,thickness=10),dict(surface=2,radius=-200,conic=0,
            material="MIRROR",thickness=-100,semi_diameter=10,replace_solves=True)]))
        references=[]
        for degrees in (0,2):
            v=[0,math.sin(math.radians(degrees)),math.cos(math.radians(degrees))]
            rays=[];expected=[]
            for x,y in ((0,1),(0,4),(4,0),(-4,0),(0,-4)):
                p=[x,y,-10];c=[0,0,-200];pc=[p[i]-c[i]for i in range(3)]
                b=sum(pc[i]*v[i]for i in range(3));cc=sum(q*q for q in pc)-200**2
                t=-cc/(b+math.sqrt(b*b-cc));q=[p[i]+t*v[i]for i in range(3)]
                normal=[(q[i]-c[i])/200 for i in range(3)];projection=sum(v[i]*normal[i]for i in range(3))
                direction=[v[i]-2*projection*normal[i]for i in range(3)]
                travel=(-100-q[2])/direction[2];image=[q[i]+travel*direction[i]for i in range(3)]
                expected.append((image,direction));rays.append(dict(x=x,y=y,z=0,l=v[0],m=v[1],n=v[2]))
            result=await e.finish(await e.call("run_batch_ray_trace",dict(request=dict(input_mode="Direct",start_surface=1,target_surface=3,rays=rays))))
            for i,(row,(point,direction))in enumerate(zip(result["rows"],expected)):
                assert row["error_code"]==0
                for j in (0,1):e.check(f"exact spherical reflection {degrees}deg ray{i} image{j} mm",row["position"][j],point[j])
                # Native DirectUnpol returns the signed sequential cosine vector;
                # this single-reflection fixture has negative propagation thickness.
                for j in range(3):e.check(f"spherical reflection {degrees}deg ray{i} native signed cosine{j}",row["direction"][j],-direction[j])
            references.append(dict(degrees=degrees,expected=expected))
        (e.folder/"ray_reference.json").write_text(json.dumps(dict(radius_mm=-200,image_z_mm=-100,
            reference="sphere quadratic intersection and vector reflection; off-axis meridional/sagittal rays",
            native_direction_convention="for this single-reflection fixture native DirectUnpol cosines are opposite to physical propagation; raw results retained",models=references),indent=2),encoding="utf-8")
        await e.call("save_lens_as",dict(path=str(e.folder/"spherical_aberration.zos")))
    asyncio.run(execute("aberrated_sphere_rays",work))
