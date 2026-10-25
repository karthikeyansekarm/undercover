from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from agent import main
from backend.main import app


@pytest.fixture
def client(tmp_path, monkeypatch) -> Iterator[TestClient]:
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "test.db"))
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))
    with TestClient(app) as test_client:
        yield test_client
