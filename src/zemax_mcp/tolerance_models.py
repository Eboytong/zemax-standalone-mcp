from typing import Annotated,Literal
from pydantic import Field,FiniteFloat,model_validator
from .schema import Request,PositiveIndex,Index,Positive

class ToleranceRange(Request):
    start: PositiveIndex = 1
    count: Annotated[int,Field(strict=True,ge=1,le=1000)] = 200
    include_metadata: bool = False

class ToleranceOperand(Request):
    type: str
    param1: Annotated[int,Field(strict=True,ge=-2147483648,le=2147483647)] | None = None
    param2: Annotated[int,Field(strict=True,ge=-2147483648,le=2147483647)] | None = None
    param3: Annotated[int,Field(strict=True,ge=-2147483648,le=2147483647)] | None = None
    minimum: FiniteFloat | None = None
    maximum: FiniteFloat | None = None
    comment: str = ""
    ignore: bool = False
    inverse_protected: bool = False

class ToleranceOperandUpdate(Request):
    operand: PositiveIndex
    type: Annotated[str,Field(min_length=1)] | None = None
    param1: Annotated[int,Field(strict=True,ge=-2147483648,le=2147483647)] | None = None
    param2: Annotated[int,Field(strict=True,ge=-2147483648,le=2147483647)] | None = None
    param3: Annotated[int,Field(strict=True,ge=-2147483648,le=2147483647)] | None = None
    minimum: FiniteFloat | None = None
    maximum: FiniteFloat | None = None
    comment: str | None = None
    ignore: bool | None = None
    inverse_protected: bool | None = None

    @model_validator(mode="after")
    def check(self):
        if not self.model_fields_set-{"operand"}:
            raise ValueError("没有公差行修改内容。")
        if any(getattr(self,key)is None for key in self.model_fields_set):
            raise ValueError("省略不修改的字段，不使用null。")
        return self

class TolerancePatch(Request):
    mode: Literal["replace","append","insert","update","delete"]
    operands: Annotated[list[ToleranceOperand],Field(max_length=1000)] = Field(default_factory=list)
    updates: Annotated[list[ToleranceOperandUpdate],Field(max_length=1000)] = Field(default_factory=list)
    operand_numbers: Annotated[list[PositiveIndex],Field(max_length=1000)] = Field(default_factory=list)
    at: PositiveIndex | None = None

    @model_validator(mode="after")
    def check(self):
        if self.mode=="update":
            if not self.updates or self.operands or self.operand_numbers or self.at is not None:
                raise ValueError("update使用非空updates。")
        elif self.mode=="delete":
            if not self.operand_numbers or self.operands or self.updates or self.at is not None:
                raise ValueError("delete使用非空operand_numbers。")
        else:
            if not self.operands or self.updates or self.operand_numbers:
                raise ValueError("replace/append/insert使用非空operands。")
            if (self.mode=="insert") != (self.at is not None):
                raise ValueError("insert须指定at；其他模式省略at。")
        ids=[x.operand for x in self.updates]+self.operand_numbers
        if len(ids)!=len(set(ids)):
            raise ValueError("同一批不能重复指定公差行。")
        return self

class ToleranceWizard(Request):
    start_surface: PositiveIndex = 1
    end_surface: PositiveIndex | None = None
    surface_radius: Positive | None = None
    surface_thickness: Positive | None = None
    surface_decenter_x: Positive | None = None
    surface_decenter_y: Positive | None = None
    surface_tilt_x_degrees: Positive | None = None
    surface_tilt_y_degrees: Positive | None = None
    element_decenter_x: Positive | None = None
    element_decenter_y: Positive | None = None
    element_tilt_x_degrees: Positive | None = None
    element_tilt_y_degrees: Positive | None = None
    focus_compensation: bool = False

    @model_validator(mode="after")
    def check(self):
        if not any(getattr(self,k) is not None for k in type(self).model_fields if k.startswith(("surface_","element_"))):raise ValueError("需要至少一个公差幅度。")
        return self

from .hpc_models import HpcSelection

class ToleranceAnalysis(Request):
    budget_seconds: Annotated[FiniteFloat,Field(gt=0,le=3600)] | None = None
    hpc: HpcSelection | None = None
    mode: Literal["sensitivity","inverse_limit","inverse_increment","monte_carlo"]
    criterion: str = "RMSSpotRadius"
    compensation: str = "None"
    sampling: Annotated[int,Field(strict=True,ge=1,le=10)] = 3
    cycles: Annotated[int,Field(strict=True,ge=1,le=100)] = 2
    configuration: Index = 0
    frequency: Positive = 50
    maximum_criterion: Positive = 1
    samples: Annotated[int,Field(strict=True,ge=1,le=10000)] = 20
    save_samples: Annotated[int,Field(strict=True,ge=0,le=10000)] = 0
    distribution: Literal["Normal","Uniform","Parabolic"] = "Normal"
    allow_tolerance_update: bool = False

    @model_validator(mode="after")
    def check(self):
        if self.mode.startswith("inverse") and not self.allow_tolerance_update:raise ValueError("逆灵敏度更新范围需要 allow_tolerance_update=true。")
        if self.save_samples>self.samples:raise ValueError("保存样本数不得大于请求数。")
        return self

class ToleranceSummary(Request):
    task_id: str
    criterion_column: Index
    threshold: FiniteFloat
    pass_when: Literal["less_equal","greater_equal"] = "less_equal"
    unit: str
