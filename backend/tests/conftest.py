import os
import shutil
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_jobradar.db")
os.environ.setdefault("UPLOAD_DIR", "./test_data/uploads")
os.environ.setdefault("EXPORT_DIR", "./test_data/exports")
os.environ.setdefault("ENABLE_SCHEDULER", "false")

TEST_DB = Path(".jobradar-test.db")


def pytest_sessionstart(session) -> None:
    for path in [Path("test_jobradar.db"), Path("test_data")]:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()


def pytest_sessionfinish(session, exitstatus) -> None:
    for path in [Path("test_jobradar.db"), Path("test_data")]:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()
