"""Independent STL triangles and ray intersections for installed CAD fixtures."""
import math
import struct


def triangles(path):
    raw=path.read_bytes()
    if len(raw)>=84:
        count=struct.unpack_from('<I',raw,80)[0]
        if len(raw)==84+50*count:
            return [[list(struct.unpack_from('<3f',raw,84+50*i+12+12*j))for j in range(3)]for i in range(count)]
    vertices=[list(map(float,line.split()[1:]))for line in raw.decode('ascii').splitlines()if line.strip().startswith('vertex ')]
    if not vertices or len(vertices)%3:raise ValueError('STL has no complete triangles')
    return [vertices[i:i+3]for i in range(0,len(vertices),3)]


def subtract(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]


def intersect(mesh,origin,direction):
    hits=[]
    for face,(a,b,c)in enumerate(mesh):
        e1,e2=subtract(b,a),subtract(c,a);p=cross(direction,e2);det=dot(e1,p)
        if abs(det)<1e-12:continue
        s=subtract(origin,a);u=dot(s,p)/det
        if not 0<u<1:continue
        q=cross(s,e1);v=dot(direction,q)/det
        if v<=0 or u+v>=1:continue
        distance=dot(e2,q)/det
        if distance<=1e-9:continue
        n=cross(e1,e2);length=math.sqrt(dot(n,n))
        hits.append(dict(distance=distance,face=face,normal=[x/length for x in n],
            position=[x+distance*y for x,y in zip(origin,direction)]))
    if not hits:raise ValueError('no forward interior triangle hit')
    return min(hits,key=lambda h:h['distance'])
