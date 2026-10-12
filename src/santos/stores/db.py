from pathlib import Path
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    Integer,
    MetaData,
    Table,
    Text,
    create_engine,
)

metadata = MetaData()
repos = Table(
    "repos",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("full_name", Text, nullable=False),
    Column("owner", Text),
    Column("language", Text),
    Column("current_stars", Integer),
    Column("description", Text),
    Column("tracked_since", Date),
    Column("active", Boolean, nullable=False),
    Column("readme_text", Text),
    Column("readme_state", Text, nullable=False),
    Column("etag", Text),
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
