from zemax_mcp.config import PROJECT_ROOT
"""Independent test references; no native calls or application imports."""
import csv
import math
import re
import struct
from pathlib import Path


def write_polarized_zbf(path, nx, ny, dx, dy, ex, ey):
    """Explicit v1 test fixture, millimetres and 0.55um, two complex fields."""
    header=[1,nx,ny,1,0,0,0,0,0]
    metadata=[dx,dy,0,math.pi*.1**2/.00055,.1,0,math.pi*.1**2/.00055,.1,.00055,1,0,0]+[0.]*8
    with path.open("wb")as stream:
        stream.write(struct.pack("<9i20d",*header,*metadata))
        for component in(ex,ey):
            for value in component:stream.write(struct.pack("<dd",value.real,value.imag))


def read_native_text(path):
    raw = Path(path).read_bytes()
    return raw.decode("utf-16" if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else "utf-8-sig")


def mtf_text_values(text):
    values = {}
    field = None
    for line in text.splitlines():
        match = re.match(r"(?:视场[：:]|Field:)\s*([-\d.]+)", line)
        if match:
            field = float(match[1])
        match = re.fullmatch(r"\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*", line)
        if match and field is not None:
            frequency, tangential, sagittal = map(float, match.groups())
            for label, value in (("T", tangential), ("S", sagittal)):
                key = (field, frequency, label)
                if key in values:
                    raise ValueError("duplicate MTF sample")
                values[key] = value
    if not values:
        raise ValueError("no field-tagged MTF samples")
    return values


def cie_table():
    path = PROJECT_ROOT / "tests/reference_data/CIE_xyz_1931_2deg.csv"
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {int(row[0]): tuple(map(float, row[1:4])) for row in csv.reader(stream)}


def cie_xyz(spectrum):
    """Spectrum is explicit (integer nm, integrated power W), not W/nm."""
    table = cie_table()
    return [683 * math.fsum(power * table[nm][i] for nm, power in spectrum) for i in range(3)]


def chromaticities(xyz):
    x, y, z = xyz
    total = x + y + z
    denominator = x + 15*y + 3*z
    return dict(chromaticity_x=x/total, chromaticity_y=y/total,
                u_prime=4*x/denominator, v_prime=9*y/denominator)


def component_overlap(ex, ey, rx, ry):
    powers = [math.fsum(abs(v)**2 for v in component) for component in (ex, ey)]
    total = sum(powers)
    efficiency = 0.
    for incident, receiver, power in zip((ex, ey), (rx, ry), powers):
        received = math.fsum(abs(v)**2 for v in receiver)
        if power and received:
            inner = sum(a.conjugate()*b for a, b in zip(incident, receiver))
            efficiency += abs(inner)**2/(power*received)*power/total
    return float(efficiency)
