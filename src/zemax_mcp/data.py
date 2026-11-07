"""Plain JSON values at the boundary; native objects never leave the worker."""

import math
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def unwrap(value):
    if value is None:
        return None
    return getattr(value, "__implementation__", value)


def clean(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if math.isfinite(value):
            # JSON consumers reject signed zero as a lossy
            # round-trip value. Optical zero has no directional significance;
            # retain every nonzero value and normalize only IEEE -0.0.
            return 0.0 if value == 0 else value
        return "Infinity" if value > 0 else "-Infinity" if value < 0 else "NaN"
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    raise TypeError(f"Not a JSON value: {type(value).__name__}")


def dotnet_array(value):
    if value.Rank == 1:
        return [float(v) for v in value]
    if value.Rank == 2:
        return [[float(value[i, j]) for j in range(value.GetLength(1))]
                for i in range(value.GetLength(0))]
    raise ValueError(f"Unsupported array rank: {value.Rank}")
