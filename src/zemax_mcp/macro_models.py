"""Typed contract for standalone ZPL command-line execution."""
import re
from typing import Annotated

from pydantic import Field, model_validator

from .schema import Request


class StandaloneMacro(Request):
    macro_path: str
    arguments: dict[str, Annotated[str, Field(max_length=1024)]] = Field(default_factory=dict, max_length=64)
    expected_output: str | None = None
    output_argument_name: str | None = None
    timeout_seconds: Annotated[int, Field(strict=True, ge=1, le=7200)] = 300

    @model_validator(mode="after")
    def validate_macro_contract(self):
        normalized = set()
        for name in self.arguments:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", name):
                raise ValueError("ZPL argument names must be 1-32 ASCII letters, digits or underscores and start with a letter")
            if name.casefold() in normalized:
                raise ValueError("ZPL argument names are case-insensitive and must be unique")
            normalized.add(name.casefold())
            if name.casefold() == "isautomated":
                raise ValueError(f"{name} is a reserved OpticStudio command-line argument")
            value = self.arguments[name]
            if any(char in value for char in ('"', "\r", "\n", "\0")):
                raise ValueError("ZPL argument values cannot contain quotes or control characters")
        if (self.expected_output is None) != (self.output_argument_name is None):
            raise ValueError("expected_output and output_argument_name must be supplied together")
        if self.output_argument_name:
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", self.output_argument_name):
                raise ValueError("output_argument_name must be a 1-32 character ZPL argument name")
            if self.output_argument_name.casefold() == "isautomated" or self.output_argument_name.casefold() in normalized:
                raise ValueError("output_argument_name must be distinct from reserved and regular arguments")
        return self
