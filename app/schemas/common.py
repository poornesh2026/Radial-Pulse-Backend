"""Shared schema building blocks."""

from __future__ import annotations

import re
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

T = TypeVar("T")

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 320 or not _EMAIL.match(value):
        raise ValueError("not a valid email address")
    return value


#: Lower-cased, trimmed, basic-shape-checked email. (Deliverability is checked by Cognito/Google.)
Email = Annotated[str, AfterValidator(normalize_email)]

ShortText = Annotated[str, Field(min_length=1, max_length=200)]


class ApiModel(BaseModel):
    """Base for request/response models: reject unknown fields, read from ORM objects."""

    model_config = ConfigDict(from_attributes=True, extra="forbid", str_strip_whitespace=True)


class Page(ApiModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class PageParams(ApiModel):
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
