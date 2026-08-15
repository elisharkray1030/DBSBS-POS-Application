from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from pos.facade import PosSession
from pos.persistence import InMemoryPersistence
from pos.sqlite import SqlitePersistence

T0 = datetime(2026, 8, 15, 9, 0, 0)
CATALOG_CSV = (
    "ItemID, ItemName, Price, Inventory, Sales, Revenue\n"
    "MUG, Mug, 60, 20, 30, 1800\n"
    "BDG, Badge, 15, 50, 10, 150\n"
    "PLUSH, Plush Bear, 120, , 5, 600\n"
)


@pytest.fixture
def clock():
    class Clock:
        def __init__(self):
            self.now = T0

        def __call__(self):
            return self.now

        def advance(self, minutes: int = 0, seconds: int = 0):
            import datetime as _dt

            self.now = self.now + _dt.timedelta(minutes=minutes, seconds=seconds)

    return Clock()


@pytest.fixture
def session(clock):
    return PosSession(InMemoryPersistence(), clock=clock)


@pytest.fixture
def catalog_file(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.csv"
    path.write_text(CATALOG_CSV, encoding="utf-8")
    return path


@pytest.fixture
def configured_session(session, catalog_file):
    session.set_device_name("Till A")
    session.set_float(500)
    session.load_catalog(catalog_file)
    return session


@pytest.fixture
def sqlite_store_factory(tmp_path: Path):
    db_path = tmp_path / "pos.db"
    stores = []

    def factory():
        store = SqlitePersistence(db_path)
        stores.append(store)
        return store

    yield factory
    for store in stores:
        store.close()
