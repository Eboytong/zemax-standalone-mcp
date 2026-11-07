from typing import Annotated, Literal
from pydantic import Field, FiniteFloat, model_validator
from .schema import Request, Index, PositiveIndex, Positive

class ConfigurationSelect(Request):
    configuration: PositiveIndex

class ConfigurationRange(Request):
    start: PositiveIndex = 1
    count: Annotated[int, Field(strict=True, ge=1, le=1000)] = 200

class ConfigurationAction(Request):
    action: Literal["add", "insert", "delete"]
    configuration: PositiveIndex | None = None
    copy_current: bool = False

class ConfigSolve(Request):
    mode: Literal["fixed", "variable", "config_pickup", "thermal_pickup"]
    configuration: PositiveIndex | None = None
    operand: PositiveIndex | None = None
    scale: FiniteFloat = 1
    offset: FiniteFloat = 0

    @model_validator(mode="after")
    def check(self):
        if "pickup" in self.mode and self.configuration is None:
            raise ValueError("拾取需要源 configuration。")
        if self.mode=="config_pickup" and self.operand is None:
            raise ValueError("配置拾取需要源 operand。")
        return self

class ConfigurationCell(Request):
    configuration: PositiveIndex
    value: FiniteFloat | str | None = None
    solve: ConfigSolve | None = None
    replace_solve: bool = False

    @model_validator(mode="after")
    def check(self):
        if self.value is None and self.solve is None: raise ValueError("需要 value 或 solve。")
        return self

class ConfigOperand(Request):
    operand: PositiveIndex | None = None
    type: str | None = None
    parameters: dict[Annotated[int, Field(ge=1, le=3)], int] = Field(default_factory=dict)
    cells: Annotated[list[ConfigurationCell], Field(max_length=100)] = Field(default_factory=list)

class ConfigurationPatch(Request):
    actions: Annotated[list[ConfigurationAction], Field(max_length=100)] = Field(default_factory=list)
    operands: Annotated[list[ConfigOperand], Field(max_length=100)] = Field(default_factory=list)
    delete_operands: Annotated[list[PositiveIndex], Field(max_length=100)] = Field(default_factory=list)
    replace_solves: bool = False

    @model_validator(mode="after")
    def check(self):
        if not (self.actions or self.operands or self.delete_operands): raise ValueError("没有修改内容。")
        return self

from .hpc_models import HpcSelection

class GlobalOptimization(Request):
    hpc: HpcSelection | None = None
    runtime_seconds: Annotated[FiniteFloat, Field(gt=0, le=86400)]
    algorithm: Literal["DampedLeastSquares", "OrthogonalDescent"] = "DampedLeastSquares"
    number_of_cores: Annotated[int, Field(strict=True, ge=1)] = 1
    number_to_save: Literal["Save_10","Save_20","Save_30","Save_40","Save_50","Save_60","Save_70","Save_80","Save_90","Save_100"] = "Save_10"
