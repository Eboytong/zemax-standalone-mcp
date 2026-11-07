"""Shared request primitives without command registration dependencies."""
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

Index = Annotated[int, Field(strict=True, ge=0)]
PositiveIndex = Annotated[int, Field(strict=True, ge=1)]
Weight = Annotated[FiniteFloat, Field(ge=0)]
Positive = Annotated[FiniteFloat, Field(gt=0)]

class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")
