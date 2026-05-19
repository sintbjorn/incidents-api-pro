import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Use SQLite file for tests to persist across app init
os.environ["DATABASE_URL"] = "sqlite:///./test_incidents.db"
Path("test_incidents.db").unlink(missing_ok=True)

from app.entrypoints.api import app  # noqa

@pytest.fixture(scope="session")
def client():
    return TestClient(app)
