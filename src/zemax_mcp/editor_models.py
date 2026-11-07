"""Typed editor row and metadata operations for installed sequential editors."""
from typing import Annotated,Literal
from pydantic import Field
from .schema import Request,PositiveIndex,Index

Editor=Literal['MFE','MCE','TDE']

class EditorMetadata(Request):
    editor: Editor
    operand: PositiveIndex = 1
    column_start: Index = 0
    column_count: Annotated[int,Field(strict=True,ge=1,le=100)] = 30

class EditorInsert(Request):
    editor: Editor
    at: PositiveIndex
    count: Annotated[int,Field(strict=True,ge=1,le=1000)] = 1
    operand_type: Annotated[str,Field(min_length=1)] | None = None

class EditorCopy(Request):
    editor: Editor
    start: PositiveIndex
    count: Annotated[int,Field(strict=True,ge=1,le=1000)] = 1
    at: PositiveIndex
