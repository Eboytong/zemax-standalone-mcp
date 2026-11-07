"""Typed disk history queries scoped to the configured output directory."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .schema import Request, Index

OpaqueId=Annotated[str,Field(pattern=r'^[0-9a-f]{32}$')]
RequestId=Annotated[str,Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')]

class TaskHistory(Request):
    session_id: OpaqueId | None = None
    request_id: RequestId | None = None
    kind: str | None = None
    state: Literal['running','cancelling','succeeded','failed','cancelled'] | None = None
    start: Index = 0
    count: Annotated[int,Field(strict=True,ge=1,le=200)] = 50

class HistoricalResult(Request):
    session_id: OpaqueId
    task_id: OpaqueId
    start: Index = 0
    count: Annotated[int,Field(strict=True,ge=1,le=1000)] = 200
    series: Index | None = None
    grid: Index | None = None
    x_start: Index = 0
    y_start: Index = 0
    width: Annotated[int,Field(strict=True,ge=1,le=1000)] = 32
    height: Annotated[int,Field(strict=True,ge=1,le=1000)] = 32

    @model_validator(mode='after')
    def region(self):
        if self.series is not None and self.grid is not None:raise ValueError('series与grid分别读取')
        if self.grid is not None and self.width*self.height>10000:raise ValueError('网格区域每次最多10000个值')
        return self

class RequestStatus(Request):
    request_id: RequestId
