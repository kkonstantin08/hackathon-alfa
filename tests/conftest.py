import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ["DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
os.environ["LLM_MODE"] = "mock"


@pytest.fixture(scope="session", autouse=True)
def ingested():
    from app import ingest

    return ingest.main([])
