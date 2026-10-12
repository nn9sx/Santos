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
from typing import get_args, get_origin

from santos.models.repo import ReadmeState, Repo

metadata = MetaData()


def _inner(annotation):
    if get_origin(annotation) is UnionType and NoneType in get_args(annotation):
        return next(arg for arg in get_args(annotation) if arg is not NoneType)
    return annotation


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
        nullable=get_origin(field.type) is UnionType and NoneType in get_args(field.type),
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
