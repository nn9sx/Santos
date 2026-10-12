from dataclasses import fields
from datetime import date
from pathlib import Path
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Enum,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
)
from types import NoneType, UnionType
from typing import Annotated, Union, get_args, get_origin

from santos.models.index import ReadmeState, Repo

metadata = MetaData()


def _unwrap(annotation):
    if get_origin(annotation) is Annotated: return _unwrap(get_args(annotation)[0])
    return annotation


def _optional(annotation):
    annotation = _unwrap(annotation)
    if get_origin(annotation) in (UnionType, Union) and NoneType in get_args(annotation):
        return next(arg for arg in get_args(annotation) if arg is not NoneType)
    return None


def _inner(annotation):
    optional = _optional(annotation)
    if optional is None: return _unwrap(annotation)
    return _unwrap(optional)


def _sql_type(annotation):
    python_type = _inner(annotation)
    if python_type is ReadmeState:
        return Enum(
            ReadmeState,
            native_enum=False,
            values_callable=lambda states: [state.value for state in states],
        )
    return {int: Integer, str: Text, date: Date, bool: Boolean}[python_type]


def _column(field, primary_key: bool) -> Column:
    return Column(
        field.name,
        _sql_type(field.type),
        primary_key=primary_key,
        nullable=_optional(field.type) is not None,
    )

repos = Table(
    Repo.table_name,
    metadata,
    *[_column(field, index == 0) for index, field in enumerate(fields(Repo))],
)
_engines = {}


def engine(db_path: Path):
    key = db_path.resolve()
    cached = _engines.get(key)
    if cached is None:
        key.parent.mkdir(parents=True, exist_ok=True)
        cached = create_engine(f"sqlite:///{key}")
        metadata.create_all(cached)
        _engines[key] = cached
    return cached
