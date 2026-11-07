"""Explicit native Detector Viewer totals; no generic grid-power inference."""
import math
import re
from .errors import ZemaxError


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?"


def check_replay_enum(native, settings, field, requested):
    expected=native.enum(settings.GetType().GetProperty(field).PropertyType,requested)
    actual=getattr(settings,field)
    if actual!=expected:
        raise ZemaxError("SETTING_REJECTED","原生回放未采用请求的枚举值。",setting=field,
                         requested=requested,expected_native=str(expected),actual=str(actual))


def replay_text_summary(lines):
    """2024 R2 Chinese/English total-power rows with explicit watt units."""
    powers=[];hits=[];unsupported=[]
    for number,line in enumerate(lines,1):
        match=re.fullmatch(r"\s*(?:总功率|Total\s+Power)\s*[:：=]\s*("+NUMBER+r")\s*(.*?)\s*",line,re.IGNORECASE)
        if match:
            token,unit=match.groups()
            if unit.casefold() not in {"w","watt","watts","瓦特"}:
                unsupported.append(dict(line=number,raw=line,reason="unverified native power unit"));continue
            value=float(token)
            if not math.isfinite(value) or value<0:
                unsupported.append(dict(line=number,raw=line,reason="invalid native total power"));continue
            mantissa,_,exponent=token.lower().partition("e")
            decimals=len(mantissa.split(".")[1])if "."in mantissa else 0
            try:rounding=0. if value==0 else .5*10.**(int(exponent or "0")-decimals)
            except OverflowError:
                unsupported.append(dict(line=number,raw=line,reason="invalid native power precision"));continue
            powers.append(dict(value=value,unit="Watts",display_rounding_W=rounding,native_token=token,line=number,raw=line))
        count=re.search(r"(?:总撞击数|Total\s+Hits)\s*[:：=]\s*(\d+)\b",line,re.IGNORECASE)
        if count:hits.append(int(count[1]))
    # Ambiguous/repeated totals are not silently selected or averaged.
    power=powers[0]if len(powers)==1 and not unsupported else None
    count=hits[0]if len(hits)==1 else None
    return dict(source="2024 R2 native Detector Viewer text preamble",total_power=power,hit_count=count,
        extraction_status="available"if power is not None else"unavailable",
        unavailable_reason=None if power is not None else"No unique finite total-power row with verified watt units",
        rejected_rows=unsupported)
