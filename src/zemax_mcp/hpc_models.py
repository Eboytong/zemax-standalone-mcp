"""Typed selection of native HPC preferences or custom settings."""
from typing import Annotated, Literal
from pydantic import Field
from .schema import Request


class HpcPreferences(Request):
    mode: Literal['preferences']


class HpcCustom(Request):
    mode: Literal['custom']
    node_count: Annotated[int, Field(strict=True, ge=1, le=2147483647)]
    instance_type: Literal['Default','Tiny','Small','Medium','Large','XLarge'] = 'Default'


HpcSelection = Annotated[HpcPreferences | HpcCustom, Field(discriminator='mode')]


class HpcSettingsQuery(Request):
    request: HpcSelection
